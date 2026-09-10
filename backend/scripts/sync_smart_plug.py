import asyncio
import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import async_session
from app.tuya_sync_service import TuyaSyncService
from app.models import SmartPlug

async def main():
    print("=" * 70)
    print("      WashQueue Smart Plug Auto-Discovery & Cloud Sync Tool      ")
    print("=" * 70)

    print("\n[*] Connecting to Tuya Cloud & querying linked devices...")
    async with async_session() as db:
        plugs = await TuyaSyncService.sync_all_plugs(db, auto_onboard_new=True)
        
        print(f"\n[+] Synchronization complete! Total plugs registered in DB: {len(plugs)}\n")
        print(f"{'Name':<22} | {'MAC Address':<18} | {'Device ID':<24} | {'Local IP':<15} | {'Online'}")
        print("-" * 95)
        for p in plugs:
            online_str = "🟢 YES" if p.is_online else "⚪ NO"
            mac_str = p.mac_address or "N/A"
            name_str = p.name or "Smart Plug"
            print(f"{name_str:<22} | {mac_str:<18} | {p.device_id:<24} | {p.ip_address:<15} | {online_str}")

        print("-" * 95)
        print("\n[*] Credentials saved to washqueue.db and synced to .env.")

if __name__ == "__main__":
    asyncio.run(main())
