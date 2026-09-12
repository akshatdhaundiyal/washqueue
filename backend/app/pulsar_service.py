import asyncio
import base64
import hashlib
import json
import logging
import os
import ssl
import sys
import threading
import time
from typing import Optional, Callable
from Crypto.Cipher import AES

try:
    from app.database import async_session
    from app.models import SmartPlug, Machine, TelemetryReading
    from app.websocket_manager import ws_manager
    from app.cloud_sync_service import CloudSyncService
    import datetime
except ImportError:
    from database import async_session
    from models import SmartPlug, Machine, TelemetryReading
    from websocket_manager import ws_manager
    from cloud_sync_service import CloudSyncService
    import datetime

logger = logging.getLogger("washqueue-pulsar")
logger.setLevel(logging.INFO)

MQ_ENDPOINTS = {
    "in": "wss://mqe.tuyain.com:8285/",
    "cn": "wss://mqe.tuyacn.com:8285/",
    "us": "wss://mqe.tuyaus.com:8285/",
    "ue": "wss://mqe-ue.tuyaus.com:8285/",
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "we": "wss://mqe-we.tuyaeu.com:8285/",
}

class TuyaPulsarService:
    """
    Background Service that connects to Tuya Pulsar WebSocket Message Queue
    and streams live device updates directly into the WashQueue database and WebSockets.
    """

    def __init__(self, access_id: str, access_secret: str, region: str = "in"):
        self.access_id = access_id
        self.access_secret = access_secret
        self.region = region.lower()
        self.endpoint = MQ_ENDPOINTS.get(self.region, "wss://mqe.tuyain.com:8285/")
        self._pulsar_thread = None
        self._loop = None

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Starts the Pulsar listener thread."""
        try:
            from tuya_connector import TuyaOpenPulsar, TuyaCloudPulsarTopic
        except ImportError:
            logger.error("tuya-connector-python is not installed. Install via `uv add tuya-connector-python`.")
            return

        self._loop = loop or asyncio.get_event_loop()
        
        self.pulsar = TuyaOpenPulsar(
            access_id=self.access_id,
            access_secret=self.access_secret,
            ws_endpoint=self.endpoint,
            topic=TuyaCloudPulsarTopic.PROD
        )
        self.pulsar.add_message_listener(self._on_raw_message)
        logger.info(f"Connecting Tuya Pulsar service ({self.region.upper()} -> {self.endpoint})...")
        self.pulsar.start()

    def stop(self):
        if hasattr(self, 'pulsar') and self.pulsar:
            self.pulsar.stop()
            logger.info("Tuya Pulsar service stopped.")

    def _on_raw_message(self, decrypted_json_str: str):
        try:
            data = json.loads(decrypted_json_str)
            dev_id = data.get("devId") or data.get("nodeId")
            status_list = data.get("status", [])
            
            if not dev_id or not status_list:
                return

            dps_dict = {item.get("code"): item.get("value") for item in status_list if "code" in item}
            
            cloud_t = data.get("t") or data.get("time")
            
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._process_dps_event(dev_id, dps_dict, cloud_t),
                    self._loop
                )
        except Exception as e:
            logger.error(f"Error handling Pulsar message: {e}")

    async def _process_dps_event(self, device_id: str, dps: dict, cloud_t: Optional[Any] = None):
        from sqlalchemy import select

        async with async_session() as db:
            try:
                # Find matching smart plug in database
                res = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
                plug = res.scalar_one_or_none()
                if not plug:
                    return

                offset_sec = float(os.getenv("TUYA_CLOUD_TIME_OFFSET_SECONDS", "0.0") or 0.0)
                if cloud_t:
                    try:
                        now = datetime.datetime.fromtimestamp((float(cloud_t) / 1000.0) + offset_sec, tz=datetime.timezone.utc)
                    except Exception:
                        now = datetime.datetime.now(datetime.timezone.utc)
                else:
                    now = datetime.datetime.now(datetime.timezone.utc)

                plug.is_online = True
                plug.last_seen_at = now

                # Parse readings
                power_w = (dps.get("cur_power") / 10.0) if "cur_power" in dps and dps["cur_power"] is not None else None
                voltage_v = (dps.get("cur_voltage") / 10.0) if "cur_voltage" in dps and dps["cur_voltage"] is not None else None
                current_ma = float(dps["cur_current"]) if "cur_current" in dps and dps["cur_current"] is not None else None
                energy_kwh = (dps.get("add_ele") / 1000.0) if "add_ele" in dps and dps["add_ele"] is not None else None
                switch_on = dps.get("switch_1")

                # Record Telemetry
                entry = TelemetryReading(
                    plug_id=plug.id,
                    voltage_v=voltage_v,
                    current_ma=current_ma,
                    power_w=power_w,
                    energy_kwh=energy_kwh,
                    switch_on=switch_on,
                    source="cloud",
                    recorded_at=now
                )
                db.add(entry)

                # Machine status logic if mapped
                if plug.machine_id and power_w is not None:
                    m_res = await db.execute(select(Machine).where(Machine.id == plug.machine_id))
                    machine = m_res.scalar_one_or_none()
                    if machine:
                        running_th = plug.power_threshold_running or 10.0
                        if power_w >= running_th and machine.status in ["available", "idle_full"]:
                            machine.status = "in_use"
                            await ws_manager.broadcast({
                                "type": "machine_status_change",
                                "machine_id": str(machine.id),
                                "machine_name": machine.name,
                                "status": "in_use",
                                "power_w": power_w
                            })

                await db.commit()
                logger.info(f"⚡ Pulsar update for plug {plug.name}: Power={power_w}W, Switch={switch_on}")

            except Exception as e:
                logger.error(f"Error persisting Pulsar telemetry: {e}")
                await db.rollback()
