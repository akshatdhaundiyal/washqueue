"""
WashQueue Washing Machine Telemetry Recorder & Threshold Calibration Tool
Continuously records live wattage, current, voltage, and energy readings from
the smart plug (locally via TinyTuya sub-20ms UDP/TCP or cloud fallback).

Outputs to:
1. Live terminal dashboard with real-time status & cycle stage detection.
2. CSV file (in backend/telemetry_logs/) for tuning analysis and graphing.
3. SQLite DB (optional: automatically persisted to telemetry_readings table).

On exit (Ctrl+C):
Calculates baseline idle wattage, agitation/motor power, peak spin power,
longest soak/fill pause duration, and suggests exact algorithm calibration
parameters (power_threshold_running, power_threshold_idle, debounce_seconds).
"""

import sys
import os
import time
import datetime
import argparse
import csv
import asyncio
from typing import Optional, List, Dict, Any

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.smart_plug_providers.tuya_local import TuyaLocalProvider
from app.database import async_session
from app.models import SmartPlug, Machine, TelemetryReading
from sqlalchemy import select

# Default plug credentials detected for device d7fa4d27a2883bb4feqvhl
DEFAULT_DEVICE_ID = "d7fa4d27a2883bb4feqvhl"
DEFAULT_IP = "192.168.1.15"
DEFAULT_KEY = "X@iLAIv|R(t(/(su"
DEFAULT_VERSION = "3.3"


async def ensure_plug_registered(device_id: str, ip: str, key: str, machine_name: Optional[str] = "Washer 1") -> SmartPlug:
    """Finds or registers the smart plug in washqueue.db and links it to a machine."""
    async with async_session() as db:
        res = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
        plug = res.scalar_one_or_none()

        target_machine = None
        if machine_name:
            m_res = await db.execute(select(Machine).where(Machine.name == machine_name))
            target_machine = m_res.scalar_one_or_none()

        if not plug:
            plug = SmartPlug(
                name=f"{machine_name or 'Washer'} Smart Plug",
                device_id=device_id,
                local_key=key,
                ip_address=ip,
                protocol_version=DEFAULT_VERSION,
                power_threshold_running=10.0,
                power_threshold_idle=5.0,
                debounce_seconds=120,
                is_online=True,
                machine_id=target_machine.id if target_machine else None
            )
            db.add(plug)
            await db.commit()
            await db.refresh(plug)
            print(f"[+] Successfully registered plug '{plug.name}' in washqueue.db linked to '{machine_name}'")
        else:
            # Update IP and key if changed
            changed = False
            if plug.ip_address != ip:
                plug.ip_address = ip
                changed = True
            if plug.local_key != key:
                plug.local_key = key
                changed = True
            if target_machine and plug.machine_id != target_machine.id:
                plug.machine_id = target_machine.id
                changed = True
            if changed:
                await db.commit()
                await db.refresh(plug)

        return plug


async def save_telemetry_to_db(plug_id, voltage_v, current_ma, power_w, energy_kwh, switch_on, source="local"):
    """Persists reading to SQLite washqueue.db so frontend dashboard plots it in real-time."""
    try:
        async with async_session() as db:
            entry = TelemetryReading(
                plug_id=plug_id,
                voltage_v=voltage_v,
                current_ma=current_ma,
                power_w=power_w,
                energy_kwh=energy_kwh,
                switch_on=switch_on,
                source=source,
                recorded_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(entry)
            await db.commit()
    except Exception as e:
        # Non-critical for CSV recording
        pass


def analyze_session(records: List[Dict[str, Any]], running_thresh: float, idle_thresh: float):
    """Computes cycle metrics and algorithm tuning recommendations."""
    if not records:
        print("\n[!] No data recorded.")
        return

    powers = [r["power_w"] for r in records if r["power_w"] is not None]
    voltages = [r["voltage_v"] for r in records if r["voltage_v"] is not None]
    currents = [r["current_ma"] for r in records if r["current_ma"] is not None]

    if not powers:
        print("\n[!] No valid power readings received.")
        return

    duration_sec = (records[-1]["timestamp"] - records[0]["timestamp"]).total_seconds()
    peak_power = max(powers)
    min_power = min(powers)
    avg_power = sum(powers) / len(powers)

    # Active readings (above idle threshold)
    active_powers = [p for p in powers if p >= idle_thresh]
    avg_active_power = sum(active_powers) / len(active_powers) if active_powers else 0.0

    # Low-power soak/pause periods during cycle
    in_pause = False
    pause_start = 0.0
    pause_durations = []
    has_started = False

    for i, r in enumerate(records):
        p = r["power_w"] or 0.0
        t = (r["timestamp"] - records[0]["timestamp"]).total_seconds()

        if p >= running_thresh:
            has_started = True
            if in_pause:
                pause_durations.append(t - pause_start)
                in_pause = False
        elif has_started and p < idle_thresh:
            if not in_pause:
                in_pause = True
                pause_start = t

    max_pause_sec = max(pause_durations) if pause_durations else 0.0

    # Baseline idle estimate: lowest 10% of values when plug is ON but washer is idle
    sorted_powers = sorted(powers)
    ten_percent = max(1, len(sorted_powers) // 10)
    baseline_idle = sum(sorted_powers[:ten_percent]) / ten_percent

    # Machine Archetype Classification
    if peak_power > 1200.0:
        archetype = "Front-Load with Internal Water Heater (High Wattage)"
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

    # Suggested tuning
    rec_running = round(max(8.0, baseline_idle + 5.0), 1)
    rec_idle = round(max(3.0, baseline_idle + 2.0), 1)
    # Debounce must exceed the longest observed soak pause with a safety buffer
    rec_debounce = max(90, int(max_pause_sec * 1.25) + 15) if max_pause_sec > 0 else 120

    print("\n" + "=" * 75)
    print("           WASHING MACHINE CYCLE TELEMETRY ANALYSIS REPORT           ")
    print("=" * 75)
    print(f"Detected Machine Profile : {archetype_icon} {archetype}")
    print(f"Total Session Duration   : {duration_sec / 60.0:.1f} minutes ({int(duration_sec)} seconds)")
    print(f"Total Samples Collected  : {len(records)}")
    print(f"Peak Power Draw          : {peak_power:.1f} W (Spin / Heating)")
    print(f"Average Active Power     : {avg_active_power:.1f} W (Motor Agitation)")
    print(f"Baseline Standby Power   : {baseline_idle:.1f} W (Electronics Idle / Off)")
    print(f"Average Voltage          : {sum(voltages)/len(voltages):.1f} V" if voltages else "N/A")
    print(f"Peak Current             : {max(currents):.0f} mA" if currents else "N/A")
    print(f"Longest Soak/Pause Period: {max_pause_sec:.1f} seconds ({max_pause_sec/60.0:.1f} min)")
    print("-" * 75)
    print("RECOMMENDED ALGORITHM TUNING FOR THIS MACHINE:")
    print(f"  • power_threshold_running : {rec_running} W  (power needed to trigger IN_USE)")
    print(f"  • power_threshold_idle    : {rec_idle} W   (power drop threshold that starts soak timer)")
    print(f"  • debounce_seconds        : {rec_debounce} s   (soak buffer to avoid false completion alert)")
    print("=" * 75)
    return rec_running, rec_idle, rec_debounce, archetype


async def main_async():
    parser = argparse.ArgumentParser(description="WashQueue Washing Machine Telemetry Logger")
    parser.add_argument("--device-id", default=DEFAULT_DEVICE_ID, help="Tuya Plug Device ID")
    parser.add_argument("--ip", default=DEFAULT_IP, help="Plug Local IP address")
    parser.add_argument("--key", default=DEFAULT_KEY, help="Plug Local Key")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="Tuya Protocol Version (default 3.3)")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds (default 2.0s)")
    parser.add_argument("--samples", type=int, default=None, help="Stop after N samples (default: run until Ctrl+C)")
    parser.add_argument("--duration", type=float, default=None, help="Stop after N seconds (default: run until Ctrl+C)")
    parser.add_argument("--machine", default="Washer 1", help="Machine name to link in DB")
    parser.add_argument("--csv", default=None, help="Custom CSV output file path")
    parser.add_argument("--no-db", action="store_true", help="Skip writing to washqueue.db")
    args = parser.parse_args()

    # Determine CSV output path
    log_dir = os.path.join(BASE_DIR, "telemetry_logs")
    os.makedirs(log_dir, exist_ok=True)
    if not args.csv:
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_machine = args.machine.lower().replace(" ", "_")
        csv_path = os.path.join(log_dir, f"telemetry_{clean_machine}_{timestamp_str}.csv")
    else:
        csv_path = args.csv

    print("=" * 75)
    print("       WashQueue Washing Machine Telemetry Logger & Algorithm Tuner   ")
    print("=" * 75)
    print(f"Device ID   : {args.device_id}")
    print(f"Local IP    : {args.ip}")
    print(f"Interval    : {args.interval}s")
    print(f"Machine     : {args.machine}")
    print(f"CSV Output  : {csv_path}")
    print(f"Store in DB : {'NO' if args.no_db else 'YES (washqueue.db)'}")
    print("=" * 75)
    sys.stdout.flush()

    plug_record = None
    if not args.no_db:
        print("[*] Verifying plug registration in database...")
        sys.stdout.flush()
        plug_record = await ensure_plug_registered(args.device_id, args.ip, args.key, args.machine)

    provider = TuyaLocalProvider()

    # Open CSV file
    csv_file = open(csv_path, mode="w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "timestamp_iso", "elapsed_seconds", "power_w", "voltage_v", "current_ma",
        "energy_kwh", "switch_on", "source", "inferred_state"
    ])
    csv_file.flush()

    records: List[Dict[str, Any]] = []
    start_time = datetime.datetime.now()
    sample_count = 0

    running_threshold = 10.0
    idle_threshold = 5.0
    if plug_record:
        running_threshold = plug_record.power_threshold_running or 10.0
        idle_threshold = plug_record.power_threshold_idle or 5.0

    print(f"\n[*] Target Running Threshold: {running_threshold} W | Idle Threshold: {idle_threshold} W")
    print("[*] Starting live high-frequency telemetry logging. Press Ctrl+C to finish & view report.\n")
    print(f"{'Time':<10} | {'Power (W)':<10} | {'Voltage (V)':<12} | {'Current (mA)':<13} | {'State':<12} | {'Source'}")
    print("-" * 75)
    sys.stdout.flush()

    async def handle_sample(t_now, p_w, v_v, c_ma, e_kwh, sw_on, src, store_db=False):
        nonlocal sample_count
        elapsed = (t_now - start_time).total_seconds()

        # Instantaneous state
        if p_w >= running_threshold:
            state_str = "RUNNING"
        elif p_w >= idle_threshold:
            state_str = "ACTIVE/SOAK"
        else:
            state_str = "IDLE/OFF"

        sample_count += 1
        time_str = t_now.strftime("%H:%M:%S")

        print(f"{time_str:<10} | {p_w:<10.1f} | {v_v:<12.1f} | {c_ma:<13.0f} | {state_str:<12} | {src}")
        sys.stdout.flush()

        # Write to CSV
        csv_writer.writerow([
            t_now.isoformat(), f"{elapsed:.2f}", p_w, v_v, c_ma, e_kwh, sw_on, src, state_str
        ])
        csv_file.flush()

        records.append({
            "timestamp": t_now,
            "power_w": p_w,
            "voltage_v": v_v,
            "current_ma": c_ma,
            "state": state_str
        })

        if store_db and not args.no_db and plug_record:
            await save_telemetry_to_db(
                plug_record.id, v_v, c_ma, p_w, e_kwh, sw_on, src
            )

    try:
        # Check if backend WebSocket is reachable
        backend_connected = False
        ws_url = "ws://127.0.0.1:8000/ws"
        try:
            import websockets
            import json
            ws_conn = await asyncio.wait_for(websockets.connect(ws_url), timeout=2.0)
            backend_connected = True
            print(f"[*] Connected to live WashQueue Edge WebSocket broadcast ({ws_url}).")
            print("[*] Streaming telemetry without socket collisions or DB query lag.\n")
            sys.stdout.flush()
        except Exception:
            backend_connected = False
            print("[*] Backend WebSocket not reachable. Polling plug directly via persistent socket.\n")
            sys.stdout.flush()

        if backend_connected:
            target_plug_id = str(plug_record.id) if plug_record else None
            async with ws_conn as ws:
                while True:
                    t_now = datetime.datetime.now()
                    elapsed = (t_now - start_time).total_seconds()
                    if args.duration and elapsed >= args.duration:
                        print(f"\n[*] Target duration ({args.duration}s) reached.")
                        break
                    if args.samples and sample_count >= args.samples:
                        print(f"\n[*] Target samples ({args.samples}) reached.")
                        break

                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw_msg)
                        if msg.get("type") == "telemetry_update":
                            # Filter by plug ID if known, otherwise take first telemetry packet
                            msg_plug_id = msg.get("plug_id")
                            if not target_plug_id or msg_plug_id == target_plug_id:
                                tel = msg.get("telemetry", {})
                                p_w = float(tel.get("power_w") or 0.0)
                                v_v = float(tel.get("voltage_v") or 0.0)
                                c_ma = float(tel.get("current_ma") or 0.0)
                                e_kwh = float(tel.get("energy_kwh") or 0.0)
                                sw_on = tel.get("switch_on", True)
                                src = tel.get("source", "ws-stream")
                                await handle_sample(t_now, p_w, v_v, c_ma, e_kwh, sw_on, src, store_db=False)
                    except asyncio.TimeoutError:
                        # Heartbeat ping
                        try:
                            await ws.send("ping")
                        except Exception:
                            print("\n[!] WebSocket disconnected. Switching to direct local socket polling...")
                            backend_connected = False
                            break
        
        # Fallback to direct polling if backend was not connected or disconnected
        if not backend_connected:
            while True:
                t_now = datetime.datetime.now()
                elapsed = (t_now - start_time).total_seconds()
                if args.duration and elapsed >= args.duration:
                    print(f"\n[*] Target duration ({args.duration}s) reached.")
                    break
                if args.samples and sample_count >= args.samples:
                    print(f"\n[*] Target samples ({args.samples}) reached.")
                    break

                telemetry = await provider.get_telemetry(
                    device_id=args.device_id,
                    local_key=args.key,
                    ip_address=args.ip,
                    protocol_version=args.version
                )
                p_w = telemetry.power_w or 0.0
                v_v = telemetry.voltage_v or 0.0
                c_ma = telemetry.current_ma or 0.0
                e_kwh = telemetry.energy_kwh or 0.0
                sw_on = telemetry.switch_on if telemetry.switch_on is not None else True
                src = getattr(telemetry, "source", "local") or "local"

                await handle_sample(t_now, p_w, v_v, c_ma, e_kwh, sw_on, src, store_db=True)
                await asyncio.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n[*] Recording stopped by user.")
    finally:
        csv_file.close()
        print(f"[+] All {sample_count} telemetry samples successfully saved to:\n    {csv_path}")
        tuning = analyze_session(records, running_threshold, idle_threshold)
        if tuning and plug_record and not args.no_db and len(records) >= 10:
            rec_run, rec_idle, rec_debounce, _ = tuning
            async with async_session() as db:
                res = await db.execute(select(SmartPlug).where(SmartPlug.id == plug_record.id))
                p = res.scalar_one_or_none()
                if p:
                    p.power_threshold_running = rec_run
                    p.power_threshold_idle = rec_idle
                    p.debounce_seconds = rec_debounce
                    await db.commit()
                    print(f"\n[+] Auto-calibrated {p.name} in washqueue.db:")
                    print(f"    • Running Threshold : {rec_run} W")
                    print(f"    • Idle Threshold    : {rec_idle} W")
                    print(f"    • Soak Debounce     : {rec_debounce} s")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
