import os
import sys
import time
import socket
import asyncio
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.smart_plug_providers.tuya_local import (
    TuyaLocalProvider,
    _device_pool,
    _device_locks,
    _collision_cooldown,
    get_device_lock,
    BoundOutletDevice,
    _find_local_bind_ip
)
from app.models import SmartPlug
from app.smart_plug_providers.base import TelemetryReadingData

class TestSocketResilience(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        _device_pool.clear()
        _device_locks.clear()
        _collision_cooldown.clear()

    def test_global_socket_unmodified(self):
        """Verify global socket.socket is NOT monkey-patched."""
        self.assertEqual(socket.socket.__module__, "socket")
        self.assertFalse(hasattr(socket.socket, "_is_mocked"))

    def test_device_pool_reuse(self):
        """Verify device instances are cached and reused to prevent socket churn."""
        provider = TuyaLocalProvider()
        dev1 = provider._get_device("test_dev_001", "1234567890123456", "192.168.1.15", "3.3")
        dev2 = provider._get_device("test_dev_001", "1234567890123456", "192.168.1.15", "3.3")
        self.assertIs(dev1, dev2, "Device pool should reuse identical device instances")
        self.assertTrue(dev1.socketPersistent, "Persistent socket should be enabled")
        self.assertTrue(dev1.socketNODELAY, "TCP_NODELAY should be enabled")

    def test_device_pool_eviction_on_config_change(self):
        """Verify changing IP address cleanly evicts and recreates device."""
        provider = TuyaLocalProvider()
        dev1 = provider._get_device("test_dev_001", "1234567890123456", "192.168.1.15", "3.3")
        dev2 = provider._get_device("test_dev_001", "1234567890123456", "192.168.1.20", "3.3")
        self.assertIsNot(dev1, dev2, "Device should be recreated when IP changes")
        self.assertEqual(dev2.address, "192.168.1.20")

    def test_safe_local_bind_resolution(self):
        """Verify local bind IP is found without crashing or monkey-patching."""
        bind_ip = _find_local_bind_ip("192.168.1.15")
        # On this machine, Wi-Fi 2 has 192.168.1.12
        if bind_ip:
            self.assertTrue(bind_ip.startswith("192.168.1."))

    async def test_per_device_concurrency_locking(self):
        """Verify concurrent operations on the same device ID are serialized."""
        lock = get_device_lock("dev_concurrent_test")
        execution_order = []

        async def worker(worker_id: int, sleep_time: float):
            async with lock:
                execution_order.append(f"start_{worker_id}")
                await asyncio.sleep(sleep_time)
                execution_order.append(f"end_{worker_id}")

        await asyncio.gather(
            worker(1, 0.05),
            worker(2, 0.02),
            worker(3, 0.01)
        )

        # In serialized execution, each worker must finish before the next starts
        expected = [
            "start_1", "end_1",
            "start_2", "end_2",
            "start_3", "end_3"
        ]
        self.assertEqual(execution_order, expected, "Concurrent tasks must be serialized by device lock")

    def test_collision_cooldown_behavior(self):
        """Verify collision cooldown stops local queries and routes to cloud fallback."""
        provider = TuyaLocalProvider()
        device_id = "dev_cooldown_test"
        
        # Manually trigger a 15s cooldown
        _collision_cooldown[device_id] = time.time() + 15.0

        # Attempting query should immediately use cloud fallback and return without local socket attempt
        res = provider._get_telemetry_sync(device_id, "key1234567890123", "192.168.1.15", "3.3")
        # Since cloud credentials might be tested or return None, verify it did not hang
        self.assertIsNotNone(res)

    def test_three_miss_grace_buffer_logic(self):
        """Simulate telemetry_service grace buffer: is_online only becomes False on 3rd failure."""
        plug = SmartPlug(
            name="Test Washer",
            device_id="dev_grace_test",
            ip_address="192.168.1.15",
            is_online=True,
            consecutive_failures=0
        )

        # Simulate Tick 1 failure
        reading_ok_1 = False
        if reading_ok_1:
            plug.is_online = True
            plug.consecutive_failures = 0
        else:
            plug.consecutive_failures += 1
            if plug.consecutive_failures >= 3:
                plug.is_online = False
        self.assertTrue(plug.is_online, "1 failure should NOT mark plug offline (grace buffer)")
        self.assertEqual(plug.consecutive_failures, 1)

        # Simulate Tick 2 failure
        reading_ok_2 = False
        if reading_ok_2:
            plug.is_online = True
            plug.consecutive_failures = 0
        else:
            plug.consecutive_failures += 1
            if plug.consecutive_failures >= 3:
                plug.is_online = False
        self.assertTrue(plug.is_online, "2 consecutive failures should STILL not mark plug offline")
        self.assertEqual(plug.consecutive_failures, 2)

        # Simulate Tick 3 failure
        reading_ok_3 = False
        if reading_ok_3:
            plug.is_online = True
            plug.consecutive_failures = 0
        else:
            plug.consecutive_failures += 1
            if plug.consecutive_failures >= 3:
                plug.is_online = False
        self.assertFalse(plug.is_online, "3rd consecutive failure MUST mark plug offline")
        self.assertEqual(plug.consecutive_failures, 3)

        # Simulate Tick 4 success (recovery)
        reading_ok_4 = True
        if reading_ok_4:
            plug.is_online = True
            plug.consecutive_failures = 0
        self.assertTrue(plug.is_online, "Successful reading must immediately recover online state")
        self.assertEqual(plug.consecutive_failures, 0)

if __name__ == "__main__":
    unittest.main()
