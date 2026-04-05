import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ConnectionEvent, Meter
from app.schemas import MeterCreate, MeterUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def meter_is_online(last_seen_at: datetime | None, window_sec: int) -> bool:
    if last_seen_at is None:
        return False
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    return last_seen_at >= _now() - timedelta(seconds=window_sec)


async def list_meters(session: AsyncSession) -> list[Meter]:
    result = await session.execute(select(Meter).order_by(Meter.created_at.desc()))
    return list(result.scalars().all())


async def get_meter(session: AsyncSession, meter_id: uuid.UUID) -> Meter | None:
    return await session.get(Meter, meter_id)


async def create_meter(session: AsyncSession, data: MeterCreate) -> Meter:
    m = Meter(
        name=data.name,
        serial_number=data.serial_number,
        peer_ip=data.peer_ip,
        notes=data.notes,
    )
    session.add(m)
    await session.flush()
    return m


async def update_meter(
    session: AsyncSession, meter_id: uuid.UUID, data: MeterUpdate
) -> Meter | None:
    m = await get_meter(session, meter_id)
    if not m:
        return None
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(m, k, v)
    await session.flush()
    return m


async def touch_meters_by_peer_ip(session: AsyncSession, peer_ip: str) -> int:
    stmt = (
        update(Meter)
        .where(Meter.peer_ip == peer_ip)
        .values(last_seen_at=func.now())
    )
    res = await session.execute(stmt)
    return res.rowcount or 0


async def log_connection_event(
    session: AsyncSession,
    peer_ip: str,
    peer_port: int | None,
    preview: bytes | None,
    max_preview: int = 256,
) -> None:
    hex_preview = None
    if preview:
        chunk = preview[:max_preview]
        hex_preview = chunk.hex().upper()
    ev = ConnectionEvent(
        peer_ip=peer_ip,
        peer_port=peer_port,
        bytes_preview_hex=hex_preview,
    )
    session.add(ev)


async def dashboard_stats(session: AsyncSession) -> tuple[int, int, int]:
    total = await session.scalar(select(func.count()).select_from(Meter))
    total = int(total or 0)
    window = settings.online_window_seconds
    threshold = _now() - timedelta(seconds=window)
    online = await session.scalar(
        select(func.count())
        .select_from(Meter)
        .where(Meter.last_seen_at.is_not(None), Meter.last_seen_at >= threshold)
    )
    online = int(online or 0)
    offline = max(0, total - online)
    return total, online, offline


async def recent_connection_events(
    session: AsyncSession, limit: int = 50
) -> list[ConnectionEvent]:
    q = (
        select(ConnectionEvent)
        .order_by(ConnectionEvent.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(q)
    return list(res.scalars().all())
