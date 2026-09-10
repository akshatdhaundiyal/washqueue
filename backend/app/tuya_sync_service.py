import os
import re
import logging
import asyncio
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import tinytuya
except ImportError:
    tinytuya = None

from app.models import SmartPlug
from app.config import settings

logger = logging.getLogger("washqueue-tuya-sync")
logger.setLevel(logging.INFO)


class TuyaSyncService:
    """
    Manages automated discovery, cloud credential synchronization, and local IP resolution
    for single or multiple smart plugs without requiring manual visits to the Tuya Developer Console.
    """

    @staticmethod
    def _get_cloud_client() -> Optional[Any]:
        if not tinytuya:
            logger.error("tinytuya library is not installed.")
            return None

        api_id = os.getenv("TUYA_ACCESS_ID", "")
        api_secret = os.getenv("TUYA_ACCESS_SECRET", "")
        api_region = os.getenv("TUYA_REGION", "in").lower()

        if not api_id or not api_secret:
            logger.warning("TUYA_ACCESS_ID or TUYA_ACCESS_SECRET not configured in environment.")
            return None

        try:
            return tinytuya.Cloud(apiRegion=api_region, apiKey=api_id, apiSecret=api_secret)
        except Exception as e:
            logger.error(f"Failed to initialize Tuya Cloud client: {e}")
            return None

    @classmethod
    def fetch_all_cloud_devices(cls) -> List[Dict[str, Any]]:
        """
        Queries Tuya Cloud for all devices linked to the developer account.
        Returns a list of device dictionaries containing id, key, mac, uuid, name, category, etc.
        """
        cloud = cls._get_cloud_client()
        if not cloud:
            return []

        try:
            devices = cloud.getdevices()
            if isinstance(devices, list):
                logger.info(f"Retrieved {len(devices)} device(s) from Tuya Cloud.")
                return devices
            elif isinstance(devices, dict) and "result" in devices:
                return devices["result"]
            else:
                logger.warning(f"Unexpected response from Tuya Cloud getdevices: {devices}")
                return []
        except Exception as e:
            logger.error(f"Error querying Tuya Cloud devices: {e}")
            return []

    @classmethod
    def discover_local_ips(cls, timeout: int = 4) -> Dict[str, str]:
        """
        Listens for Tuya UDP broadcast heartbeats on the local LAN (ports 6666/6667).
        Returns a mapping of device_id -> local_ip.
        """
        if not tinytuya:
            return {}

        try:
            # tinytuya.deviceScan broadcasts UDP packets and listens for heartbeats
            logger.info(f"Scanning local network for Tuya UDP heartbeats (timeout={timeout}s)...")
            scanned = tinytuya.deviceScan(verbose=False, maxretry=2)
            dev_to_ip: Dict[str, str] = {}
            if isinstance(scanned, dict):
                for ip, data in scanned.items():
                    if isinstance(data, dict):
                        dev_id = data.get("gwId") or data.get("devId") or data.get("id")
                        if dev_id:
                            dev_to_ip[dev_id] = ip
            logger.info(f"Discovered {len(dev_to_ip)} active Tuya device(s) on local LAN.")
            return dev_to_ip
        except Exception as e:
            logger.warning(f"Local UDP scan encountered error: {e}")
            return {}

    @classmethod
    async def sync_all_plugs(
        cls,
        db: AsyncSession,
        auto_onboard_new: bool = True
    ) -> List[SmartPlug]:
        """
        Syncs all registered smart plugs against Tuya Cloud:
        1. Fetches all cloud devices linked to the Tuya account.
        2. Matches database SmartPlug records by permanent mac_address (or device_id).
        3. Updates device_id and local_key if changed (e.g. after a factory reset).
        4. If auto_onboard_new is True, registers any newly detected smart plugs (category 'cz').
        5. Attempts local IP discovery to update plug IP addresses.
        6. Updates .env with the primary plug's credentials for fallback scripts.
        """
        loop = asyncio.get_event_loop()
        cloud_devices = await loop.run_in_executor(None, cls.fetch_all_cloud_devices)
        if not cloud_devices:
            logger.warning("No devices returned from Tuya Cloud sync.")
            return []

        # Map cloud devices by normalized MAC address and device ID
        cloud_by_mac: Dict[str, Dict[str, Any]] = {}
        cloud_by_id: Dict[str, Dict[str, Any]] = {}
        for dev in cloud_devices:
            mac = dev.get("mac")
            if mac:
                norm_mac = mac.lower().replace("-", ":")
                cloud_by_mac[norm_mac] = dev
            dev_id = dev.get("id")
            if dev_id:
                cloud_by_id[dev_id] = dev

        # Fetch existing plugs from database
        result = await db.execute(select(SmartPlug))
        existing_plugs = list(result.scalars().all())
        updated_plugs: List[SmartPlug] = []

        # 1. Update existing plugs
        for plug in existing_plugs:
            matched_cloud = None
            if plug.mac_address:
                norm_mac = plug.mac_address.lower().replace("-", ":")
                matched_cloud = cloud_by_mac.get(norm_mac)
            if not matched_cloud and plug.device_id:
                matched_cloud = cloud_by_id.get(plug.device_id)

            if matched_cloud:
                new_dev_id = matched_cloud.get("id")
                new_key = matched_cloud.get("key")
                new_name = matched_cloud.get("name", plug.name)
                new_mac = matched_cloud.get("mac", plug.mac_address)

                changed = False
                if new_dev_id and plug.device_id != new_dev_id:
                    logger.info(f"Plug '{plug.name}' device_id updated: {plug.device_id} -> {new_dev_id}")
                    plug.device_id = new_dev_id
                    changed = True
                if new_key and plug.local_key != new_key:
                    logger.info(f"Plug '{plug.name}' local_key updated from Tuya Cloud.")
                    plug.local_key = new_key
                    changed = True
                if new_mac and plug.mac_address != new_mac:
                    plug.mac_address = new_mac
                    changed = True
                if new_name and not plug.name:
                    plug.name = new_name
                    changed = True

                if changed:
                    updated_plugs.append(plug)

        # 2. Auto-onboard new smart plugs if none exist or requested
        if auto_onboard_new:
            for dev in cloud_devices:
                category = dev.get("category", "")
                name = dev.get("name", "")
                # Tuya 'cz' category = Socket / Smart Plug
                is_plug = category == "cz" or "plug" in name.lower() or "socket" in name.lower()
                if not is_plug:
                    continue

                dev_mac = dev.get("mac")
                norm_mac = dev_mac.lower().replace("-", ":") if dev_mac else None
                dev_id = dev.get("id")
                dev_key = dev.get("key")

                # Check if already present in DB
                already_present = any(
                    (norm_mac and p.mac_address and p.mac_address.lower().replace("-", ":") == norm_mac) or
                    (dev_id and p.device_id == dev_id)
                    for p in existing_plugs
                )

                if not already_present and dev_id and dev_key:
                    new_plug = SmartPlug(
                        name=name.strip() or "Tuya Smart Plug",
                        mac_address=norm_mac,
                        device_id=dev_id,
                        local_key=dev_key,
                        ip_address=dev.get("ip") or os.getenv("TUYA_DEVICE_IP", "127.0.0.1"),
                        provider="tuya_local",
                        protocol_version="3.3",
                        is_online=True
                    )
                    db.add(new_plug)
                    existing_plugs.append(new_plug)
                    updated_plugs.append(new_plug)
                    logger.info(f"Auto-onboarded new smart plug '{new_plug.name}' (ID: {dev_id}, MAC: {norm_mac})")

        # 3. Local IP Discovery
        discovered_ips = await loop.run_in_executor(None, cls.discover_local_ips)
        for plug in existing_plugs:
            if plug.device_id in discovered_ips:
                new_ip = discovered_ips[plug.device_id]
                if plug.ip_address != new_ip:
                    logger.info(f"Updating IP for '{plug.name}': {plug.ip_address} -> {new_ip}")
                    plug.ip_address = new_ip
                    if plug not in updated_plugs:
                        updated_plugs.append(plug)

        await db.commit()

        # 4. Sync .env for backwards compatibility if we have at least one plug
        if existing_plugs:
            primary_plug = existing_plugs[0]
            cls.update_env_file(
                device_id=primary_plug.device_id,
                local_key=primary_plug.local_key,
                device_ip=primary_plug.ip_address,
                mac_address=primary_plug.mac_address
            )

        return existing_plugs

    @classmethod
    def update_env_file(
        cls,
        device_id: Optional[str] = None,
        local_key: Optional[str] = None,
        device_ip: Optional[str] = None,
        mac_address: Optional[str] = None,
        env_path: Optional[str] = None
    ):
        """
        Safely updates the local .env file with current smart plug credentials.
        """
        if not env_path:
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

        if not os.path.exists(env_path):
            logger.warning(f".env file not found at {env_path}")
            return

        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            updates = {}
            if device_id:
                updates["TUYA_DEVICE_ID"] = device_id
            if local_key:
                updates["TUYA_LOCAL_KEY"] = local_key
            if device_ip and not device_ip.startswith("127.0."):
                updates["TUYA_DEVICE_IP"] = device_ip
            if mac_address:
                updates["TUYA_DEVICE_MAC"] = mac_address

            for key, val in updates.items():
                pattern = rf"^{key}=.*$"
                replacement = f"{key}={val}"
                if re.search(pattern, content, flags=re.MULTILINE):
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    content += f"\n{replacement}"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Updated .env credentials for Tuya smart plug at {env_path}")
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
