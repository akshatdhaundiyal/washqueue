# System Architecture - WashQueue Hybrid Edge-Cloud Appliance

This document describes the architectural layout, component roles, and data flows of the **WashQueue Hostel Laundry Management & Smart Plug Telemetry System**.

## System Components

WashQueue uses a **Hybrid Edge-Cloud Architecture**:

1. **Local Edge Layer (Primary - 100% Offline Capable)**:
   - **Nuxt 3 Dashboard**: SPA frontend running on local Wi-Fi. Automatically connects to native local WebSockets (`ws://<edge-ip>:8000/ws`).
   - **FastAPI Engine**: Runs backend logic, PIN authentication, provider-agnostic smart plug drivers, and background workers using native **`uv`**.
   - **Embedded SQLite (`washqueue.db`)**: Primary database running on the local edge hardware (`sqlite+aiosqlite`).
   - **Wipro Smart Plug LAN Driver**: Polls local Wipro/Tuya smart plugs over TCP port 6668 via `tinytuya` with 2-minute soak debounce logic.

2. **Cloud Layer (Secondary - Remote Access & Alerts)**:
   - **Supabase Cloud DB**: Syncs state changes for remote status inspection over 4G/5G mobile data.
   - **Cloud Sync Engine**: Event-driven worker on the edge device that pushes state transitions to Cloud DB. Buffers pending events in an offline replay queue (`cloud_sync_queue`) if hostel internet drops.
   - **Mobile Push Notifications**: Triggers WebPush / FCM alerts on student phones when laundry finishes or when pinged.

---

## Architecture Diagram

```mermaid
graph TD
    subgraph Hostel Local LAN (Primary - 100% Offline Capable)
        subgraph Local Devices
            HostelStudent["Student on Hostel Wi-Fi"]
            HostelAdmin["Admin on Hostel Wi-Fi"]
            WiproPlug["Wipro Smart Plug (Local IP / Port 6668)"]
        end

        subgraph Edge Appliance (FastAPI + SQLite + uv)
            LocalAPI["FastAPI Backend (uv run)"]
            LocalWS["Native WebSockets /ws"]
            EdgeDB[(Local SQLite: washqueue.db)]
            SyncEngine["Event-Driven Cloud Sync Engine"]
            OfflineQueue[(Replay Queue: cloud_sync_queue)]
        end
    end

    subgraph Internet & Cloud Layer (Secondary / Remote)
        CloudDB[(Supabase Cloud DB)]
        PushService["WebPush / FCM Notification Service"]
        RemoteStudent["Remote Student on 4G/5G Cellular Data"]
    end

    %% Local Operations
    HostelStudent -->|Local REST & WS| LocalAPI
    HostelAdmin -->|Local REST & PIN| LocalAPI
    LocalAPI -->|Async DB| EdgeDB
    LocalAPI -->|Poll Local Socket| WiproPlug
    LocalAPI -.->|Local Broadcast| LocalWS

    %% Cloud Sync Operations
    LocalAPI -->|State Transition Event| SyncEngine
    SyncEngine -->|Online: Instant Event Sync| CloudDB
    SyncEngine -->|Offline: Buffer Event| OfflineQueue
    OfflineQueue -.->|Re-connection: Replay Batch| CloudDB

    CloudDB -->|Trigger Mobile Alert| PushService
    PushService -.->|Mobile Push Notification| RemoteStudent
    RemoteStudent -->|Check Status Over Cellular| CloudDB
```

---

## Data Flows

### 1. Smart Plug Power Telemetry & State Inference
1. Background polling worker reads local smart plug socket every 10 seconds.
2. If power draw spikes (`>= 10W`), machine status transitions to `in_use`.
3. If power draw drops (`< 5W`), a 2-minute soak debounce timer begins.
4. If low power persists for 120s, machine status transitions to `idle_full`.
5. Edge server broadcasts update over local WebSocket (`/ws`) and queues event for Cloud DB sync.

### 2. Event-Driven Cloud Sync & Offline Replay
1. Whenever a machine status changes or an owner is pinged, the Edge server queues a cloud sync event.
2. If online, event is immediately synced to Cloud DB for remote phone access.
3. If hostel internet goes down, event is buffered in `cloud_sync_queue`.
4. When internet recovers, offline events are automatically replayed in background.
