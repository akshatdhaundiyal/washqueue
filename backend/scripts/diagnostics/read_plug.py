import os
import sys
import json
import urllib.request
import asyncio
from dotenv import load_dotenv

# Load configuration from .env (three levels up from backend/scripts/diagnostics/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))
sys.path.insert(0, BASE_DIR)

from app.smart_plug_providers.tuya_local import TuyaLocalProvider

DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
IP_ADDRESS = os.getenv("TUYA_DEVICE_IP")
LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY")
VERSION = os.getenv("TUYA_VERSION", "3.3")

if not all([DEVICE_ID, IP_ADDRESS, LOCAL_KEY]):
    print("[-] Error: Missing required Tuya credentials in .env (TUYA_DEVICE_ID, TUYA_DEVICE_IP, TUYA_LOCAL_KEY).")
    exit(1)

def check_backend_running():
    """Checks if the WashQueue FastAPI backend is running locally."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/smart-plugs",
            headers={"User-Agent": "WashQueue-CLI", "X-Admin-PIN": "1234"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                return data
    except Exception:
        pass
    return None

async def main():
    print("=" * 60)
    print("  WashQueue Smart Plug Diagnostic Tool (Smart Dual-Mode)")
    print("=" * 60)
    print(f"Target Device ID: {DEVICE_ID}")
    print(f"Target IP:        {IP_ADDRESS}\n")

    # 1. Check if backend is active to avoid port 6668 collision
    backend_plugs = check_backend_running()
    if backend_plugs is not None:
        print("[*] Detected active WashQueue backend at http://127.0.0.1:8000")
        print("[*] Reading telemetry directly through backend API (zero port 6668 collision)...")
        matching = next((p for p in backend_plugs if p.get("device_id") == DEVICE_ID), None)
        if matching:
            print(f"Plug Name:     {matching.get('name')}")
            print(f"Online Status: {'ONLINE' if matching.get('is_online') else 'OFFLINE'}")
            print(f"Power:         {matching.get('power_w', 0.0)} W")
            print(f"Voltage:       {matching.get('voltage_v', 0.0)} V")
            print(f"Current:       {matching.get('current_ma', 0.0)} mA")
            print(f"Switch State:  {'ON' if matching.get('switch_on') else 'OFF'}")
            print(f"Telemetry Src: {matching.get('source', 'local')}")
            print("\n[+] Read successfully from backend without socket collisions.")
            return
        else:
            print(f"[-] Device {DEVICE_ID} not registered in backend database. Falling back to direct socket...")

    # 2. Standalone mode: Direct query using TuyaLocalProvider
    print("[*] Running standalone direct query via TuyaLocalProvider...")
    provider = TuyaLocalProvider()
    reading = await provider.get_telemetry(
        device_id=DEVICE_ID,
        local_key=LOCAL_KEY,
        ip_address=IP_ADDRESS,
        protocol_version=VERSION
    )

    if reading.raw_dps and "error" not in reading.raw_dps:
        print("\n[+] Telemetry Received:")
        print(f"Power:         {reading.power_w or 0.0} W")
        print(f"Voltage:       {reading.voltage_v or 0.0} V")
        print(f"Current:       {reading.current_ma or 0.0} mA")
        print(f"Switch State:  {'ON' if reading.switch_on else 'OFF'}")
        print(f"Telemetry Src: {reading.source}")
        print(f"Raw DPS:       {reading.raw_dps}")
    else:
        print(f"\n[-] Query returned error: {reading.raw_dps}")

if __name__ == "__main__":
    asyncio.run(main())
