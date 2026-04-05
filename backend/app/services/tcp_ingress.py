import asyncio
import logging

from app.core.config import settings
from app.db import AsyncSessionLocal
from app.services import meters as meter_service

logger = logging.getLogger(__name__)

_server: asyncio.Server | None = None
_serve_task: asyncio.Task[None] | None = None


async def _handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
) -> None:
    peer = writer.get_extra_info("peername")
    ip = peer[0] if peer else "unknown"
    port = int(peer[1]) if peer and len(peer) > 1 else None
    data = b""
    try:
        data = await asyncio.wait_for(reader.read(8192), timeout=3.0)
    except TimeoutError:
        pass
    except OSError as e:
        logger.debug("ingress read: %s", e)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await meter_service.touch_meters_by_peer_ip(session, ip)
            await meter_service.log_connection_event(session, ip, port, data or None)

    try:
        writer.close()
        await writer.wait_closed()
    except OSError:
        pass


async def start_tcp_ingress() -> None:
    global _server, _serve_task
    if not settings.tcp_ingress_enabled:
        logger.info("TCP ingress disabled")
        return
    _server = await asyncio.start_server(
        _handle_client,
        settings.tcp_ingress_host,
        settings.tcp_ingress_port,
    )
    sockets = _server.sockets or []
    addrs = ", ".join(str(s.getsockname()) for s in sockets)
    logger.info("TCP meter ingress listening on %s", addrs)
    _serve_task = asyncio.create_task(_server.serve_forever())


async def stop_tcp_ingress() -> None:
    global _server, _serve_task
    if _serve_task:
        _serve_task.cancel()
        try:
            await _serve_task
        except asyncio.CancelledError:
            pass
        _serve_task = None
    if _server:
        _server.close()
        await _server.wait_closed()
        _server = None
