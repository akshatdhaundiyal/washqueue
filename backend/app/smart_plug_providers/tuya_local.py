import os
import time
import socket
import asyncio
import datetime
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

# Module-level singletons to eliminate socket churn and cross-thread collisions
_device_pool: Dict[str, Any] = {}          # device_id -> BoundOutletDevice
_device_locks: Dict[str, asyncio.Lock] = {} # device_id -> asyncio.Lock
_collision_cooldown: Dict[str, float] = {}  # device_id -> timestamp (cooldown expiration)

def get_device_lock(device_id: str) -> asyncio.Lock:
    """Returns or creates an asyncio.Lock for the specific physical device ID."""
    if device_id not in _device_locks:
        _device_locks[device_id] = asyncio.Lock()
    return _device_locks[device_id]

def _find_local_bind_ip(target_ip: str) -> Optional[str]:
    """Finds the local interface IP that matches the subnet prefix of target_ip."""
    try:
        prefix = '.'.join(target_ip.split('.')[:3]) + '.'
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            cand = info[4][0]
            if cand.startswith(prefix):
                return cand
    except Exception:
        pass
    return None

if tinytuya:
    class BoundOutletDevice(tinytuya.OutletDevice):
        """
        Subclass of tinytuya.OutletDevice that safely binds the TCP socket
        to a specific physical NIC IP before connecting, eliminating VPN/Tailscale
        route collisions without mutating Python's global socket.socket class.
        """
        def __init__(self, *args, bind_ip: Optional[str] = None, **kwargs):
            self.bind_ip = bind_ip
            super().__init__(*args, **kwargs)

        def _get_socket(self, renew):
            if renew and self.socket is not None:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None

            if self.socket is None:
                retries = 0
                err = tinytuya.ERR_OFFLINE
                while retries < self.socketRetryLimit:
                    if not self.address:
                        return tinytuya.ERR_OFFLINE
                    if (self.version > 3.1) and ((not self.local_key) or (len(self.local_key) != 16)):
                        return tinytuya.ERR_KEY_OR_VER

                    family = socket.AF_INET6 if ':' in self.address else socket.AF_INET
                    s = socket.socket(family, socket.SOCK_STREAM)
                    if self.bind_ip:
                        try:
                            s.bind((self.bind_ip, 0))
                        except Exception as e:
                            logger.debug(f"Failed to bind socket to local IP {self.bind_ip}: {e}")
                    if self.socketNODELAY:
                        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    s.settimeout(self.connection_timeout)
                    try:
                        retries += 1
                        s.connect((self.address, self.port))
                        self.socket = s
                        if self.version >= 3.4:
                            if self._negotiate_session_key():
                                return True
                            else:
                                if self.socket:
                                    self.socket.close()
                                    self.socket = None
                                return tinytuya.ERR_KEY_OR_VER
                        else:
                            return True
                    except socket.timeout:
                        err = tinytuya.ERR_OFFLINE
                    except Exception:
                        err = tinytuya.ERR_CONNECT

                    if s:
                        try:
                            s.close()
                        except Exception:
                            pass
                    self.socket = None
                    if retries < self.socketRetryLimit:
                        time.sleep(self.socketRetryDelay)
                return err
            return True
else:
    BoundOutletDevice = None

class TuyaLocalProvider(SmartPlugProvider):
    """
    Local LAN smart plug provider for Wipro / Tuya-based plugs.
    Communicates directly with the device over TCP port 6668/6667.
    Reuses persistent TCP connections to eliminate socket churn.
    Zero cloud dependencies in local mode with automatic Cloud API fallback.
    """

    def _get_device(self, device_id: str, local_key: str, ip_address: str, protocol_version: str):
        if not tinytuya or not BoundOutletDevice:
            raise RuntimeError("tinytuya library is not installed.")

        version_float = float(protocol_version) if protocol_version else 3.3
        bind_ip = _find_local_bind_ip(ip_address)
        key_bytes = local_key.encode('utf-8') if isinstance(local_key, str) else local_key

        # Reuse cached device if parameters match
        device = _device_pool.get(device_id)
        if device is not None:
            key_matches = device.local_key in (local_key, key_bytes)
            if (device.address == ip_address and 
                key_matches and 
                device.version == version_float and
                getattr(device, "bind_ip", None) == bind_ip):
                return device
            else:
                # Configuration changed, tear down old socket
                try:
                    device._check_socket_close(True)
                except Exception:
                    pass
                _device_pool.pop(device_id, None)

        # Create new device with persistent socket settings
        device = BoundOutletDevice(
            dev_id=device_id,
            address=ip_address,
            local_key=local_key,
            version=version_float,
            bind_ip=bind_ip
        )
        device.set_socketPersistent(True)
        device.set_socketNODELAY(True)
        device.set_socketRetryLimit(2)
        device.set_socketRetryDelay(0.2)
        device.set_socketTimeout(3.5)
        _device_pool[device_id] = device
        return device

    async def get_telemetry(self, device_id: str, local_key: str, ip_address: str, protocol_version: str = "3.3") -> TelemetryReadingData:
        """
        Polls device status over local socket using asyncio lock per device
        to serialize access and prevent socket collisions.
        """
        lock = get_device_lock(device_id)
        async with lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._get_telemetry_sync, device_id, local_key, ip_address, protocol_version
            )

    def _get_telemetry_cloud_fallback(self, device_id: str) -> Optional[TelemetryReadingData]:
        """
        Fallback telemetry fetcher using Tuya Cloud API if local LAN communication is blocked or during DHCP changes.
        """
        try:
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

            cloud_t = res.get("t")
            adjusted_dt = None
            if cloud_t:
                try:
                    offset_sec = float(os.getenv("TUYA_CLOUD_TIME_OFFSET_SECONDS", "0.0") or 0.0)
                    adjusted_dt = datetime.datetime.fromtimestamp((float(cloud_t) / 1000.0) + offset_sec, tz=datetime.timezone.utc)
                except Exception:
                    pass

            return TelemetryReadingData(
                voltage_v=voltage_v,
                current_ma=current_ma,
                power_w=power_w,
                energy_kwh=energy_kwh,
                switch_on=switch_on,
                source="cloud",
                timestamp=adjusted_dt,
                raw_dps=dps
            )
        except Exception as e:
            logger.debug(f"Cloud fallback query failed for {device_id}: {e}")
            return None

    def _get_telemetry_sync(self, device_id: str, local_key: str, ip_address: str, protocol_version: str) -> TelemetryReadingData:
        now_ts = time.time()

        # 1. Check if device is in collision cooldown (e.g. mobile app holding port or previous failure)
        cooldown_until = _collision_cooldown.get(device_id, 0)
        if now_ts < cooldown_until:
            logger.debug(f"Device {device_id} in local collision cooldown ({cooldown_until - now_ts:.1f}s left). Using Cloud fallback...")
            cloud_reading = self._get_telemetry_cloud_fallback(device_id)
            if cloud_reading:
                return cloud_reading
            return TelemetryReadingData(raw_dps={"error": "In collision cooldown, cloud fallback unavailable"})

        device = None
        try:
            # 2. Retrieve or create persistent device
            device = self._get_device(device_id, local_key, ip_address, protocol_version)

            # Adaptive timeout: 1.5s fast probe if socket already open; 3.5s if opening/reconnecting
            if device.socket is not None:
                device.socket.settimeout(1.5)
            else:
                device.set_socketTimeout(3.5)

            data = device.status()

            # If local socket succeeded and returned DPS
            if isinstance(data, dict) and "dps" in data:
                dps: Dict[str, Any] = data.get("dps", {})
                _collision_cooldown.pop(device_id, None)

                switch_on = bool(dps.get("1", False)) if "1" in dps else None
                current_raw = dps.get("18", dps.get("4"))
                current_ma = float(current_raw) if current_raw is not None else None

                power_raw = dps.get("19", dps.get("5"))
                power_w = float(power_raw) / 10.0 if power_raw is not None else None

                voltage_raw = dps.get("20", dps.get("6"))
                voltage_v = None
                if voltage_raw is not None:
                    val = float(voltage_raw)
                    voltage_v = val / 10.0 if val > 1000 else val

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

            # Local LAN returned error or no DPS (conflict / mobile app active / connection refused)
            logger.warning(f"Tuya local device {device_id} ({ip_address}) returned error ({data}). Resetting socket & initiating 15s Cloud cooldown...")
            if device:
                try:
                    device._check_socket_close(True)
                except Exception:
                    pass
            _device_pool.pop(device_id, None)
            _collision_cooldown[device_id] = now_ts + 15.0

            cloud_reading = self._get_telemetry_cloud_fallback(device_id)
            if cloud_reading:
                return cloud_reading

            return TelemetryReadingData(raw_dps={"error": str(data)})

        except Exception as e:
            logger.warning(f"Local query error for {device_id} ({ip_address}): {e}. Initiating 15s Cloud cooldown...")
            if device:
                try:
                    device._check_socket_close(True)
                except Exception:
                    pass
            _device_pool.pop(device_id, None)
            _collision_cooldown[device_id] = now_ts + 15.0

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
        lock = get_device_lock(device_id)
        async with lock:
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
        now_ts = time.time()
        cooldown_until = _collision_cooldown.get(device_id, 0)
        if now_ts < cooldown_until:
            logger.info(f"Device {device_id} in local collision cooldown. Using Cloud fallback for switch to {on}...")
            return self._set_switch_cloud_fallback(device_id, on)

        device = None
        try:
            device = self._get_device(device_id, local_key, ip_address, protocol_version)
            device.set_socketTimeout(3.5)
            res = device.turn_on() if on else device.turn_off()
            if isinstance(res, dict) and "Error" not in res and res.get("Err") != "905":
                _collision_cooldown.pop(device_id, None)
                return True
        except Exception as e:
            logger.warning(f"Local switch error for {device_id} ({ip_address}): {e}")
            if device:
                try:
                    device._check_socket_close(True)
                except Exception:
                    pass
            _device_pool.pop(device_id, None)
            _collision_cooldown[device_id] = now_ts + 15.0

        # Fallback to Tuya Cloud API
        logger.info(f"Using Tuya Cloud fallback to switch device {device_id} to {on}...")
        return self._set_switch_cloud_fallback(device_id, on)

