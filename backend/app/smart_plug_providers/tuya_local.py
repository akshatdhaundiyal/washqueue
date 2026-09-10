import os
import asyncio
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

try:
    import tinytuya
except ImportError:
    tinytuya = None

try:
    from app.smart_plug_providers.base import SmartPlugProvider, TelemetryReadingData, PlugStatusData
except ImportError:
    from .base import SmartPlugProvider, TelemetryReadingData, PlugStatusData

logger = logging.getLogger("washqueue-tuya-local")

class TuyaLocalProvider(SmartPlugProvider):
    """
    Local LAN smart plug provider for Wipro / Tuya-based plugs.
    Communicates directly with the device over TCP port 6668/6667.
    Zero cloud dependencies.
    """

    def _create_device(self, device_id: str, local_key: str, ip_address: str, protocol_version: str):
        if not tinytuya:
            raise RuntimeError("tinytuya library is not installed.")
            
        version_float = float(protocol_version) if protocol_version else 3.3
        d = tinytuya.OutletDevice(
            dev_id=device_id,
            address=ip_address,
            local_key=local_key,
            version=version_float
        )
        d.set_socketRetryLimit(1)
        d.set_socketTimeout(1.5)

        # Ensure local interface binding for multi-homed or VPN/Tailscale-routed systems
        import socket
        try:
            prefix = '.'.join(ip_address.split('.')[:3]) + '.'
            local_bind_ip = None
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                cand = info[4][0]
                if cand.startswith(prefix):
                    local_bind_ip = cand
                    break
            if local_bind_ip:
                orig_get_socket = d._get_socket
                def bound_get_socket(renew):
                    real_socket = socket.socket
                    def wrapped_socket(*args, **kwargs):
                        s = real_socket(*args, **kwargs)
                        try:
                            s.bind((local_bind_ip, 0))
                        except Exception:
                            pass
                        return s
                    socket.socket = wrapped_socket
                    try:
                        return orig_get_socket(renew)
                    finally:
                        socket.socket = real_socket
                d._get_socket = bound_get_socket
        except Exception:
            pass

        return d

    async def get_telemetry(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> TelemetryReadingData:
        """
        Polls device status over local socket using asyncio thread pool executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_telemetry_sync, device_id, local_key, ip_address, protocol_version
        )

    def _get_telemetry_cloud_fallback(self, device_id: str) -> Optional[TelemetryReadingData]:
        """
        Fallback telemetry fetcher using Tuya Cloud API if local LAN communication is blocked or during DHCP changes.
        """
        try:
            import os
            api_id = os.getenv("TUYA_ACCESS_ID")
            api_secret = os.getenv("TUYA_ACCESS_SECRET")
            api_region = os.getenv("TUYA_REGION", "in").lower()
            if not api_id or not api_secret or not tinytuya:
                return None

            cloud = tinytuya.Cloud(apiRegion=api_region, apiKey=api_id, apiSecret=api_secret)
            res = cloud.getstatus(device_id)
            if not isinstance(res, dict) or not res.get("success") or "result" not in res:
                return None

            result_list = res.get("result", [])
            dps: Dict[str, Any] = {item.get("code"): item.get("value") for item in result_list if "code" in item}

            switch_on = bool(dps.get("switch_1", False)) if "switch_1" in dps else None
            current_raw = dps.get("cur_current")
            current_ma = float(current_raw) if current_raw is not None else None

            power_raw = dps.get("cur_power")
            power_w = float(power_raw) / 10.0 if power_raw is not None else None

            voltage_raw = dps.get("cur_voltage")
            voltage_v = float(voltage_raw) / 10.0 if voltage_raw is not None else None

            energy_raw = dps.get("add_ele")
            energy_kwh = float(energy_raw) / 1000.0 if energy_raw is not None else None

            return TelemetryReadingData(
                voltage_v=voltage_v,
                current_ma=current_ma,
                power_w=power_w,
                energy_kwh=energy_kwh,
                switch_on=switch_on,
                source="cloud",
                raw_dps=dps
            )
        except Exception as e:
            logger.debug(f"Cloud fallback query failed for {device_id}: {e}")
            return None

    def _get_telemetry_sync(self, device_id: str, local_key: str, ip_address: str, protocol_version: str) -> TelemetryReadingData:
        try:
            # 1. Attempt local LAN connection first (0 cloud quota, sub-20ms latency)
            device = self._create_device(device_id, local_key, ip_address, protocol_version)
            data = device.status()
            
            # If local socket succeeded and returned DPS
            if isinstance(data, dict) and "dps" in data:
                dps: Dict[str, Any] = data.get("dps", {})

                # Switch: DPS 1
                switch_on = bool(dps.get("1", False)) if "1" in dps else None

                # Current (mA): DPS 18 or 4
                current_raw = dps.get("18", dps.get("4"))
                current_ma = float(current_raw) if current_raw is not None else None

                # Power (W): DPS 19 or 5 (Tuya 0.1W unit)
                power_raw = dps.get("19", dps.get("5"))
                power_w = None
                if power_raw is not None:
                    power_w = float(power_raw) / 10.0

                # Voltage (V): DPS 20 or 6
                voltage_raw = dps.get("20", dps.get("6"))
                voltage_v = None
                if voltage_raw is not None:
                    val = float(voltage_raw)
                    voltage_v = val / 10.0 if val > 1000 else val

                # Energy (kWh): DPS 17
                energy_raw = dps.get("17")
                energy_kwh = float(energy_raw) / 100.0 if energy_raw is not None else None

                return TelemetryReadingData(
                    voltage_v=voltage_v,
                    current_ma=current_ma,
                    power_w=power_w,
                    energy_kwh=energy_kwh,
                    switch_on=switch_on,
                    source="local",
                    raw_dps=dps
                )

            # Local LAN returned error or no DPS (e.g. client isolation, IP change, key mismatch)
            logger.warning(f"Tuya local device {device_id} ({ip_address}) unreachable or failed ({data}). Falling back to Cloud...")
            cloud_reading = self._get_telemetry_cloud_fallback(device_id)
            if cloud_reading:
                return cloud_reading

            return TelemetryReadingData(raw_dps={"error": str(data)})

        except Exception as e:
            logger.warning(f"Local query error for {device_id} ({ip_address}): {e}. Trying cloud fallback...")
            cloud_reading = self._get_telemetry_cloud_fallback(device_id)
            if cloud_reading:
                return cloud_reading
            return TelemetryReadingData(raw_dps={"error": str(e)})

    async def get_status(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> PlugStatusData:
        reading = await self.get_telemetry(device_id, local_key, ip_address, protocol_version)
        is_online = reading.raw_dps is not None and "error" not in reading.raw_dps
        switch_on = reading.switch_on if reading.switch_on is not None else False
        return PlugStatusData(is_online=is_online, switch_on=switch_on)

    async def set_switch(self, device_id: str, local_key: str, ip_address: str, on: bool, protocol_version: str = "3.3") -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._set_switch_sync, device_id, local_key, ip_address, on, protocol_version
        )

    def _set_switch_cloud_fallback(self, device_id: str, on: bool) -> bool:
        try:
            api_region = os.getenv("TUYA_REGION") or os.getenv("TUYA_API_REGION", "in")
            api_key = os.getenv("TUYA_ACCESS_ID") or os.getenv("TUYA_API_KEY")
            api_secret = os.getenv("TUYA_ACCESS_SECRET") or os.getenv("TUYA_API_SECRET")
            if not api_key or not api_secret or not tinytuya:
                return False
            cloud = tinytuya.Cloud(apiRegion=api_region.lower(), apiKey=api_key, apiSecret=api_secret)
            res = cloud.sendcommand(device_id, {"commands": [{"code": "switch_1", "value": on}]})
            return isinstance(res, dict) and bool(res.get("success", False))
        except Exception as e:
            logger.error(f"Cloud fallback switch error for {device_id}: {e}")
            return False

    def _set_switch_sync(self, device_id: str, local_key: str, ip_address: str, on: bool, protocol_version: str) -> bool:
        # 1. Try local LAN socket connection first
        try:
            device = self._create_device(device_id, local_key, ip_address, protocol_version)
            res = device.turn_on() if on else device.turn_off()
            if isinstance(res, dict) and "Error" not in res and res.get("Err") != "905":
                return True
        except Exception as e:
            logger.warning(f"Local switch error for {device_id} ({ip_address}): {e}")

        # 2. Fallback to Tuya Cloud API
        logger.info(f"Using Tuya Cloud fallback to switch device {device_id} to {on}...")
        return self._set_switch_cloud_fallback(device_id, on)
