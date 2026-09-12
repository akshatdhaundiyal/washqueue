"""
WashQueue Synthetic Washing Machine Cycle Simulator & Algorithm Benchmark
Generates a realistic multi-phase washing machine power profile without needing
to run a physical machine. 

Simulates:
1. Standby / Pre-cycle (1.0 W)
2. Water Filling / Valve hum (18 W)
3. Main Wash Agitation (180W - 260W oscillating bursts)
4. Soak Period (1.5 W pause for 3 minutes - tests soak debounce!)
5. Rinse & Drain (60W pump + 220W agitation)
6. High-Speed Spin Cycle (400W - 580W peak)
7. End of Cycle / Standby (0.5 W)

Directly writes to washqueue.db (telemetry_readings) and CSV for instant algorithm tuning.
"""

import os
import sys
import time
import math
import random
import datetime
import argparse
import csv
import asyncio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Base dir is backend/ (three levels up from backend/scripts/diagnostics/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app.database import async_session
from app.models import SmartPlug, Machine, TelemetryReading
from sqlalchemy import select

DEFAULT_DEVICE_ID = "d7fa4d27a2883bb4feqvhl"

def generate_cycle_profile(total_minutes: float = 40.0, step_seconds: int = 2):
    """
    Generates time-series data points (time_offset_sec, power_w, voltage_v, current_ma, phase_name).
    """
    total_seconds = int(total_minutes * 60)
    data = []

    # Phase boundaries (fraction of total cycle)
    # 0.00 - 0.05: Standby before start
    # 0.05 - 0.15: Water Fill (18W)
    # 0.15 - 0.40: Wash Agitation (180-260W)
    # 0.40 - 0.55: Deep Soak (1.5W low power)
    # 0.55 - 0.70: Rinse Agitation & Drain (60-220W)
    # 0.70 - 0.90: High-Speed Spin (420-560W)
    # 0.90 - 1.00: Completed / Standby (0.8W)

    base_v = 220.0

    for s in range(0, total_seconds, step_seconds):
        progress = s / total_seconds
        v = round(base_v + random.uniform(-2.5, 2.5), 1)

        if progress < 0.05:
            phase = "Standby"
            p = round(random.uniform(0.5, 1.2), 1)
        elif progress < 0.15:
            phase = "Water Fill"
            p = round(18.0 + random.uniform(-1.5, 1.5), 1)
        elif progress < 0.40:
            phase = "Wash Agitation"
            # Oscillating motor power curve
            osc = math.sin(s * 0.2)
            base_motor = 210.0 + 40.0 * osc
            p = round(max(10.0, base_motor + random.uniform(-15.0, 15.0)), 1)
        elif progress < 0.55:
            phase = "Soak Period"
            # Standby electronics only
            p = round(random.uniform(0.8, 2.2), 1)
        elif progress < 0.70:
            phase = "Rinse & Drain"
            osc = math.sin(s * 0.25)
            p = round(160.0 + 50.0 * osc + random.uniform(-10.0, 10.0), 1)
        elif progress < 0.90:
            phase = "Spin Cycle"
            # Ramp up to peak
            spin_prog = (progress - 0.70) / 0.20
            p = round(320.0 + 220.0 * spin_prog + random.uniform(-15.0, 15.0), 1)
        else:
            phase = "Cycle Complete (Standby)"
            p = round(random.uniform(0.4, 1.0), 1)

        # Approximate current: I = P / V * 1000 (mA)
        ma = round((p / v) * 1000.0, 1) if p > 0 else 0.0

        data.append({
            "offset_sec": s,
            "power_w": p,
            "voltage_v": v,
            "current_ma": ma,
            "phase": phase
        })

    return data


async def simulate_cycle(
    device_id: str = DEFAULT_DEVICE_ID,
    fast_forward: bool = True,
    cycle_minutes: float = 35.0,
    store_db: bool = True
):
    print("=" * 75)
    print("      WashQueue Washing Machine Cycle Simulator & Benchmark Tool     ")
    print("=" * 75)
    print(f"Device ID       : {device_id}")
    print(f"Cycle Duration  : {cycle_minutes} minutes")
    print(f"Execution Mode  : {'FAST-FORWARD (simulated into DB in ~5 seconds)' if fast_forward else 'REAL-TIME (1x)'}")
    print(f"Persist to DB   : {'YES (washqueue.db)' if store_db else 'NO'}")
    print("=" * 75)

    async with async_session() as db:
        res = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
        plug = res.scalar_one_or_none()
        if not plug:
            print(f"[!] SmartPlug with device_id '{device_id}' not found in DB.")
            return

        plug_id = plug.id
        plug_name = plug.name or "Washer Plug"

    profile = generate_cycle_profile(total_minutes=cycle_minutes, step_seconds=2)
    print(f"[*] Generated {len(profile)} high-resolution cycle samples.")

    # Save to CSV
    log_dir = os.path.join(BASE_DIR, "telemetry_logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(log_dir, f"simulated_wash_cycle_{ts}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_iso", "offset_seconds", "power_w", "voltage_v", "current_ma", "phase"])
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=cycle_minutes)
        for pt in profile:
            pt_time = now + datetime.timedelta(seconds=pt["offset_sec"])
            w.writerow([pt_time.isoformat(), pt["offset_sec"], pt["power_w"], pt["voltage_v"], pt["current_ma"], pt["phase"]])

    print(f"[+] Saved synthetic profile to: {csv_path}")

    if store_db:
        print("[*] Inserting simulated telemetry readings into washqueue.db...")
        async with async_session() as db:
            now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=cycle_minutes)
            cum_kwh = 0.0
            entries = []
            for pt in profile:
                pt_time = now + datetime.timedelta(seconds=pt["offset_sec"])
                cum_kwh += (pt["power_w"] * 2.0) / 3600000.0  # 2s step in kWh
                entries.append(TelemetryReading(
                    plug_id=plug_id,
                    voltage_v=pt["voltage_v"],
                    current_ma=pt["current_ma"],
                    power_w=pt["power_w"],
                    energy_kwh=round(cum_kwh, 4),
                    switch_on=True,
                    source="simulated",
                    recorded_at=pt_time
                ))
            db.add_all(entries)
            await db.commit()
            print(f"[+] Successfully persisted {len(entries)} readings to 'telemetry_readings' table in washqueue.db!")

    # Test the algorithm logic against this profile
    print("\n" + "=" * 75)
    print("         EVALUATING INFERENCE ALGORITHM AGAINST THIS DATASET         ")
    print("=" * 75)

    running_threshold = plug.power_threshold_running or 10.0
    idle_threshold = plug.power_threshold_idle or 5.0
    debounce_sec = plug.debounce_seconds or 120

    machine_status = "available"
    state_history = []
    low_power_start = None

    for pt in profile:
        p = pt["power_w"]
        t = pt["offset_sec"]

        if p >= running_threshold:
            low_power_start = None
            if machine_status in ["available", "idle_full"]:
                machine_status = "in_use"
                state_history.append((t, pt["phase"], p, "--> Transition to IN_USE"))

        elif p < idle_threshold:
            if machine_status == "in_use":
                if low_power_start is None:
                    low_power_start = t
                else:
                    elapsed = t - low_power_start
                    if elapsed >= debounce_sec:
                        machine_status = "idle_full"
                        state_history.append((t, pt["phase"], p, f"--> Debounce satisfied ({elapsed}s >= {debounce_sec}s). Transition to IDLE_FULL"))
                        low_power_start = None

    print(f"Configured Running Threshold : {running_threshold} W")
    print(f"Configured Idle Threshold    : {idle_threshold} W")
    print(f"Configured Debounce Window   : {debounce_sec} s")
    print("-" * 75)
    print("State Transitions Detected:")
    for t_sec, phase, p, event in state_history:
        mins = t_sec // 60
        secs = t_sec % 60
        print(f"  [{mins:02d}:{secs:02d}] ({phase:<24} | {p:>5.1f}W)  {event}")

    # Check if soak caused premature trigger
    soak_false_positive = any("Soak Period" in phase for _, phase, _, event in state_history if "IDLE_FULL" in event)
    if soak_false_positive:
        print("\n[!] WARNING: Soak phase triggered a premature IDLE_FULL! Increase debounce_seconds or adjust idle threshold.")
    else:
        print("\n[+] SUCCESS: Soak period did NOT cause a premature completed trigger. Cycle ended cleanly!")

    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="WashQueue Washing Machine Cycle Simulator")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID, help="Tuya Plug Device ID")
    parser.add_argument("--minutes", type=float, default=35.0, help="Cycle duration in minutes (default: 35.0)")
    parser.add_argument("--no-db", action="store_true", help="Do not persist to database")
    args = parser.parse_args()

    asyncio.run(simulate_cycle(
        device_id=args.device_id,
        fast_forward=True,
        cycle_minutes=args.minutes,
        store_db=not args.no_db
    ))

if __name__ == "__main__":
    main()
