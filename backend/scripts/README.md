# WashQueue Scripts & CLI Utilities

This directory contains command-line utilities for recording smart plug telemetry, tuning state detection algorithms, database maintenance, and hardware diagnostics.

---

## 🚀 Core Operational Tools (Top-Level)

| Tool | Command | Description |
| :--- | :--- | :--- |
| **`record_telemetry.py`** | `uv run python scripts/record_telemetry.py` | **Primary live telemetry recorder**. Streams live from backend WebSocket (`ws://localhost:8000/ws`) with auto-reconnect and instant CSV logging. Computes soak pauses and auto-calibrates the washer profile. |
| **`tune_from_csv.py`** | `uv run python scripts/tune_from_csv.py --csv <path>` | Post-run analyzer for recorded CSVs. Recommends running/idle wattage thresholds and debounce seconds. |
| **`export_telemetry.py`** | `uv run python scripts/export_telemetry.py --hours 24` | Exports historical telemetry readings from `washqueue.db` to CSV or JSON. |

---

## 🛠️ Subdirectories

### 1. `maintenance/` (Database & Schema Recovery)
* **`repair_db.py`**: Emergency one-time repair tool for corrupted SQLite files. Extracts intact user/machine records, recreates a fresh telemetry table, and converts the DB to WAL mode.
* **`clean_reset_db.py`**: Wipes transient bookings/telemetry and resets Washer 1 and Hostel Admin to a clean baseline.
* **`set_available.py`**: Quick one-liner helper to force Washer 1 to `available` status.

### 2. `diagnostics/` (Probes, Simulators & Verification)
* **`simulate_wash_cycle.py`**: Synthetic washing machine cycle simulator (fill, agitation, soak, spin) for offline testing without physical appliances.
* **`read_plug.py`**: Quick one-shot probe of live smart plug wattage, voltage, current, and switch state (safe dual-mode: checks backend first).
* **`read_plug_pulsar.py`**: Real-time listener for Tuya Cloud Pulsar Message Queue.
* **`sync_smart_plug.py`**: Auto-discovers and links registered Tuya cloud plugs into the local database.
* **`verify_backend.py`**: Automated end-to-end unit tests for scheduler, queue, and booking flows.
* **`verify_smart_plugs.py`**: Tests for smart plug provider registry and soak debounce state engine.
* **`verify_registration.py`**: Tests student campus registration, login, and profile deletion.

### 3. `archive/` (Superseded Tools)
* **`run_background_logger.py`**: Legacy polling logger (superseded by `record_telemetry.py`).
