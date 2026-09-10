import asyncio
import datetime
import logging
from typing import Dict, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.database import async_session
    from app.models import SmartPlug, Machine, TelemetryReading, Booking
    from app.smart_plug_providers.registry import get_provider
    from app.websocket_manager import ws_manager
    from app.cloud_sync_service import CloudSyncService
except ImportError:
    from .database import async_session
    from .models import SmartPlug, Machine, TelemetryReading, Booking
    from .smart_plug_providers.registry import get_provider
    from .websocket_manager import ws_manager
    from .cloud_sync_service import CloudSyncService

logger = logging.getLogger("washqueue-telemetry-service")
logger.setLevel(logging.INFO)

# In-memory tracking for soak cycle debounce: plug_id -> datetime when power dropped below threshold
_low_power_trackers: Dict[str, datetime.datetime] = {}

async def poll_all_smart_plugs():
    """
    Main loop iteration: polls all registered smart plugs, records telemetry,
    and updates washing machine states using debounce logic.
    """
    async with async_session() as db:
        try:
            # Fetch all smart plugs
            result = await db.execute(select(SmartPlug))
            plugs = list(result.scalars().all())
            
            for plug in plugs:
                await process_plug_telemetry(db, plug)
                
            await db.commit()
        except Exception as e:
            logger.error(f"Error during telemetry polling tick: {e}")
            await db.rollback()

async def process_plug_telemetry(db: AsyncSession, plug: SmartPlug):
    plug_id_str = str(plug.id)
    try:
        provider = get_provider(plug.provider)
        reading = await provider.get_telemetry(
            device_id=plug.device_id,
            local_key=plug.local_key,
            ip_address=plug.ip_address,
            protocol_version=plug.protocol_version
        )
        
        now = datetime.datetime.now(datetime.timezone.utc)
        is_online = reading.raw_dps is not None and "error" not in reading.raw_dps
        
        # 1. Update plug online & health state
        plug.is_online = is_online
        if is_online:
            plug.last_seen_at = now
            plug.consecutive_failures = 0
            plug.last_error = None
        else:
            plug.consecutive_failures = (plug.consecutive_failures or 0) + 1
            if isinstance(reading.raw_dps, dict) and "error" in reading.raw_dps:
                plug.last_error = str(reading.raw_dps["error"])
            else:
                plug.last_error = "Device unreachable"

        # 2. Record telemetry reading if online or error payload
        source_tag = getattr(reading, "source", "local") or "local"
        telemetry_entry = TelemetryReading(
            plug_id=plug.id,
            voltage_v=reading.voltage_v,
            current_ma=reading.current_ma,
            power_w=reading.power_w,
            energy_kwh=reading.energy_kwh,
            switch_on=reading.switch_on,
            source=source_tag,
            recorded_at=now
        )
        db.add(telemetry_entry)

        # Broadcast real-time telemetry update over WebSocket to connected Admin dashboards (< 10ms)
        asyncio.create_task(ws_manager.broadcast({
            "type": "telemetry_update",
            "plug_id": str(plug.id),
            "is_online": is_online,
            "telemetry": {
                "voltage_v": reading.voltage_v,
                "current_ma": reading.current_ma,
                "power_w": reading.power_w,
                "energy_kwh": reading.energy_kwh,
                "switch_on": reading.switch_on,
                "source": source_tag,
                "recorded_at": now.isoformat()
            }
        }))

        # 3. State Inference Logic (if plug is mapped to a machine)
        if plug.machine_id and is_online and reading.power_w is not None:
            machine_result = await db.execute(select(Machine).where(Machine.id == plug.machine_id))
            machine = machine_result.scalar_one_or_none()
            
            if machine:
                power = reading.power_w
                running_threshold = plug.power_threshold_running or 10.0
                idle_threshold = plug.power_threshold_idle or 5.0
                debounce_sec = plug.debounce_seconds or 120

                # High power draw detected: Machine is actively running
                if power >= running_threshold:
                    _low_power_trackers.pop(plug_id_str, None)
                    if machine.status in ["available", "idle_full"]:
                        logger.info(f"⚡ Power spike ({power}W >= {running_threshold}W) on {machine.name}. Setting status to 'in_use'.")
                        machine.status = "in_use"
                        
                        # Trigger local WebSocket broadcast & Cloud Sync
                        asyncio.create_task(ws_manager.broadcast({
                            "type": "machine_status_change",
                            "machine_id": str(machine.id),
                            "machine_name": machine.name,
                            "status": "in_use",
                            "power_w": power
                        }))
                        asyncio.create_task(CloudSyncService.queue_event("machine_status_change", {
                            "machine_id": str(machine.id),
                            "machine_name": machine.name,
                            "status": "in_use",
                            "power_w": power
                        }))

                # Low power draw: Machine might have finished, or is soaking
                elif power < idle_threshold:
                    if machine.status == "in_use":
                        if plug_id_str not in _low_power_trackers:
                            _low_power_trackers[plug_id_str] = now
                            logger.info(f"⏳ Low power ({power}W < {idle_threshold}W) on {machine.name}. Starting {debounce_sec}s soak debounce window.")
                        else:
                            elapsed = (now - _low_power_trackers[plug_id_str]).total_seconds()
                            if elapsed >= debounce_sec:
                                logger.info(f"✅ Debounce complete ({elapsed:.1f}s >= {debounce_sec}s) for {machine.name}. Setting status to 'idle_full'.")
                                machine.status = "idle_full"
                                _low_power_trackers.pop(plug_id_str, None)

                                asyncio.create_task(ws_manager.broadcast({
                                    "type": "machine_status_change",
                                    "machine_id": str(machine.id),
                                    "machine_name": machine.name,
                                    "status": "idle_full",
                                    "power_w": power
                                }))
                                asyncio.create_task(CloudSyncService.queue_event("machine_status_change", {
                                    "machine_id": str(machine.id),
                                    "machine_name": machine.name,
                                    "status": "idle_full",
                                    "power_w": power
                                }))
                    else:
                        _low_power_trackers.pop(plug_id_str, None)
                else:
                    _low_power_trackers.pop(plug_id_str, None)

    except Exception as e:
        logger.error(f"Failed to process smart plug {plug.device_id} ({plug.ip_address}): {e}")

async def start_telemetry_polling_loop(interval_seconds: int = 1):
    """
    Background worker loop for polling smart plugs.
    """
    logger.info(f"Starting WashQueue local smart plug telemetry service (interval: {interval_seconds}s)...")
    while True:
        try:
            await poll_all_smart_plugs()
        except Exception as e:
            logger.error(f"Unhandled exception in telemetry loop: {e}")
        await asyncio.sleep(interval_seconds)
