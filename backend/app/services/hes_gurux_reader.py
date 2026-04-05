# DLMS I/O adapted from Gurux.DLMS.Client.Example.python (GPLv2) — log to devnull, no stdout.
# https://github.com/Gurux/Gurux.DLMS.Python

from __future__ import annotations

import datetime
import logging
import os

from gurux_common import GXCommon, ReceiveParameters, TimeoutException
from gurux_common.enums import TraceLevel
from gurux_dlms import GXByteBuffer, GXDLMSException, GXReplyData
from gurux_dlms.enums import (
    AssociationResult,
    Authentication,
    DataType,
    InterfaceType,
    Security,
    SourceDiagnostic,
)
from gurux_net import GXNet

logger = logging.getLogger(__name__)


class HesGuruxReader:
    """Minimal GXDLMSReader for head-end outbound TCP (WRAPPER/HDLC)."""

    def __init__(self, client, media: GXNet, trace: int = TraceLevel.OFF) -> None:
        self.reply_buff = bytearray(8 + 1024)
        self.wait_time = 8000
        self.log_file = open(os.devnull, "w", encoding="utf-8")
        self.trace = trace
        self.media = media
        self.invocation_counter: str | None = None
        self.client = client

    def _trace(self, line: str, level: int) -> None:
        if self.trace >= level:
            logger.debug("%s", line)
        self.log_file.write(line + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    def read_dlms_packet(self, data, reply: GXReplyData | None = None) -> None:
        if reply is None:
            reply = GXReplyData()
        if isinstance(data, bytearray):
            self._read_dlms_packet2(data, reply)
        elif data:
            for it in data:
                reply.clear()
                self._read_dlms_packet2(it, reply)

    def _read_dlms_packet2(self, data: bytearray, reply: GXReplyData) -> None:
        if not data:
            return
        from gurux_dlms import GXDLMSTranslator

        notify = GXReplyData()
        reply.error = 0
        eop = 0x7E
        if self.client.interfaceType == InterfaceType.WRAPPER and isinstance(
            self.media, GXNet
        ):
            eop = None
        p = ReceiveParameters()
        p.eop = eop
        p.allData = True
        p.waitTime = self.wait_time
        if eop is None:
            p.Count = 8
        else:
            p.Count = 5
        self.media.eop = eop
        rd = GXByteBuffer()
        with self.media.getSynchronous():
            if not reply.isStreaming():
                self._trace(
                    "TX: " + self._now() + "\t" + GXByteBuffer.hex(data),
                    TraceLevel.VERBOSE,
                )
                self.media.send(data)
            pos = 0
            try:
                while not self.client.getData(rd, reply, notify):
                    if notify.data.size != 0:
                        if not notify.isMoreData():
                            notify.clear()
                        continue
                    if not p.eop:
                        p.count = self.client.getFrameSize(rd)
                    while not self.media.receive(p):
                        pos += 1
                        if pos == 3:
                            raise TimeoutException(
                                "Failed to receive reply from the device in given time."
                            )
                        logger.warning("DLMS resend %s/3", pos)
                        self.media.send(data, None)
                    rd.set(p.reply)
                    p.reply = None
            except Exception as e:
                self._trace("RX: " + self._now() + "\t" + str(rd), TraceLevel.ERROR)
                raise e
            self._trace("RX: " + self._now() + "\t" + str(rd), TraceLevel.VERBOSE)
            if reply.error != 0:
                raise GXDLMSException(reply.error)

    def read_data_block(self, data, reply: GXReplyData) -> None:
        if data:
            if isinstance(data, list):
                for it in data:
                    reply.clear()
                    self.read_data_block(it, reply)
                return
            self.read_dlms_packet(data, reply)
            while reply.isMoreData():
                if reply.isStreaming():
                    data = None
                else:
                    data = self.client.receiverReady(reply)
                self.read_dlms_packet(data, reply)

    def initialize_optical_head(self) -> None:
        if self.client.interfaceType != InterfaceType.HDLC_WITH_MODE_E:
            return
        raise RuntimeError("HDLC_WITH_MODE_E serial not supported in HES outbound path")

    def update_frame_counter(self) -> None:
        if not (
            self.invocation_counter
            and self.client.ciphering is not None
            and self.client.ciphering.security != Security.NONE
        ):
            return
        from gurux_dlms.enums import Conformance
        from gurux_dlms.objects import GXDLMSData

        self.initialize_optical_head()
        self.client.proposedConformance |= Conformance.GENERAL_PROTECTION
        add = self.client.clientAddress
        auth = self.client.authentication
        security = self.client.ciphering.security
        challenge = self.client.ctoSChallenge
        try:
            self.client.clientAddress = 16
            self.client.authentication = Authentication.NONE
            self.client.ciphering.security = Security.NONE
            reply = GXReplyData()
            data = self.client.snrmRequest()
            if data:
                self.read_dlms_packet(data, reply)
                self.client.parseUAResponse(reply.data)
                self.reply_buff = bytearray(self.client.hdlcSettings.maxInfoTX + 40)
            reply.clear()
            self.read_data_block(self.client.aarqRequest(), reply)
            self.client.parseAareResponse(reply.data)
            reply.clear()
            d = GXDLMSData(self.invocation_counter)
            self.read_object(d, 2)
            self.client.ciphering.invocationCounter = 1 + d.value
            self.disconnect_dlms()
        finally:
            self.client.clientAddress = add
            self.client.authentication = auth
            self.client.ciphering.security = security
            self.client.ctoSChallenge = challenge

    def initialize_connection(self) -> None:
        self.update_frame_counter()
        self.initialize_optical_head()
        reply = GXReplyData()
        data = self.client.snrmRequest()
        if data:
            self.read_dlms_packet(data, reply)
            self.client.parseUAResponse(reply.data)
            self.reply_buff = bytearray(self.client.hdlcSettings.maxInfoTX + 40)
        reply.clear()
        self.read_data_block(self.client.aarqRequest(), reply)
        self.client.parseAareResponse(reply.data)
        reply.clear()
        if self.client.authentication > Authentication.LOW:
            try:
                for it in self.client.getApplicationAssociationRequest():
                    self.read_dlms_packet(it, reply)
                    self.client.parseApplicationAssociationResponse(reply.data)
            except GXDLMSException:
                raise GXDLMSException(
                    AssociationResult.PERMANENT_REJECTED,
                    SourceDiagnostic.AUTHENTICATION_FAILURE,
                )

    def read_object(self, item, attribute_index: int):
        data = self.client.read(item, attribute_index)[0]
        reply = GXReplyData()
        self.read_data_block(data, reply)
        if item.getDataType(attribute_index) == DataType.NONE:
            item.setDataType(attribute_index, reply.valueType)
        return self.client.updateValue(item, attribute_index, reply.value)

    def invoke_method_request(self, request) -> None:
        reply = GXReplyData()
        self.read_data_block(request, reply)

    def disconnect_dlms(self) -> None:
        if self.media and self.media.isOpen():
            reply = GXReplyData()
            self.read_dlms_packet(self.client.disconnectRequest(), reply)

    def close(self) -> None:
        if self.media and self.media.isOpen():
            reply = GXReplyData()
            try:
                if (
                    self.client.interfaceType == InterfaceType.WRAPPER
                    or self.client.ciphering.security != Security.NONE
                ):
                    self.read_data_block(self.client.releaseRequest(), reply)
            except Exception:
                pass
            reply.clear()
            self.read_dlms_packet(self.client.disconnectRequest(), reply)
            self.media.close()
        try:
            self.log_file.close()
        except OSError:
            pass
