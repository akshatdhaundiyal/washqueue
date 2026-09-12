# System Architecture - WashQueue Hybrid Edge-Cloud Appliance

This document describes the architectural layout, component roles, data flows, and security privacy models of the **WashQueue Hostel Laundry Management & Smart Plug Telemetry System**.

---

## System Components

WashQueue uses a **Hybrid Edge-Cloud Architecture**:

1. **Local Edge Layer (Primary - 100% Offline Capable)**:
   - **Nuxt 4 Dashboard & Component Hierarchy**: Modular Vue 3 architecture adhering to modern responsive standards:
     - **Desktop Navigation**: Fixed left column sidebar (`AppSidebar`) with instant route/theme switching.
     - **Mobile Optimization**: Dedicated top sticky header (`AppTopHeader`) with notification bell, settings, and avatar navigation, plus a floating bottom pill dock (`MobileBottomNav`).
     - **Modularized Hub Components**: `HomeHeroMachine` (active stopwatch), `OverviewCards` (room stats), `ApplianceCard` (6-machine grid), `ResidentProfileView` (rules & info), and `SettingsModal`.
     - **Admin Console Layout**: Aligned with the desktop left sidebar (`AdminSidebar`) and telemetry header (`AdminTopHeader`).
     - **Institutional Branding Engine**: Reusable `<AppLogo>` component (auto-theme adaptive SVG vector mark with isolated instance gradients) and composite `<AppBranding>` header component (Logo + Divider + University/Org + Hostel/Hall Name & Crest). Managed dynamically via `useHostelBranding()` with live dual-theme preview in `UsersSettingsTab.vue`.
     - **Hostel Timezone Localization Engine**: Universal conversion from UTC database timestamps (`Z`) to local hostel timezone (default: `Asia/Kolkata` - IST) with a 12-hour AM/PM vs 24-hour military clock display preference toggle via `useAppTimezone()`.
     - **Typography Engine**: **Plus Jakarta Sans** for UI/text paired with **JetBrains Mono** (`tabular-nums`) for jitter-free telemetry numbers, stopwatches, wattages, and database tables. High contrast parity guaranteed across both dark and light modes.
   - **FastAPI Engine**: Runs backend logic, PIN authentication, student identity/registration router, provider-agnostic smart plug drivers, and background workers using native **`uv`**.
   - **Dynamic Rotating QR Station (`qr_service.py`)**: Generates cryptographically signed HMAC-SHA256 registration tokens with a 60-second rotation frequency and 360-second verification window for physical laundry desk kiosks.
   - **Student Approval State Machine**: Implements an administrative gate (`status: "pending"` $\rightarrow$ `"approved"` / `"rejected"`). New registrants cannot log in or reserve machines until an admin reviews and approves the request in the Operator Console.
   - **Embedded SQLite (`washqueue.db`)**: Primary edge database (`sqlite+aiosqlite`) with hardened schema constraints, composite indexing, dynamic startup column migrations (`migrate_user_columns()`), and health tracking.
   - **Wipro / Tuya Smart Plug Driver & Concurrency Engine**: High-speed (1-second) local socket telemetry polling over TCP port 6668 via `tinytuya`. Features a persistent socket connection pool (`BoundOutletDevice`) to eliminate socket churn, per-device `asyncio.Lock` serialization, adaptive timeout sensitivity (1.5s probe $\rightarrow$ 3.5s reconnect), a 3-miss grace buffer, safe physical NIC binding, and a 15-second collision cooldown with automatic **Tuya Cloud OpenAPI Fallback** when the plug is occupied or router client isolation is active.
   - **Dual Database Portal**: Admin-facing interactive SQL console and table explorer supporting both local SQLite and remote cloud database queries.

2. **Cloud Layer (Secondary - Remote Access, Auto-Sync & Alerts)**:
   - **Supabase Cloud DB (PostgreSQL)**: Syncs state changes for remote status inspection over 4G/5G mobile data.
   - **Tuya Cloud API & Pulsar MQ**: Auto-discovers smart plug credentials, local keys, and streams device state changes.
   - **Cloud Sync Engine**: Event-driven worker on the edge device that pushes state transitions to Cloud DB. Buffers pending events in an offline replay queue (`cloud_sync_queue`) if hostel internet drops.
   - **Mobile Push Notifications**: Triggers WebPush / FCM alerts on student phones when laundry finishes or when pinged.

---

## Architecture Diagram

```mermaid
graph TD
    subgraph Hostel Local LAN (Primary - 100% Offline Capable)
        subgraph Local Devices
            HostelStudent["Student on Mobile / Desktop Wi-Fi"]
            HostelAdmin["Admin Portal (/admin)"]
            WiproPlug["Tuya / Wipro Smart Plug (IP: 192.168.1.7:6668)"]
        end

        subgraph Edge Appliance (FastAPI + SQLite + uv)
            LocalAPI["FastAPI Backend (uv run)"]
            AuthRouter["Auth Router (/api/auth) - Double-Sharing Rooms"]
            LocalWS["Native WebSockets /ws (< 10ms)"]
            EdgeDB[(Local SQLite: washqueue.db)]
            DBPortal["Database Portal Service"]
            TelemetryLoop["1s High-Speed Telemetry Worker"]
            SyncEngine["Event-Driven Cloud Sync Engine"]
            OfflineQueue[(Replay Queue: cloud_sync_queue)]
        end
    end

    subgraph Internet & Cloud Layer (Secondary / Remote)
        TuyaCloud["Tuya Cloud API & Pulsar MQ"]
        CloudDB[(Supabase PostgreSQL)]
        PushService["WebPush / FCM Notification Service"]
        RemoteStudent["Remote Student on 4G/5G Cellular Data"]
    end

    %% Local Operations
    HostelStudent -->|Register / Sign-In| AuthRouter
    HostelStudent -->|REST & Real-Time WS| LocalAPI
    HostelAdmin -->|REST & Admin PIN| LocalAPI
    LocalAPI -->|SQLAlchemy 2.0 Async| EdgeDB
    TelemetryLoop -->|1s Direct Socket Poll (source: local)| WiproPlug
    TelemetryLoop -.->|Fallback (source: cloud)| TuyaCloud
    TelemetryLoop -->|Instant Broadcast| LocalWS
    LocalWS -.->|Sub-10ms Push| HostelStudent
    LocalWS -.->|Live Gauges Push| HostelAdmin

    %% Database Portal
    HostelAdmin -->|Interactive SQL Console| DBPortal
    DBPortal -->|Query Local| EdgeDB
    DBPortal -->|Query Cloud| CloudDB

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

## Identity, Privacy & Resident Onboarding

### 1. Rotating Physical QR Verification & Kiosk Token Gating
* **Physical Presence Gating**: To eliminate spam registrations and rogue signups, resident registration is strictly gated by a dynamic QR code displayed on a tablet kiosk at the hostel laundry desk.
* **HMAC-SHA256 Token Signature**:
  $$\text{Token} = \text{hostel\_id} \,.\, \text{timestamp} \,.\, \text{nonce} \,.\, \text{HMAC}_{24}(\dots)$$
* **Rotation & Grace Window**: The kiosk rotates tokens every **60 seconds**. Once scanned by a student phone, the backend grants a **360-second grace window** to complete the form without rushing.
* **Direct Signup Blocking**: Visiting `/login` directly only permits existing residents to sign in. Attempting to access registration without scanning the desk QR displays a guidance screen ("Hostel Desk QR Required").

### 2. Administrator Approval Workflow & Authorization Gates
* **Pending Status Upon Registration**: When a resident completes the QR-verified registration form, the account is created with `status: "pending"`.
* **Login Enforcement (HTTP 403)**: Unapproved accounts cannot sign in or reserve machines. Attempted logins receive a `403 Forbidden` response explaining that the request is awaiting hostel administrator approval.
* **Admin Review Queue**: The Operator Console displays a live **`PENDING_REGISTRATION_REQUESTS`** queue card showing applicant name, room number, mobile phone, and local submission timestamp.
* **1-Click Authorization**: Clicking **`✓ Approve Resident`** transitions the student to `status: "approved"`, stamps `approved_at`, and unblocks immediate login and machine reservation. Clicking **`✕ Reject`** transitions the account to `rejected`.

### 3. Student Registration & Multi-Roommate Identity
* **Composite Identification**: Uniqueness is keyed on `(Student Name, Room Number)`.
* In **double-sharing and multi-sharing rooms**, roommates share the same Room Number (e.g. `Room B-214`) while maintaining individual accounts, passwords (SHA-256 with salt), and booking histories.
* Sign-in accepts `Room Number` + `Password`, with optional `Student Name` disambiguation for roommates.

### 4. Privacy Masking vs. Admin Audit
* **Public / Student View (`GET /api/machines`)**:
  * Anonymizes active occupants (`"Occupied by Resident"`).
  * Shows cycle duration, countdown timers, and live power status without exposing personal names.
* **Operator Console (`GET /api/admin/machines`)**:
  * Unmasks full student details (**Name**, **Room Number**, **Mobile Phone**, **Start Time**, **Queue Waitlist**) for warden audit logs.

### 5. Targeted Separate Pings
* **`🔔 Ping Occupant`**: Dispatches a direct `nudge_alert` to the resident holding the booking to collect finished clothes.
* **`🛡️ Alert Admin`**: Escalates unattended laundry or hardware issues directly to the hostel operator console with room metadata.

---

## Data Flows

### 1. Smart Plug Power Telemetry & 4-Hour Historical Analysis
1. Background polling worker reads local smart plug socket every **2 seconds** (`TELEMETRY_POLL_INTERVAL=2`) and tags `source="local"`.
2. If TCP socket is blocked by router client isolation, it falls back to Tuya Cloud OpenAPI within 1.5s and tags `source="cloud"`.
3. If power draw spikes (`>= 10W`), machine status transitions to `in_use`.
4. If power draw drops (`< 5W`), a 2-minute soak debounce timer begins.
5. If low power persists for 120s, machine status transitions to `idle_full`.
6. Edge server broadcasts `telemetry_update` in real-time over WebSocket (`/ws`) to all connected client browsers (< 10ms latency).
7. `GET /api/smart-plugs/{id}/history?hours=4` returns the complete 4-hour historical series with local vs cloud source breakdown and peak/avg metrics.

### 2. Dual Database Exploration & Administrative Querying
1. Admin opens `/admin` and authenticates with `ADMIN_PIN`.
2. Under **Tab 3: DATABASE_PORTAL**, selects target: `Local (SQLite)` or `Cloud (Supabase)`.
3. Discovered tables are queried for schema and live record counts.
4. Custom SQL queries (`SELECT`, `WITH`, `PRAGMA`, `EXPLAIN`) run with read-only safety guardrails, returning serialized JSON rows and execution timings in milliseconds.

### 3. Event-Driven Cloud Sync & Offline Replay
1. Whenever a machine status changes or an owner is pinged, the Edge server queues a cloud sync event.
2. If online, event is immediately synced to Cloud DB for remote phone access.
3. If hostel internet goes down, event is buffered in `cloud_sync_queue`.
4. When internet recovers, offline events are automatically replayed in background.

### 4. Institutional Branding & Reusable SVG Architecture
1. **`<AppLogo />` Component**:
   - Embeds the official WashQueue SVG vector geometry with circular washer drum, dual-gradient waves (`#38BDF8` to `#2DD4BF`), and telemetry indicator.
   - Automatically adapts colors: "Wash" uses `#FFFFFF` on dark backgrounds and `#191D24` on light backgrounds via `useAppTheme()`.
   - Generates unique ID namespaces (`wq-grad-[id]`, `wave-grad-[id]`) for every SVG gradient def to avoid DOM conflicts across multiple simultaneous instances.
2. **`<AppBranding />` & `useHostelBranding()` Composable**:
   - Renders a composite brand header: `[WashQueue Logo] | [Organization Logo + Name] • [Hostel Crest + Name]`.
   - Persists organization and hostel identity reactively into `localStorage` with default fallbacks.
   - Operator Admin Console (`UsersSettingsTab.vue`) provides an end-to-end management suite:
     - URL input & local image file upload (`FileReader` data URL) for both organization and hostel logos.
     - Live dual-card preview rendering the branding lockup in Light Mode and Dark Mode simultaneously.
     - Reactive propagation across all mobile headers, desktop headers, sidebars, and the login portal.

### 5. Public Resident 4-Hour Telemetry Inspection & Card Tap
1. **Card Tap Trigger**:
   - Tapping any `<ApplianceCard />` in the appliances grid or the `<HomeHeroMachine />` claimed card emits `view-history`.
   - Action buttons (`Claim & Book`, `Buzz to Empty`) utilize `@click.stop` to ensure bookings or nudges do not trigger the modal.
2. **Public Telemetry API (`GET /api/machines/{id}/power-history?hours=4`)**:
   - Accessible without administrative PIN for students.
   - Resolves machine's linked plug and returns `TelemetryHistoryResponse` (chronological points, peak power, average active wattage, local vs cloud count).
3. **Dynamic Wall-Clock X-Axis Visualization**:
   - Time ticks compute actual local hours and minutes (`HH:mm`, e.g. `08:30 (-4h)`, `09:30 (-3h)`, `10:30 (-2h)`, `11:30 (-1h)`, `12:30 (Live)`).
   - Canvas draws vertical dashed grid lines aligned with time ticks.
   - Live WebSocket stream appends real-time data points dynamically to the chart.
4. **Resilient Offline Fallback**:
   - If offline or unlinked, client synthesizes a realistic 4-hour washing profile (motor agitation, soak pauses, high-speed spin peaks, 0W completion).

### 6. Strict Role-Based UI Architecture & Authentication Flow
1. **Centralized Authentication (`/login`)**:
   - Handles both Resident Student authentication and Hostel Administrator PIN entry.
   - Replaced all early developer prototype view-switch buttons with genuine role-based routing.
2. **Resident Navigation Integrity**:
   - Removed `"Admin Console"` from student viewports.
   - Resident navigation is strictly scoped to student tasks: **Home Status**, **Appliances Hub**, **Resident Profile**, and **Settings**.
   - Standard `<LogOut />` action is integrated directly into the resident profile card at the base of the sidebar.
3. **Operator Console Isolation**:
   - Removed `"Resident Hub"` toggle from admin sidebar and headers.
   - Dedicated exclusively to the 4 operational domains (**Fleet & Bookings**, **Smart Plugs & IoT**, **Database Portal**, **Users & Settings**).
   - Session termination is guarded by the **`Lock Admin Session`** control.

