"""
Outbound DLMS/COSEM toward meter (TCP). Requires meter.peer_ip and reachable dlms_tcp_port.
Ingress 8766 is separate (meters pushing); many deployments also expose 4059 for client reads.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from gurux_dlms.enums import Authentication, InterfaceType
from gurux_dlms.objects import GXDLMSData, GXDLMSDisconnectControl
from gurux_dlms.secure.GXDLMSSecureClient import GXDLMSSecureClient
from gurux_common.enums import TraceLevel
from gurux_net import GXNet
from gurux_net.enums import NetworkType

from app.core.config import Settings
from app.services.hes_gurux_reader import HesGuruxReader

logger = logging.getLogger(__name__)

IDENTITY_OBIS = (
    "0.0.96.1.0.255",
    "0.0.96.1.1.255",
    "0.0.96.1.2.255",
)
RELAY_OBIS = "0.0.96.3.10.255"


def _fmt_value(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _build_client(settings: Settings) -> GXDLMSSecureClient:
    auth = (
        Authentication.LOW
        if settings.dlms_authentication.strip().upper() == "LOW"
        else Authentication.NONE
    )
    pwd = settings.dlms_password_effective
    iface = (
        InterfaceType.WRAPPER
        if settings.dlms_interface.strip().upper() == "WRAPPER"
        else InterfaceType.HDLC
    )
    return GXDLMSSecureClient(
        True,
        settings.dlms_client_address,
        settings.dlms_server_address,
        auth,
        pwd,
        iface,
    )


def run_dlms_tcp(
    host: str,
    port: int,
    settings: Settings,
    work: Callable[[HesGuruxReader, GXDLMSSecureClient], Any],
) -> Any:
    client = _build_client(settings)
    media = GXNet(NetworkType.TCP, host, port)
    reader = HesGuruxReader(client, media, TraceLevel.OFF)
    media.open()
    try:
        reader.initialize_connection()
        return work(reader, client)
    finally:
        reader.close()


def read_identity_and_registers(settings: Settings, host: str, port: int) -> dict[str, Any]:
    registers: dict[str, str] = {}
    serial: str | None = None
    serial_obis: str | None = None

    def work(reader: HesGuruxReader, client: GXDLMSSecureClient) -> None:
        nonlocal serial, serial_obis
        for ln in IDENTITY_OBIS:
            try:
                d = GXDLMSData(ln)
                v = reader.read_object(d, 2)
                s = _fmt_value(v)
                if s:
                    serial = s
                    serial_obis = ln
                    break
            except Exception as e:
                logger.debug("identity read %s: %s", ln, e)
        for obis in settings.dlms_extra_read_obis_list():
            try:
                d = GXDLMSData(obis.strip())
                v = reader.read_object(d, 2)
                registers[obis.strip()] = _fmt_value(v)
            except Exception as e:
                logger.debug("register read %s: %s", obis, e)
                registers[obis.strip()] = ""

    run_dlms_tcp(host, port, settings, work)
    return {
        "serial_number": serial,
        "serial_source_obis": serial_obis,
        "registers": registers,
    }


def relay_disconnect(settings: Settings, host: str, port: int) -> None:
    def work(reader: HesGuruxReader, client: GXDLMSSecureClient) -> None:
        dc = GXDLMSDisconnectControl(RELAY_OBIS)
        reader.invoke_method_request(dc.remoteDisconnect(client))

    run_dlms_tcp(host, port, settings, work)


def relay_reconnect(settings: Settings, host: str, port: int) -> None:
    def work(reader: HesGuruxReader, client: GXDLMSSecureClient) -> None:
        dc = GXDLMSDisconnectControl(RELAY_OBIS)
        reader.invoke_method_request(dc.remoteReconnect(client))

    run_dlms_tcp(host, port, settings, work)
