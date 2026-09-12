import asyncio
import datetime
import uuid
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend root is in sys.path (three levels up from backend/scripts/diagnostics/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app.database import Base
from app.models import Machine, Booking, Queue, SmartPlug, TelemetryReading, User
from app.repositories import MachineRepository, SmartPlugRepository, TelemetryRepository, UserRepository
from app.smart_plug_providers.registry import get_provider
from app.smart_plug_providers.base import TelemetryReadingData
from app.telemetry_service import process_plug_telemetry, _low_power_trackers
from app.config import settings

async def run_smart_plug_tests():
    print("==================================================")
    print("   WashQueue Smart Plug & Admin Verification      ")
    print("==================================================")

    # 1. Initialize in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        print("\n--- Test 1: Seed Users & Admin PIN Check ---")
        u1 = User(id=uuid.uuid4(), name="Alex", email="alex@hostel.edu", is_admin=False)
        admin = User(id=uuid.uuid4(), name="Admin", email="admin@hostel.edu", is_admin=True)
        db.add_all([u1, admin])
        await db.commit()

        users = await UserRepository.get_all(db)
        assert len(users) == 2
        print(f"[OK] Users seeded. Admin PIN configured as: '{settings.admin_pin}'")

        print("\n--- Test 2: Smart Plug Provider Registry ---")
        provider = get_provider("tuya_local")
        assert provider is not None
        wipro_provider = get_provider("wipro")
        assert wipro_provider is not None
        print("[OK] Provider registry returned TuyaLocalProvider for 'tuya_local' and 'wipro'.")

        print("\n--- Test 3: Create Machine & Register Smart Plug ---")
        m1 = Machine(name="Washer 1", status="available")
        db.add(m1)
        await db.flush()

        plug = await SmartPlugRepository.create(
            db,
            machine_id=m1.id,
            provider="tuya_local",
            device_id="bf_test_device_12345",
            local_key="1234567890123456",
            ip_address="192.168.1.100",
            protocol_version="3.3",
            power_threshold_running=10.0,
            power_threshold_idle=5.0,
            debounce_seconds=120
        )
        await db.commit()

        plugs = await SmartPlugRepository.get_all(db)
        assert len(plugs) == 1
        assert plugs[0].device_id == "bf_test_device_12345"
        print(f"[OK] Smart plug registered for '{m1.name}' (IP: {plug.ip_address}).")

        print("\n--- Test 4: Mock Telemetry & High Power State Inference ---")
        mock_reading = TelemetryReadingData(
            voltage_v=230.5,
            current_ma=650.0,
            power_w=150.0,
            energy_kwh=1.2,
            switch_on=True,
            raw_dps={"1": True, "18": 650, "19": 150, "20": 2305}
        )

        from app.smart_plug_providers.tuya_local import TuyaLocalProvider
        
        async def mock_get_telemetry(self, *args, **kwargs):
            return current_mock_reading

        current_mock_reading = mock_reading
        TuyaLocalProvider.get_telemetry = mock_get_telemetry

        # Run telemetry processor
        await process_plug_telemetry(db, plug)
        await db.commit()

        # Check machine status
        updated_machine = await MachineRepository.get_by_id(db, m1.id)
        print(f"High power (150W) recorded. Machine status: '{updated_machine.status}'")
        assert updated_machine.status == "in_use"
        assert plug.is_online == True

        # Check recorded telemetry entry in DB
        telemetry = await TelemetryRepository.get_latest_for_plug(db, plug.id)
        assert telemetry is not None
        assert telemetry.power_w == 150.0
        assert telemetry.voltage_v == 230.5
        print(f"[OK] Telemetry stored: {telemetry.voltage_v}V, {telemetry.power_w}W. Machine transitioned to 'in_use'.")

        print("\n--- Test 5: Low Power Soak Debounce Logic ---")
        # Machine drops power below 5W (soak cycle dip)
        current_mock_reading = TelemetryReadingData(
            voltage_v=230.0,
            current_ma=10.0,
            power_w=2.0,
            energy_kwh=1.2,
            switch_on=True,
            raw_dps={"1": True, "18": 10, "19": 2, "20": 2300}
        )

        # First tick: should start soak debounce timer, but machine remains 'in_use'
        await process_plug_telemetry(db, plug)
        await db.commit()

        m_status = (await MachineRepository.get_by_id(db, m1.id)).status
        print(f"Tick 1 (2W power): Machine status: '{m_status}' (Debounce timer started)")
        assert m_status == "in_use"
        assert str(plug.id) in _low_power_trackers

        # Fast-forward low power tracker by 125 seconds (beyond 120s debounce)
        _low_power_trackers[str(plug.id)] = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=125)

        # Second tick: debounce expired -> machine status should transition to 'idle_full'
        await process_plug_telemetry(db, plug)
        await db.commit()

        m_status_after = (await MachineRepository.get_by_id(db, m1.id)).status
        print(f"Tick 2 (125s elapsed): Machine status: '{m_status_after}'")
        assert m_status_after == "idle_full"
        assert str(plug.id) not in _low_power_trackers
        print("[OK] 2-minute soak debounce verified! Machine transitioned to 'idle_full'.")

        print("\n==================================================")
        print("   All Smart Plug & Admin Tests Passed Successfully!  ")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_smart_plug_tests())
