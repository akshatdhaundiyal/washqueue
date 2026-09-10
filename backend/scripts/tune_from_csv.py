"""
WashQueue CSV Telemetry Analyzer & Algorithm Tuner
Reads any previously recorded washing machine telemetry CSV file and evaluates:
1. Complete breakdown of phases (Standby, Fill, Agitation, Soak pauses, Drain, Spin).
2. Machine archetype profile.
3. Tests candidate running/idle/debounce settings to verify if any premature "IDLE_FULL" triggers occur.
4. Allows instantly updating the calibration in washqueue.db.
"""

import os
import sys
import csv
import argparse
import datetime
import asyncio

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.database import async_session
from app.models import SmartPlug
from sqlalchemy import select

def load_csv(filepath: str):
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            p_w = float(row.get("power_w", 0.0) or 0.0)
            v_v = float(row.get("voltage_v", 0.0) or 0.0)
            c_ma = float(row.get("current_ma", 0.0) or 0.0)
            t_sec = float(row.get("elapsed_seconds") or row.get("offset_seconds") or 0.0)
            records.append({
                "time_sec": t_sec,
                "power_w": p_w,
                "voltage_v": v_v,
                "current_ma": c_ma,
                "phase": row.get("phase") or row.get("inferred_state", "")
            })
    return records

def analyze_and_simulate(records, test_running=None, test_idle=None, test_debounce=None):
    if not records:
        print("[!] CSV contains no records.")
        return

    powers = [r["power_w"] for r in records]
    duration_sec = records[-1]["time_sec"] - records[0]["time_sec"]
    peak_power = max(powers)

    # Machine Archetype Classification
    active_powers = [p for p in powers if p >= 5.0]
    avg_active = sum(active_powers) / len(active_powers) if active_powers else 0.0

    # Sort powers for baseline standby
    sorted_p = sorted(powers)
    baseline_idle = sum(sorted_p[:max(1, len(sorted_p)//10)]) / max(1, len(sorted_p)//10)

    # Calculate pauses
    in_pause = False
    pause_start = 0.0
    pauses = []
    has_started = False
    idle_ref = test_idle or (baseline_idle + 2.0)
    running_ref = test_running or (baseline_idle + 5.0)

    for r in records:
        p = r["power_w"]
        t = r["time_sec"]
        if p >= running_ref:
            has_started = True
            if in_pause:
                pauses.append((pause_start, t - pause_start))
                in_pause = False
        elif has_started and p < idle_ref:
            if not in_pause:
                in_pause = True
                pause_start = t

    max_pause_sec = max([d for _, d in pauses]) if pauses else 0.0

    # Archetype detection
    if peak_power > 1200.0:
        archetype = "Front-Load with Internal Heater (High Wattage)"
        archetype_icon = "🔥"
    elif max_pause_sec >= 150.0:
        archetype = "Top-Load Pulsator with Deep Soak Cycle (Extended Pause)"
        archetype_icon = "🌀"
    elif max_pause_sec < 90.0 and peak_power <= 600.0:
        archetype = "Direct-Drive Inverter Front-Load (Smooth / Eco)"
        archetype_icon = "🌊"
    else:
        archetype = "Standard Multi-Stage Automatic Washer"
        archetype_icon = "🧺"

    rec_running = round(max(8.0, baseline_idle + 5.0), 1)
    rec_idle = round(max(3.0, baseline_idle + 2.0), 1)
    rec_debounce = max(90, int(max_pause_sec * 1.25) + 15) if max_pause_sec > 0 else 120

    active_run = test_running if test_running is not None else rec_running
    active_idle = test_idle if test_idle is not None else rec_idle
    active_deb = test_debounce if test_debounce is not None else rec_debounce

    print("\n" + "=" * 75)
    print("                    TELEMETRY DATASET PROFILE                        ")
    print("=" * 75)
    print(f"Detected Archetype       : {archetype_icon} {archetype}")
    print(f"Total Recorded Duration  : {duration_sec / 60.0:.1f} minutes ({int(duration_sec)} seconds)")
    print(f"Total Samples            : {len(records)}")
    print(f"Peak Power Observed      : {peak_power:.1f} W")
    print(f"Average Agitation Power  : {avg_active:.1f} W")
    print(f"Standby / Idle Power     : {baseline_idle:.1f} W")
    print(f"Number of Low-Power Pauses: {len(pauses)}")
    print(f"Longest Pause / Soak Window: {max_pause_sec:.1f} seconds ({max_pause_sec/60.0:.1f} min)")

    print("-" * 75)
    print(f"EVALUATING ALGORITHM (Running >= {active_run}W | Idle < {active_idle}W | Debounce = {active_deb}s):")
    print("-" * 75)

    machine_status = "available"
    events = []
    low_start = None

    for r in records:
        p = r["power_w"]
        t = r["time_sec"]

        if p >= active_run:
            low_start = None
            if machine_status in ["available", "idle_full"]:
                machine_status = "in_use"
                events.append((t, p, "--> Transition to IN_USE"))
        elif p < active_idle:
            if machine_status == "in_use":
                if low_start is None:
                    low_start = t
                else:
                    elapsed = t - low_start
                    if elapsed >= active_deb:
                        machine_status = "idle_full"
                        events.append((t, p, f"--> Debounce reached ({int(elapsed)}s >= {active_deb}s). Marked IDLE_FULL"))
                        low_start = None

    for t_sec, p, ev in events:
        mins = int(t_sec // 60)
        secs = int(t_sec % 60)
        print(f"  [{mins:02d}:{secs:02d}] ({p:>5.1f}W)  {ev}")

    # Check if there were multiple IDLE_FULL events before end
    full_events = [e for e in events if "IDLE_FULL" in e[2]]
    if len(full_events) > 1:
        print(f"\n[!] WARNING: Detected {len(full_events)} completion triggers! Debounce ({active_deb}s) is too short.")
        print(f"    Set debounce to at least {rec_debounce}s to eliminate false completion alerts.")
    elif len(full_events) == 1:
        print("\n[+] SUCCESS: Exactly 1 clean completion event detected at cycle end. Zero false alerts!")
    else:
        print("\n[*] Note: No completion trigger fired (cycle may still be active or thresholds need adjustment).")

    print("=" * 75)
    return rec_running, rec_idle, rec_debounce

async def apply_to_db(device_id: str, run_w: float, idle_w: float, deb_s: int):
    async with async_session() as db:
        res = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
        plug = res.scalar_one_or_none()
        if plug:
            plug.power_threshold_running = run_w
            plug.power_threshold_idle = idle_w
            plug.debounce_seconds = deb_s
            await db.commit()
            print(f"[+] Saved calibration to {plug.name} in washqueue.db!")

def main():
    parser = argparse.ArgumentParser(description="WashQueue Offline CSV Telemetry Tuner")
    parser.add_argument("--csv", required=True, help="Path to recorded telemetry CSV file")
    parser.add_argument("--run", type=float, default=None, help="Test running threshold (W)")
    parser.add_argument("--idle", type=float, default=None, help="Test idle threshold (W)")
    parser.add_argument("--debounce", type=int, default=None, help="Test debounce seconds (s)")
    parser.add_argument("--apply-db", default=None, help="Tuya Device ID to apply recommended tuning to")
    args = parser.parse_args()

    records = load_csv(args.csv)
    rec_run, rec_idle, rec_deb = analyze_and_simulate(records, args.run, args.idle, args.debounce)

    if args.apply_db:
        asyncio.run(apply_to_db(args.apply_db, rec_run, rec_idle, rec_deb))

if __name__ == "__main__":
    main()
