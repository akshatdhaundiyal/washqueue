import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, Uuid, UniqueConstraint, Index
from sqlalchemy.orm import relationship

try:
    from app.database import Base
except ImportError:
    from .database import Base

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="available")

    bookings = relationship("Booking", back_populates="machine", cascade="all, delete-orphan")
    queue_entries = relationship("Queue", back_populates="machine", cascade="all, delete-orphan")
    smart_plug = relationship("SmartPlug", back_populates="machine", uselist=False)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(Uuid(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    estimated_end_at = Column(DateTime(timezone=True), nullable=False)
    cleared_at = Column(DateTime(timezone=True), nullable=True)

    machine = relationship("Machine", back_populates="bookings")

class Queue(Base):
    __tablename__ = "queue"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(Uuid(as_uuid=True), ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    position = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="waiting")

    machine = relationship("Machine", back_populates="queue_entries")

class SmartPlug(Base):
    __tablename__ = "smart_plugs"
    __table_args__ = (
        UniqueConstraint("machine_id", name="uq_smart_plugs_machine_id"),
        UniqueConstraint("mac_address", "outlet_index", name="uq_smart_plugs_mac_outlet"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(Uuid(as_uuid=True), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=True)
    mac_address = Column(String, nullable=True, index=True)
    outlet_index = Column(Integer, nullable=False, default=1)
    provider = Column(String, nullable=False, default="tuya_local")
    device_id = Column(String, nullable=False, index=True)
    local_key = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    protocol_version = Column(String, nullable=False, default="3.3")
    power_threshold_running = Column(Float, nullable=False, default=10.0)
    power_threshold_idle = Column(Float, nullable=False, default=5.0)
    debounce_seconds = Column(Integer, nullable=False, default=120)
    is_online = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    machine = relationship("Machine", back_populates="smart_plug")
    telemetry_readings = relationship("TelemetryReading", back_populates="smart_plug", cascade="all, delete-orphan")

class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    __table_args__ = (
        Index("ix_telemetry_plug_recorded_at", "plug_id", "recorded_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plug_id = Column(Uuid(as_uuid=True), ForeignKey("smart_plugs.id", ondelete="CASCADE"), nullable=False)
    voltage_v = Column(Float, nullable=True)
    current_ma = Column(Float, nullable=True)
    power_w = Column(Float, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    switch_on = Column(Boolean, nullable=True)
    source = Column(String, nullable=True, default="local")  # "local" (socket/WS) or "cloud" (Tuya OpenAPI)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    smart_plug = relationship("SmartPlug", back_populates="telemetry_readings")

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    room_number = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)
    hashed_password = Column(String, nullable=True)
    role = Column(String, nullable=False, default="student")  # "student" | "admin"
    is_admin = Column(Boolean, nullable=False, default=False)
    university = Column(String, nullable=True)
    college = Column(String, nullable=True)
    hostel = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


