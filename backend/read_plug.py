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
plug.set_socketPersistent(True)

status = plug.status()
print("Raw Data:", status)

dps = status.get('dps', {})
print(f"Power: {dps.get('19', 0) / 10.0} W")
print(f"Voltage: {dps.get('20', 0) / 10.0} V")
print(f"Current: {dps.get('18', 0)} mA")