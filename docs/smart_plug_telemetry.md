# Smart Plug Telemetry & Remote Control Guide

This document explains the hardware integration, high-speed telemetry polling, real-time WebSocket streaming, remote switching, 4-hour historical power analytics, and the visual threshold calibration studio in **WashQueue**.

---

## 1. Supported Hardware & Protocols

* **Hardware**: Wipro / Tuya 16A Smart Plugs (and multi-socket power strips).
* **Local LAN Protocol**: Direct AES-encrypted TCP socket communication over port `6668` using `tinytuya` (v3.3 / v3.4).
* **Cloud API Protocol**: Tuya Cloud OpenAPI (`iot-03/devices/{device_id}/commands`) with Apache Pulsar MQ integration.

---

## 2. High-Speed Telemetry & Real-Time WebSockets

```
[Smart Plug] ──(1s Local TCP Socket)──> [Backend Server] ──(WebSocket Push < 10ms)──> [Dashboards]
                                              │
                                              └──(Cloud Fallback if Isolated)──> [Tuya Cloud]
```

* **1-Second Polling Loop**: The background telemetry worker runs every **1 second** (`TELEMETRY_POLL_INTERVAL=1` in `backend/.env`). Direct local socket queries execute in **~20ms** with zero cloud quota usage and tag `source="local"`.
* **Sub-10ms WebSocket Broadcast**: Whenever a telemetry reading is recorded, the backend broadcasts a `telemetry_update` message over the open WebSocket connection (`/ws`). Connected browser dashboards update immediately without HTTP polling overhead.
* **Automatic Cloud Fallback**: If the hostel Wi-Fi router has AP/Client Isolation enabled (blocking direct LAN packets between PC and plug IP), the provider automatically falls back to Tuya Cloud API within ~1.5 seconds and tags `source="cloud"`.

---

## 3. 4-Hour Historical Power Graph (Local vs. Cloud Differentiable)

WashQueue stores and aggregates historical telemetry to graph power signatures over a rolling 4-hour window.

### Endpoint
```http
GET /api/smart-plugs/{id}/history?hours=4
Headers:
  X-Admin-PIN: 1234
```

### Response Schema
```json
{
  "plug_id": "0df62734-ad1a-4eb3-81b4-2396120800b4",
  "plug_name": "SpeedQueen Washer 02 Plug",
  "hours": 4,
  "peak_power_w": 1159.4,
  "avg_power_w": 284.2,
  "local_points_count": 232,
  "cloud_points_count": 12,
  "series": [
    {
      "timestamp": "2026-09-01T20:10:00Z",
      "power_w": 340.5,
      "voltage_v": 232.1,
      "current_ma": 1460.0,
      "source": "local"
    }
  ]
}
```

### Visualizer Presentation
* **🟢 Local LAN / WebSocket (`#10b981`)**: Smooth solid emerald gradient curve for ~1-second high-density local telemetry.
* **🔷 Tuya Cloud Fallback (`#06b6d4`, `◆`)**: Cyan diamond point markers and dashed connector lines.
* **Live Dynamic Append**: Active open chart modals dynamically append incoming real-time WebSocket telemetry packets.

---

## 4. Visual Threshold Calibration Studio (Web UI)

To allow non-technical hostel wardens and administrative staff to tune power thresholds without raw code or electrical engineering knowledge, WashQueue provides an **Interactive Graph & WebSocket Threshold Calibration Studio** directly in the Admin Panel (`/admin` -> **IoT & Smart Plugs** -> **Visual Calibration Studio**):

### 1-Click Appliance Profile Presets
* 🌀 **Top-Load (Deep Soak)**: Running Cutoff: `12.0W`, Soak/Pause Cutoff: `4.0W`, Debounce Soak: `240s` (4-min buffer prevents false completion alerts during long agitation pauses).
* 🌊 **Front-Load Inverter DD**: Running Cutoff: `8.0W`, Soak/Pause Cutoff: `3.5W`, Debounce Soak: `90s` (optimized for smooth sinusoidal tumbling direct-drive motors).
* 🔥 **Front-Load Heated (Steam)**: Running Cutoff: `10.0W`, Soak/Pause Cutoff: `4.0W`, Debounce Soak: `120s` (handles high-power internal water heater plates up to 2200W).
* ⚡ **Compact / Quick Wash**: Running Cutoff: `6.0W`, Soak/Pause Cutoff: `2.5W`, Debounce Soak: `60s` (low-draw mini washers & short 15-min cycles).
* 💨 **Commercial Drum Dryer**: Running Cutoff: `25.0W`, Soak/Pause Cutoff: `10.0W`, Debounce Soak: `60s` (high-power continuous tumbling commercial dryers).
* 🛠️ **Custom Tuning**: Fine-tune via sliders or direct on-chart drag handles.

### Interactive SVG Chart & Smart Features
* **⚡ Auto-Detect from Graph**: Scans the loaded 4-hour telemetry curve, measures baseline standby wattage, detects the longest soak pause, snaps the sliders to the optimal values, and displays the detected machine archetype badge!
* **🧪 Simulate Test Cycle**: Injects a synthetic 25-minute wash cycle into the database in 1 click, instantly populating the graph for testing without running physical appliances.
* **🟢 Active Wash Zone (Emerald Background)**: $[ \text{Running Cutoff}, \text{Max Power} ]$ $\rightarrow$ Status: `in_use`.
* **🟡 Soak / Pause Zone (Amber Background)**: $[ \text{Idle Cutoff}, \text{Running Cutoff} ]$ $\rightarrow$ Status: `soak` (starts debounce timer).
* **⚪ Standby / Empty Zone (Dark Background)**: $[ 0, \text{Idle Cutoff} ]$ $\rightarrow$ Status: `available`.
* **Draggable Guide Lines**: Admins can drag horizontal dotted threshold lines (Green `RUN` and Amber `SOAK`) up or down directly on the live power curve.
* **Hostel-Wide Propagation**: Checkbox *"Apply this calibration to all similar machines in this hostel"* batch-updates similar washers across the building.

### Calibration Endpoints
```http
PATCH /api/smart-plugs/{id}/calibration
Headers:
  X-Admin-PIN: 1234
Content-Type: application/json

{
  "power_threshold_running": 12.0,
  "power_threshold_idle": 4.0,
  "debounce_seconds": 180,
  "apply_to_similar_machines": true
}
```

```http
POST /api/smart-plugs/{id}/auto-calibrate?apply=false
Headers:
  X-Admin-PIN: 1234
```

```http
POST /api/smart-plugs/{id}/simulate-cycle?minutes=25
Headers:
  X-Admin-PIN: 1234
```

---

## 5. Washing Machine Power Profiles & Archetypes

Different washing machine mechanisms produce vastly different electrical power signatures. Understanding these archetypes is critical for accurate inference:

| Machine Archetype | Example Models | Power Curve Characteristics | Key Gotcha & Tuning Rule |
| :--- | :--- | :--- | :--- |
| **Top-Load Pulsator** | IFB, Samsung, Whirlpool Top-Loads | Sharp, high-frequency pulses (180W–320W bursts every 2s) as agitator oscillates. | **Deep soak pauses (3–10 minutes at 0–2W)**. `debounce_seconds` must be set to **180s–300s** so soak pauses aren't mistaken for cycle completion. |
| **Front-Load Inverter DD** | LG AI DirectDrive, Bosch Serie 6 | Smooth sinusoidal power ramp (100W–250W); gentle drum reversals; spin cycle ramps to 450W–650W. | Shorter rest intervals (20s–60s). `debounce_seconds` of **90s–120s** is ideal. |
| **Front-Load with Heater** | Any washer running Hot/Steam wash | Wash agitation interrupted by a **sustained 1800W–2200W plateau** for 15–25 minutes. | High peak power; standard pauses. Set `running` at **10W**, `debounce` at **120s**. |
| **Commercial / Laundromat** | Speed Queen, Maytag Commercial | Continuous motor hum, fast mechanical timer, violent drainage/spin. | Minimal pauses (<45s). Lower debounce (**60s–90s**) allows faster machine turnover. |

---

## 6. Telemetry Logging, Simulation & Tuning Suite (CLI)

For developers and power users, WashQueue provides dedicated command-line utilities in `backend/scripts/`:

### A. Live Cycle Recorder & Auto-Tuner (`record_telemetry.py`)
```powershell
python scripts/record_telemetry.py --machine "Washer 1" --interval 1.0
```
* Polls local LAN socket every 1s (<20ms latency).
* Streams real-time console dashboard (Timestamp, Watts, Volts, Current, Inferred State).
* Simultaneously writes high-res data to `telemetry_logs/telemetry_washer_1_<timestamp>.csv` and `washqueue.db`.
* On <kbd>Ctrl</kbd>+<kbd>C</kbd>, generates full cycle report (peak spin power, baseline standby, longest soak pause) and auto-updates the plug's thresholds in the database.

### B. Synthetic Cycle Simulator (`simulate_wash_cycle.py`)
```powershell
python scripts/simulate_wash_cycle.py --minutes 30
```
* Generates a complete physics-based washing machine power profile (fill, agitation, soak pause, rinse, spin, standby) into `washqueue.db` and CSV in ~5 seconds.
* Tests candidate thresholds against the synthetic dataset and flags premature soak triggers.

### C. Offline CSV Benchmark Tuner (`tune_from_csv.py`)
```powershell
python scripts/tune_from_csv.py --csv telemetry_logs/my_cycle.csv --debounce 180
```
* Replays any past recorded wash run from CSV without running physical appliances.
* Evaluates state machine transitions and verifies zero false-positive completions.

### D. Historical Telemetry Exporter (`export_telemetry.py`)
```powershell
python scripts/export_telemetry.py --device-id d7fa4d27a2883bb4feqvhl --hours 24 --format csv
```
* Dumps stored time-series readings from SQLite (`washqueue.db`) to CSV or JSON.

### E. Continuous Background Logger Daemon (`run_background_logger.py`)
```powershell
python scripts/run_background_logger.py --interval 2.0
```
* Passive headless daemon that continuously logs live smart plug telemetry into `washqueue.db`.

---

## 7. Database Persistence & Network Architecture

### SQLite WAL Mode (Write-Ahead Logging)
* `backend/washqueue.db` operates in **WAL mode** (`PRAGMA journal_mode=WAL`) with `PRAGMA synchronous=NORMAL`.
* Guarantees atomic disk commits across sudden power cuts or process stops.
* Allows high-frequency 1s telemetry writes while the web server and admin portal execute concurrent analytical reads with zero database lock contention.

### Subnet Interface Auto-Binding (Multi-Homed / VPN Robustness)
* Windows machines with active VPNs (such as **Tailscale**) frequently advertise route metrics of `0` for `192.168.1.0/24`, causing default OS sockets to route local LAN packets into the virtual VPN interface.
* [`TuyaLocalProvider`](file:///d:/lab/projects/washqueue/backend/app/smart_plug_providers/tuya_local.py) automatically identifies the local physical NIC matching the plug's subnet (`192.168.1.12`) and binds before connecting, ensuring 100% reliable <20ms local communication.

---

## 8. Remote Relay Switching

Operators can turn the smart plug ON or OFF remotely via the Admin dashboard or REST API:

```http
POST /api/smart-plugs/{id}/switch?on=true
Headers:
  X-Admin-PIN: 1234
```

1. **Local Socket First**: Sends `turn_on()` / `turn_off()` over direct LAN socket.
2. **Cloud API Fallback**: If local socket is unreachable, dispatches the command via Tuya OpenAPI.
3. **Optimistic UI Update**: Button state updates instantly upon confirmation.

---

## 9. Power State Inference & Debounce Logic

| Detected Power Draw | Inferred Machine State | Description |
| :--- | :--- | :--- |
| **`>= Running Threshold`** (e.g. 10W) | `in_use` | Motor / drum is actively spinning or heating. |
| **`< Running & >= Idle`** (e.g. 4W–10W) | *Debouncing...* | Machine is in soak or rest phase. Soak debounce timer starts. |
| **`< Idle` for >= Debounce Duration** | `idle_full` | Wash cycle completed. Machine is full and waiting to be emptied. |
| **User clears machine** | `available` | Laundry removed; machine is empty and ready for next resident. |

