import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.schemas import (
    ConnectionEventRead,
    DashboardStats,
    MeterCreate,
    MeterRead,
    MeterUpdate,
)
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


@router.post("/meters/{meter_id}/read-identity")
async def read_meter_identity(meter_id: uuid.UUID) -> None:
    """
    Placeholder: DLMS/COSEM identity read (Gurux) on the ingress session — next iteration.
    """
    raise HTTPException(
        status_code=501,
        detail=f"DLMS identity read not wired yet (meter_id={meter_id}); see meter-communication-reference-ar.md",
    )
