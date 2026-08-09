from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any

class MachineBase(BaseModel):
    name: str
    status: str

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class BookingBase(BaseModel):
    machine_id: UUID
    user_id: UUID
    started_at: datetime
    estimated_end_at: datetime
    cleared_at: Optional[datetime] = None

class BookingResponse(BookingBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class QueueBase(BaseModel):
    machine_id: UUID
    user_id: UUID
    joined_at: datetime
    position: int
    status: str

class QueueResponse(QueueBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# Request DTOs
class ClaimRequest(BaseModel):
    user_id: UUID

class PingRequest(BaseModel):
    user_id: UUID

class QueueJoinRequest(BaseModel):
    user_id: UUID

class PinVerifyRequest(BaseModel):
    pin: str

# User DTOs
class UserResponse(BaseModel):
    id: UUID
    name: str
    email: Optional[str] = None
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Smart Plug DTOs
class SmartPlugBase(BaseModel):
    provider: str = "tuya_local"
    device_id: str
    local_key: str
    ip_address: str
    protocol_version: str = "3.3"
    power_threshold_running: float = 10.0
    power_threshold_idle: float = 5.0
    debounce_seconds: int = 120

class SmartPlugCreate(SmartPlugBase):
    machine_id: Optional[UUID] = None

class SmartPlugUpdate(BaseModel):
    machine_id: Optional[UUID] = None
    provider: Optional[str] = None
    device_id: Optional[str] = None
    local_key: Optional[str] = None
    ip_address: Optional[str] = None
    protocol_version: Optional[str] = None
    power_threshold_running: Optional[float] = None
    power_threshold_idle: Optional[float] = None
    debounce_seconds: Optional[int] = None

class SmartPlugResponse(SmartPlugBase):
    id: UUID
    machine_id: Optional[UUID] = None
    is_online: bool = False
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Telemetry DTOs
class TelemetryReadingResponse(BaseModel):
    id: UUID
    plug_id: UUID
    voltage_v: Optional[float] = None
    current_ma: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    switch_on: Optional[bool] = None
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Anonymized Student Machine Status Detail
class MachineDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_booking: Optional[BookingResponse] = None
    queue: List[QueueResponse] = []
    latest_power_w: Optional[float] = None
    is_plug_online: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)

# Admin Detailed Machine Response (Exposes User Identity + Telemetry)
class AdminBookingResponse(BookingResponse):
    user_name: str
    user_email: Optional[str] = None

class AdminQueueResponse(QueueResponse):
    user_name: str
    user_email: Optional[str] = None

class AdminMachineDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_booking: Optional[AdminBookingResponse] = None
    queue: List[AdminQueueResponse] = []
    smart_plug: Optional[SmartPlugResponse] = None
    latest_telemetry: Optional[TelemetryReadingResponse] = None
    model_config = ConfigDict(from_attributes=True)
