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

## 4. Visual Threshold Calibration Studio (For Non-Tech Admins)

To allow non-technical hostel wardens and administrative staff to tune power thresholds without understanding raw code or electrical engineering formulas, WashQueue provides an **Interactive Graph & WebSocket Threshold Calibration Studio**:

### 1-Click Appliance Presets
* 🌊 **Front-Load Eco Washer**: Running Cutoff: `8.0W`, Soak/Pause Cutoff: `3.5W`, Debounce Soak: `90s`.
* 🌀 **Top-Load Heavy Washer**: Running Cutoff: `15.0W`, Soak/Pause Cutoff: `6.0W`, Debounce Soak: `150s`.
* 💨 **Commercial Drum Dryer**: Running Cutoff: `25.0W`, Soak/Pause Cutoff: `10.0W`, Debounce Soak: `60s`.
* ⚡ **Custom Calibration**: Fine-tune via sliders or direct on-chart drag handles.

### Interactive SVG Chart & Colored Zones
* **🟢 Active Wash Zone (Emerald Background)**: $[ \text{Running Cutoff}, \text{Max Power} ]$ $\rightarrow$ Status: `in_use`.
* **🟡 Soak / Pause Zone (Amber Background)**: $[ \text{Idle Cutoff}, \text{Running Cutoff} ]$ $\rightarrow$ Status: `soak` (starts debounce timer).
* **⚪ Standby / Empty Zone (Dark Background)**: $[ 0, \text{Idle Cutoff} ]$ $\rightarrow$ Status: `available`.
* **Draggable Guide Lines**: Non-tech admins can drag horizontal threshold lines up or down directly on the live power curve.

### Calibration Update Endpoint
```http
PATCH /api/smart-plugs/{id}/calibration
Headers:
  X-Admin-PIN: 1234
Content-Type: application/json

{
  "power_threshold_running": 12.5,
  "power_threshold_idle": 4.5,
  "debounce_seconds": 120,
  "apply_to_similar_machines": true
}
```

---

## 5. Remote Relay Switching

Operators can turn the smart plug ON or OFF remotely via the Admin dashboard or REST API:

### Endpoint
```http
POST /api/smart-plugs/{id}/switch?on=true
Headers:
  X-Admin-PIN: 1234
```

### Switching Mechanics
1. **Local Socket First**: Attempts to send `turn_on()` / `turn_off()` over the local TCP socket.
2. **Cloud API Fallback**: If local socket is unreachable, immediately dispatches the command via Tuya Cloud API payload:
   ```json
   {
     "commands": [
       { "code": "switch_1", "value": true }
     ]
   }
   ```
3. **Optimistic UI Update**: The admin button (`⚡ SWITCH ON` <-> `⚪ SWITCH OFF`) updates instantly in local state upon confirmation.

---

## 6. Power State Inference & Debounce Logic

| Detected Power Draw | Inferred Machine State | Description |
| :--- | :--- | :--- |
| **`>= Running Threshold`** (e.g. 10W) | `in_use` | Motor / drum is actively spinning or heating. |
| **`< Running & >= Idle`** (e.g. 5W-10W) | *Debouncing...* | Machine is soaking or in a pause phase. Starts soak debounce timer. |
| **`< Idle` for >= Debounce Duration** | `idle_full` | Wash cycle completed. Machine is full and waiting to be emptied. |
| **User clears machine** | `available` | Laundry removed; machine is empty and ready for the next student. |
