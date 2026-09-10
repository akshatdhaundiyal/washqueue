import os
import tinytuya
from dotenv import load_dotenv

# Load configuration from .env
load_dotenv()

DEVICE_ID = os.getenv("TUYA_DEVICE_ID")
IP_ADDRESS = os.getenv("TUYA_DEVICE_IP")
LOCAL_KEY = os.getenv("TUYA_LOCAL_KEY")
VERSION = float(os.getenv("TUYA_VERSION", "3.3"))

if not all([DEVICE_ID, IP_ADDRESS, LOCAL_KEY]):
    print("[-] Error: Missing required Tuya credentials in .env (TUYA_DEVICE_ID, TUYA_DEVICE_IP, TUYA_LOCAL_KEY).")
    exit(1)

plug = tinytuya.OutletDevice(DEVICE_ID, IP_ADDRESS, LOCAL_KEY, version=VERSION)
plug.set_socketTimeout(3)
plug.set_socketRetryLimit(1)

status = plug.status()
print("Raw Data:", status)

if isinstance(status, dict) and 'dps' in status:
    dps = status.get('dps', {})
    print(f"Power:   {dps.get('19', 0) / 10.0} W")
    print(f"Voltage: {dps.get('20', 0) / 10.0} V")
    print(f"Current: {dps.get('18', 0)} mA")
else:
    print("\n[!] Local LAN query timed out or device unreachable at", IP_ADDRESS)
    print("[*] Checking Tuya Cloud API...")
    try:
        c = tinytuya.Cloud(
            apiRegion=os.getenv("TUYA_REGION", "in"),
            apiKey=os.getenv("TUYA_ACCESS_ID"),
            apiSecret=os.getenv("TUYA_ACCESS_SECRET")
        )
        c_status = c.getstatus(DEVICE_ID)
        if c_status.get("success"):
            print("Cloud Status Data:", c_status.get("result"))
            for item in c_status.get("result", []):
                code, val = item.get("code"), item.get("value")
                if code == "cur_voltage":
                    print(f"Voltage: {val / 10.0} V")
                elif code == "cur_power":
                    print(f"Power:   {val / 10.0} W")
                elif code == "cur_current":
                    print(f"Current: {val} mA")
                elif code == "switch_1":
                    print(f"Switch:  {'ON' if val else 'OFF'}")
    except Exception as e:
        print("Cloud query error:", e)