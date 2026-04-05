import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MeterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    serial_number: str | None = Field(None, max_length=64)
    peer_ip: str | None = Field(None, max_length=45)
    notes: str | None = None


class MeterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    serial_number: str | None = Field(None, max_length=64)
    peer_ip: str | None = Field(None, max_length=45)
    notes: str | None = None


class MeterRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    serial_number: str | None
    peer_ip: str | None
    notes: str | None
    created_at: datetime
    last_seen_at: datetime | None
    is_online: bool = False


class DashboardStats(BaseModel):
    total_meters: int
    online_meters: int
    offline_meters: int
    online_window_seconds: int


class ConnectionEventRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    peer_ip: str
    peer_port: int | None
    bytes_preview_hex: str | None
    created_at: datetime
