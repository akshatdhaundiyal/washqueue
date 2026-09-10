"""
WashQueue Historical Telemetry Exporter
Exports stored time-series telemetry from SQLite (washqueue.db) to CSV or JSON
for washing machine algorithm tuning and offline analysis.
"""

import os
import sys
import csv
import json
import argparse
import datetime
import asyncio

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import async_session
from app.models import SmartPlug, TelemetryReading, Machine
from sqlalchemy import select

async def export_telemetry(device_id: str = None, hours: int = 24, format: str = "csv", output_file: str = None):
    async with async_session() as db:
        query = select(SmartPlug)
        if device_id:
            query = query.where(SmartPlug.device_id == device_id)
        
        plugs = (await db.execute(query)).scalars().all()
        if not plugs:
            print(f"[!] No smart plugs found matching device_id: {device_id}")
            return

        for plug in plugs:
            # Fetch machine name
            machine_name = "Unassigned"
            if plug.machine_id:
                m = (await db.execute(select(Machine).where(Machine.id == plug.machine_id))).scalar_one_or_none()
                if m:
                    machine_name = m.name

            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
            t_query = (
                select(TelemetryReading)
                .where(TelemetryReading.plug_id == plug.id)
                .where(TelemetryReading.recorded_at >= cutoff)
                .order_by(TelemetryReading.recorded_at.asc())
            )
            readings = (await db.execute(t_query)).scalars().all()

            if not readings:
                print(f"[*] Plug '{plug.name}' ({plug.device_id}) has 0 readings in the last {hours} hours.")
                continue

            # Determine filename
            os.makedirs(os.path.join(BASE_DIR, "telemetry_logs"), exist_ok=True)
            if not output_file:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(BASE_DIR, "telemetry_logs", f"export_{plug.device_id}_{ts}.{format}")
            else:
                filename = output_file

            if format == "csv":
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["timestamp_iso", "voltage_v", "current_ma", "power_w", "energy_kwh", "switch_on", "source"])
                    for r in readings:
                        w.writerow([
                            r.recorded_at.isoformat() if r.recorded_at else "",
                            r.voltage_v, r.current_ma, r.power_w, r.energy_kwh, r.switch_on, r.source
                        ])
            else:
                data = [{
                    "timestamp": r.recorded_at.isoformat() if r.recorded_at else "",
                    "voltage_v": r.voltage_v,
                    "current_ma": r.current_ma,
                    "power_w": r.power_w,
                    "energy_kwh": r.energy_kwh,
                    "switch_on": r.switch_on,
                    "source": r.source
                } for r in readings]
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

            print(f"[+] Exported {len(readings)} points for '{plug.name}' ({machine_name}) -> {filename}")

def main():
    parser = argparse.ArgumentParser(description="Export WashQueue Telemetry Data")
    parser.add_argument("--device-id", default=None, help="Tuya Plug Device ID (exports all if omitted)")
    parser.add_argument("--hours", type=int, default=24, help="Export data from the last N hours (default: 24)")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format (default: csv)")
    parser.add_argument("--out", default=None, help="Custom output file path")
    args = parser.parse_args()

    asyncio.run(export_telemetry(args.device_id, args.hours, args.format, args.out))

if __name__ == "__main__":
    main()
