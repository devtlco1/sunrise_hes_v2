import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from gurux_common import TimeoutException
from gurux_dlms import GXDLMSException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.schemas import (
    ConnectionEventRead,
    DashboardStats,
    DlmsReadResult,
    DlmsRelayResult,
    MeterCreate,
    MeterRead,
    MeterUpdate,
)
from app.services import dlms_meter as dlms_ops
from app.services import meters as meter_service

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_stats(session: AsyncSession = Depends(get_db)) -> DashboardStats:
    total, online, offline = await meter_service.dashboard_stats(session)
    return DashboardStats(
        total_meters=total,
        online_meters=online,
        offline_meters=offline,
        online_window_seconds=settings.online_window_seconds,
    )


@router.get("/meters", response_model=list[MeterRead])
async def list_meters(session: AsyncSession = Depends(get_db)) -> list[MeterRead]:
    rows = await meter_service.list_meters(session)
    w = settings.online_window_seconds
    return [
        MeterRead(
            id=m.id,
            name=m.name,
            serial_number=m.serial_number,
            peer_ip=m.peer_ip,
            notes=m.notes,
            created_at=m.created_at,
            last_seen_at=m.last_seen_at,
            is_online=meter_service.meter_is_online(m.last_seen_at, w),
        )
        for m in rows
    ]


@router.post("/meters", response_model=MeterRead, status_code=201)
async def create_meter(
    body: MeterCreate, session: AsyncSession = Depends(get_db)
) -> MeterRead:
    m = await meter_service.create_meter(session, body)
    w = settings.online_window_seconds
    return MeterRead(
        id=m.id,
        name=m.name,
        serial_number=m.serial_number,
        peer_ip=m.peer_ip,
        notes=m.notes,
        created_at=m.created_at,
        last_seen_at=m.last_seen_at,
        is_online=meter_service.meter_is_online(m.last_seen_at, w),
    )


@router.patch("/meters/{meter_id}", response_model=MeterRead)
async def patch_meter(
    meter_id: uuid.UUID,
    body: MeterUpdate,
    session: AsyncSession = Depends(get_db),
) -> MeterRead:
    m = await meter_service.update_meter(session, meter_id, body)
    if not m:
        raise HTTPException(status_code=404, detail="Meter not found")
    w = settings.online_window_seconds
    return MeterRead(
        id=m.id,
        name=m.name,
        serial_number=m.serial_number,
        peer_ip=m.peer_ip,
        notes=m.notes,
        created_at=m.created_at,
        last_seen_at=m.last_seen_at,
        is_online=meter_service.meter_is_online(m.last_seen_at, w),
    )


@router.get("/ingress/events", response_model=list[ConnectionEventRead])
async def list_ingress_events(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[ConnectionEventRead]:
    return await meter_service.recent_connection_events(session, limit=limit)


def _require_peer_ip(m) -> str:
    if not m or not m.peer_ip or not str(m.peer_ip).strip():
        raise HTTPException(
            status_code=400,
            detail="يجب تعبئة peer_ip للمقياس (عنوان يقبل اتصال DLMS من السيرفر، غالباً نفس IP الظاهر في الـ ingress).",
        )
    return str(m.peer_ip).strip()


@router.post("/meters/{meter_id}/read-identity", response_model=DlmsReadResult)
async def read_meter_identity(
    meter_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> DlmsReadResult:
    """
    قراءة هوية + سجلات OBIS إضافية عبر DLMS (اتصال صادر إلى peer_ip:DLMS_TCP_PORT).
    """
    m = await meter_service.get_meter(session, meter_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meter not found")
    host = _require_peer_ip(m)
    port = settings.dlms_tcp_port
    try:
        data = await asyncio.to_thread(
            dlms_ops.read_identity_and_registers, settings, host, port
        )
    except (TimeoutException, GXDLMSException, OSError, ConnectionError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    serial = data.get("serial_number")
    if serial:
        await meter_service.update_meter(
            session, meter_id, MeterUpdate(serial_number=serial)
        )
    msg = None
    if not serial:
        msg = "لم يُستخرج رقم تسلسلي من OBIS الهوية؛ جرّب LOW auth وكلمة المرور أو واجهة HDLC بدل WRAPPER."
    return DlmsReadResult(
        serial_number=serial,
        serial_source_obis=data.get("serial_source_obis"),
        registers=data.get("registers") or {},
        message=msg,
    )


@router.post("/meters/{meter_id}/relay/disconnect", response_model=DlmsRelayResult)
async def relay_disconnect_meter(
    meter_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> DlmsRelayResult:
    m = await meter_service.get_meter(session, meter_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meter not found")
    host = _require_peer_ip(m)
    try:
        await asyncio.to_thread(
            dlms_ops.relay_disconnect, settings, host, settings.dlms_tcp_port
        )
    except (TimeoutException, GXDLMSException, OSError, ConnectionError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return DlmsRelayResult(operation="disconnect")


@router.post("/meters/{meter_id}/relay/reconnect", response_model=DlmsRelayResult)
async def relay_reconnect_meter(
    meter_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> DlmsRelayResult:
    m = await meter_service.get_meter(session, meter_id)
    if not m:
        raise HTTPException(status_code=404, detail="Meter not found")
    host = _require_peer_ip(m)
    try:
        await asyncio.to_thread(
            dlms_ops.relay_reconnect, settings, host, settings.dlms_tcp_port
        )
    except (TimeoutException, GXDLMSException, OSError, ConnectionError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return DlmsRelayResult(operation="reconnect")
