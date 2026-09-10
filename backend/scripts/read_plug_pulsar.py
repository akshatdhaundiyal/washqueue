import json
import logging
import time
import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tuya_connector import TuyaOpenPulsar, TuyaCloudPulsarTopic
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tuya-pulsar")

# Load configuration from environment variables or tinytuya.json
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "tinytuya.json")
if os.getenv("TUYA_ACCESS_ID"):
    ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "")
    ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET", "")
    REGION = os.getenv("TUYA_REGION", "in").lower()
    TARGET_DEVICE_ID = os.getenv("TUYA_DEVICE_ID", "").strip()
elif os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    ACCESS_ID = config.get("apiKey", "")
    ACCESS_SECRET = config.get("apiSecret", "")
    REGION = config.get("apiRegion", "in").lower()
    TARGET_DEVICE_ID = config.get("apiDeviceID", "").strip()
else:
    ACCESS_ID = ""
    ACCESS_SECRET = ""
    REGION = "in"
    TARGET_DEVICE_ID = ""

# Tuya Pulsar MQ Endpoints by region
MQ_ENDPOINTS = {
    "in": "wss://mqe.tuyain.com:8285/",
    "cn": "wss://mqe.tuyacn.com:8285/",
    "us": "wss://mqe.tuyaus.com:8285/",
    "ue": "wss://mqe-ue.tuyaus.com:8285/",
    "eu": "wss://mqe.tuyaeu.com:8285/",
    "we": "wss://mqe-we.tuyaeu.com:8285/",
}

MQ_ENDPOINT = MQ_ENDPOINTS.get(REGION, "wss://mqe.tuyain.com:8285/")

print("=" * 60)
print("[*] WashQueue Tuya Pulsar Message Queue Client")
print(f"Region: {REGION.upper()} -> {MQ_ENDPOINT}")
print(f"Access ID: {ACCESS_ID[:6]}...{ACCESS_ID[-4:] if len(ACCESS_ID) > 10 else ''}")
print("=" * 60)

def on_message(message_str: str):
    """
    Callback triggered whenever a decrypted message is received from Tuya Pulsar MQ.
    """
    try:
        data = json.loads(message_str)
        dev_id = data.get("devId") or data.get("nodeId")
        biz_code = data.get("bizCode")
        status_list = data.get("status", [])

        print(f"\n[EVENT] Device: {dev_id} | BizCode: {biz_code}")
        
        # Parse standard Tuya DPS status updates
        dps_dict = {}
        for item in status_list:
            code = item.get("code")
            val = item.get("value")
            dps_dict[code] = val

        if dps_dict:
            print("  [Telemetry Status]:")
            if "switch_1" in dps_dict:
                print(f"     Switch State: {'ON [Active]' if dps_dict['switch_1'] else 'OFF [Inactive]'}")
            if "cur_power" in dps_dict:
                power_w = dps_dict["cur_power"] / 10.0
                print(f"     Active Power: {power_w:.1f} W")
            if "cur_voltage" in dps_dict:
                voltage_v = dps_dict["cur_voltage"] / 10.0
                print(f"     Voltage:      {voltage_v:.1f} V")
            if "cur_current" in dps_dict:
                current_ma = dps_dict["cur_current"]
                print(f"     Current:      {current_ma} mA")
            if "add_ele" in dps_dict:
                energy_kwh = dps_dict["add_ele"] / 1000.0
                print(f"     Total Energy: {energy_kwh:.3f} kWh")
            
            other_keys = {k: v for k, v in dps_dict.items() if k not in ["switch_1", "cur_power", "cur_voltage", "cur_current", "add_ele"]}
            if other_keys:
                print(f"     Other DPS:    {other_keys}")
        else:
            print(f"  Raw Payload: {data}")

    except Exception as e:
        print(f"[!] Error parsing message: {e}\nRaw message: {message_str}")

# Initialize Tuya Open Pulsar listener
pulsar = TuyaOpenPulsar(
    access_id=ACCESS_ID,
    access_secret=ACCESS_SECRET,
    ws_endpoint=MQ_ENDPOINT,
    topic=TuyaCloudPulsarTopic.PROD
)

pulsar.add_message_listener(on_message)

try:
    print("[+] Connecting to Tuya Pulsar WebSocket Queue...")
    pulsar.start()
    print("[+] Connected and listening for real-time events. (Press Ctrl+C to stop)\n")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[-] Stopping Pulsar listener...")
finally:
    pulsar.stop()
    print("[-] Disconnected.")
