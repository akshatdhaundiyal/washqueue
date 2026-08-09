import asyncio
import logging
from typing import Optional, Dict, Any

try:
    import tinytuya
except ImportError:
    tinytuya = None

try:
    from app.smart_plug_providers.base import SmartPlugProvider, TelemetryReadingData, PlugStatusData
except ImportError:
    from smart_plug_providers.base import SmartPlugProvider, TelemetryReadingData, PlugStatusData

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
        d.set_socketRetryLimit(2)
        d.set_socketTimeout(3)
        return d

    async def get_telemetry(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> TelemetryReadingData:
        """
        Polls device status over local socket using asyncio thread pool executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_telemetry_sync, device_id, local_key, ip_address, protocol_version
        )

    def _get_telemetry_sync(self, device_id: str, local_key: str, ip_address: str, protocol_version: str) -> TelemetryReadingData:
        try:
            device = self._create_device(device_id, local_key, ip_address, protocol_version)
            data = device.status()
            
            if not isinstance(data, dict) or "dps" not in data:
                logger.warning(f"Tuya device {device_id} ({ip_address}) did not return DPS payload: {data}")
                return TelemetryReadingData(raw_dps={"error": str(data)})

            dps: Dict[str, Any] = data.get("dps", {})

            # Standard Tuya DPS mappings
            # Switch: DPS 1
            switch_on = bool(dps.get("1", False)) if "1" in dps else None

            # Current (mA): DPS 18 or 4
            current_raw = dps.get("18", dps.get("4"))
            current_ma = float(current_raw) if current_raw is not None else None

            # Power (W): DPS 19 or 5 (sometimes reported as 0.1W units)
            power_raw = dps.get("19", dps.get("5"))
            power_w = None
            if power_raw is not None:
                val = float(power_raw)
                # If power value is unexpectedly large (e.g., > 5000), it's in 0.1W units
                power_w = val / 10.0 if val > 5000 else val

            # Voltage (V): DPS 20 or 6 (usually in 0.1V units, e.g. 2300 = 230V)
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
                raw_dps=dps
            )
        except Exception as e:
            logger.error(f"Error polling local Tuya plug {device_id} at {ip_address}: {e}")
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

    def _set_switch_sync(self, device_id: str, local_key: str, ip_address: str, on: bool, protocol_version: str) -> bool:
        try:
            device = self._create_device(device_id, local_key, ip_address, protocol_version)
            res = device.turn_on() if on else device.turn_off()
            return isinstance(res, dict) and "Error" not in res
        except Exception as e:
            logger.error(f"Failed to set switch state for {device_id}: {e}")
            return False
