from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class TelemetryReadingData:
    voltage_v: Optional[float] = None
    current_ma: Optional[float] = None
    power_w: Optional[float] = None
    energy_kwh: Optional[float] = None
    switch_on: Optional[bool] = None
    source: str = "local"  # "local" | "cloud"
    raw_dps: Optional[Dict[str, Any]] = None

@dataclass
class PlugStatusData:
    is_online: bool
    switch_on: bool

class SmartPlugProvider(ABC):
    """
    Provider-agnostic interface for communicating with smart plugs.
    Implementations translate hardware-specific protocols (Tuya, Tasmota, Shelly)
    into standard telemetry models.
    """

    @abstractmethod
    async def get_telemetry(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> TelemetryReadingData:
        """Poll current telemetry metrics (voltage, current, power, energy)."""
        pass

    @abstractmethod
    async def get_status(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> PlugStatusData:
        """Get online and switch state."""
        pass

    @abstractmethod
    async def set_switch(self, device_id: str, local_key: str, ip_address: str, on: bool, protocol_version: str = "3.3") -> bool:
        """Turn plug on or off."""
        pass
