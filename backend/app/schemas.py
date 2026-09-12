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
    user_id: Optional[UUID] = None
    target: str = "occupant" # "occupant" | "admin" | "both"

class QueueJoinRequest(BaseModel):
    user_id: UUID

class PinVerifyRequest(BaseModel):
    pin: str

class StudentRegisterRequest(BaseModel):
    name: str
    room_number: str
    password: str
    registration_token: str
    phone: Optional[str] = None
    email: Optional[str] = None
    university: Optional[str] = None
    college: Optional[str] = None
    hostel: Optional[str] = None

class StudentLoginRequest(BaseModel):
    room_number: str
    password: str
    name: Optional[str] = None

class CalibrationUpdateRequest(BaseModel):
    power_threshold_running: float
    power_threshold_idle: float
    debounce_seconds: int
    apply_to_similar_machines: bool = False

class CalibrationUpdateResponse(BaseModel):
    plug_id: UUID
    plug_name: Optional[str] = None
    power_threshold_running: float
    power_threshold_idle: float
    debounce_seconds: int
    similar_plugs_updated: int = 0
    message: str

# User DTOs
class UserResponse(BaseModel):
    id: UUID
    name: str
    room_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "student"
    is_admin: bool = False
    status: Optional[str] = "approved"  # "pending" | "approved" | "rejected"
    approved_at: Optional[datetime] = None
    university: Optional[str] = None
    college: Optional[str] = None
    hostel: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Smart Plug DTOs
class SmartPlugBase(BaseModel):
    name: Optional[str] = None
    mac_address: Optional[str] = None
    outlet_index: int = 1
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
    name: Optional[str] = None
    mac_address: Optional[str] = None
    outlet_index: Optional[int] = None
    machine_id: Optional[UUID] = None
    provider: Optional[str] = None
    device_id: Optional[str] = None
    local_key: Optional[str] = None
    ip_address: Optional[str] = None
    protocol_version: Optional[str] = None
    power_threshold_running: Optional[float] = None
    power_threshold_idle: Optional[float] = None
    debounce_seconds: Optional[int] = None

# Telemetry DTOs
class TelemetryReadingResponse(BaseModel):
    id: UUID
    plug_id: UUID
    voltage_v: Optional[float] = None
    current_ma: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    switch_on: Optional[bool] = None
    source: Optional[str] = "local"
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TelemetryHistoryPoint(BaseModel):
    timestamp: str
    power_w: float = 0.0
    voltage_v: Optional[float] = None
    current_ma: Optional[float] = None
    source: str = "local"  # "local" | "cloud"

class TelemetryHistoryResponse(BaseModel):
    plug_id: UUID
    plug_name: Optional[str] = None
    hours: int = 4
    peak_power_w: float = 0.0
    avg_power_w: float = 0.0
    local_points_count: int = 0
    cloud_points_count: int = 0
    series: List[TelemetryHistoryPoint] = []

class SmartPlugResponse(SmartPlugBase):
    id: UUID
    machine_id: Optional[UUID] = None
    is_online: bool = False
    last_seen_at: Optional[datetime] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    created_at: datetime
    latest_telemetry: Optional[TelemetryReadingResponse] = None
    model_config = ConfigDict(from_attributes=True)

# Anonymized Student Machine Status Detail (Protects user identity on public view)
class MachineDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_booking: Optional[BookingResponse] = None
    queue: List[QueueResponse] = []
    latest_power_w: Optional[float] = None
    is_plug_online: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)

# Admin Detailed Machine Response (Exposes User Identity + Room Number + Telemetry)
class AdminBookingResponse(BookingResponse):
    user_name: str
    user_email: Optional[str] = None
    room_number: Optional[str] = None

class AdminQueueResponse(QueueResponse):
    user_name: str
    user_email: Optional[str] = None
    room_number: Optional[str] = None

class AdminMachineDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_booking: Optional[AdminBookingResponse] = None
    queue: List[AdminQueueResponse] = []
    smart_plug: Optional[SmartPlugResponse] = None
    latest_telemetry: Optional[TelemetryReadingResponse] = None
    model_config = ConfigDict(from_attributes=True)

class SystemSettingsResponse(BaseModel):
    timezone: str
    default_timezone: str = "Asia/Kolkata"
    server_time_utc: datetime

class SystemSettingsUpdateRequest(BaseModel):
    timezone: str

class OnboardingQrResponse(BaseModel):
    token: str
    hostel_id: str
    ttl_seconds: int = 60
    expires_at: int
    lan_ip: str
    default_url: str

class VerifyQrRequest(BaseModel):
    token: str


