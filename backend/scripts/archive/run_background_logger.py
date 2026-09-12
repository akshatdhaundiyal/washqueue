"""
WashQueue Continuous Smart Plug Background Telemetry Logger [ARCHIVED]
NOTE: Superseded by scripts/record_telemetry.py which connects via native
WebSocket with auto-reconnect, CSV flushing, and auto-calibration.
"""

import os
import sys
import time
import datetime
import argparse
import asyncio
import logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Base dir is backend/ (three levels up from backend/scripts/archive/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import async_session
from app.models import SmartPlug, TelemetryReading
from app.smart_plug_providers.tuya_local import TuyaLocalProvider
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("washqueue-bg-logger")

DEFAULT_DEVICE_ID = "d7fa4d27a2883bb4feqvhl"
DEFAULT_IP = "192.168.1.15"
DEFAULT_KEY = "X@iLAIv|R(t(/(su"
DEFAULT_VERSION = "3.3"

async def background_logger_loop(device_id: str, ip: str, key: str, version: str, interval: float):
    logger.info(f"Starting continuous telemetry logger for plug {device_id} ({ip}) every {interval}s...")

    async with async_session() as db:
        res = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
        plug = res.scalar_one_or_none()
        if not plug:
            logger.error(f"Plug {device_id} not found in database. Run record_telemetry.py or register it first.")
            return
        plug_id = plug.id
        plug_name = plug.name

    provider = TuyaLocalProvider()

    while True:
        try:
            telemetry = await provider.get_telemetry(
                device_id=device_id,
                local_key=key,
                ip_address=ip,
                protocol_version=version
            )

            p_w = telemetry.power_w or 0.0
            v_v = telemetry.voltage_v or 0.0
            c_ma = telemetry.current_ma or 0.0
            e_kwh = telemetry.energy_kwh or 0.0
            sw_on = telemetry.switch_on if telemetry.switch_on is not None else True
            src = getattr(telemetry, "source", "local") or "local"

            now = datetime.datetime.now(datetime.timezone.utc)

            async with async_session() as db:
                entry = TelemetryReading(
                    plug_id=plug_id,
                    voltage_v=v_v,
                    current_ma=c_ma,
                    power_w=p_w,
                    energy_kwh=e_kwh,
                    switch_on=sw_on,
                    source=src,
                    recorded_at=now
                )
                db.add(entry)
                await db.commit()

        except Exception as e:
            logger.warning(f"Error reading telemetry: {e}")

        await asyncio.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="WashQueue Continuous Background Logger")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID)
    parser.add_argument("--ip", default=DEFAULT_IP)
    parser.add_argument("--key", default=DEFAULT_KEY)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds (default: 2.0s)")
    args = parser.parse_args()

    try:
        asyncio.run(background_logger_loop(args.device_id, args.ip, args.key, args.version, args.interval))
    except KeyboardInterrupt:
        logger.info("Background logger stopped by user.")

if __name__ == "__main__":
    main()
