# Project Milestones - WashQueue Hostel Laundry Management System

This document outlines the milestones and key checkpoints for developing, validating, and deploying the **WashQueue** laundry management system.

## Milestone 1: Database Setup & Schemas
- [x] Create `supabase_schema.sql` & `supabase_schema_v2.sql` defining `machines`, `bookings`, `queue`, `smart_plugs`, `telemetry_readings`, and `users` tables.
- [x] Establish Foreign Key relations and constraints.
- [x] Support cross-database compatibility (Embedded SQLite + PostgreSQL/Supabase).
- [x] Seed database with initial washing & drying machines.

## Milestone 2: FastAPI Backend Core & Repositories
- [x] Implement database connectivity utilizing async engine (`asyncpg` / `aiosqlite`) and SQLAlchemy 2.0 models.
- [x] Build async repositories encapsulating DB operations (`MachineRepository`, `BookingRepository`, `QueueRepository`, `SmartPlugRepository`, `UserRepository`, `TelemetryRepository`).
- [x] Set up schemas utilizing Pydantic v2 for request inputs and responses.
- [x] Create `/api/machines/{id}/claim`, `/api/machines/{id}/clear`, and `/api/machines/{id}/ping` endpoints.
- [x] Create queue endpoints: `/api/machines/{id}/queue/join` and `/api/machines/{id}/queue/leave`.

## Milestone 3: Background Scheduler & Overdue Checks
- [x] Implement local background checker logic (`scheduler.py`) verifying overdue bookings.
- [x] Map endpoint `/api/scheduler/tick` that transitions overdue machines from `in_use` to `idle_full`.
- [x] Add logger notifications signaling when a machine's cycle is complete and status shifts.

## Milestone 4: Nuxt Frontend Init & Tailwind Integration
- [x] Initialize Nuxt project structure in `frontend/`.
- [x] Add Tailwind CSS module and configure styles/typography.
- [x] Build main layout framework and responsive design grids.

## Milestone 5: Local Edge WebSockets & Real-Time Sync
- [x] Implement native FastAPI WebSocket ConnectionManager (`/ws`).
- [x] Connect Nuxt frontend using custom `useLocalWebSocket` composable for zero-latency local LAN updates.
- [x] Implement localized client-side countdown timer calculating difference between `estimated_end_at` and current time.
- [x] Style color transitions: Green (`available`), Red (`in_use`), Orange (`idle_full`).

## Milestone 6: Provider-Agnostic Smart Plug Integration
- [x] Create abstract `SmartPlugProvider` interface and provider registry.
- [x] Implement `TuyaLocalProvider` for Wipro smart plugs using `tinytuya` over local TCP socket port 6668.
- [x] Build background telemetry polling worker running every 10 seconds.
- [x] Implement power state inference logic with **2-minute soak debounce window** (`< 5W`).

## Milestone 7: PIN-Protected Admin Dashboard
- [x] Implement `X-Admin-PIN` security dependency (`auth.py`) for Admin routes (default PIN: `1234`).
- [x] Build `/admin` frontend portal with PIN unlock overlay.
- [x] Expose exact student identities (name, email, room number) on Admin view while keeping regular student dashboard anonymized.
- [x] Build local Wipro smart plug manager (register, edit, test LAN connection, delete) and live telemetry gauges.

## Milestone 8: Hybrid Edge-Cloud Sync & Native `uv` Project Setup
- [x] Build event-driven `CloudSyncService` with an offline replay queue (`cloud_sync_queue`) in SQLite.
- [x] Support remote status inspection and mobile WebPush notifications via Cloud DB.
- [x] Migrate Python environment to native `uv` project management (`pyproject.toml`, `uv.lock`, `uv run`).
- [x] Containerize backend with `Dockerfile` using multi-stage `uv sync`.

## Milestone 9: High-Speed Live Telemetry & Real-Time WebSockets
- [x] Optimize background telemetry polling loop to **2-second interval** (`TELEMETRY_POLL_INTERVAL=2`).
- [x] Implement real-time `telemetry_update` broadcast over WebSocket (`/ws`) delivering sub-10ms instantaneous telemetry pushes.
- [x] Build live aggregate telemetry banner in Admin portal (Total Load in Watts, Grid Voltage, Online Nodes, Active Running Machines).
- [x] Provide color-coded instantaneous telemetry cards per plug (Watts, Volts, Current, Energy) with manual refresh and cloud auto-discovery.

## Milestone 10: Schema Hardening & Multi-Socket Support
- [x] Add composite unique constraint on `(mac_address, outlet_index)` for multi-socket power strips.
- [x] Add 1-to-1 machine constraint (`uq_smart_plugs_machine_id`) and relaxed device ID indexing for clean re-pairing.
- [x] Implement compound index on `telemetry_readings(plug_id, recorded_at DESC)`.
- [x] Add consecutive failure tracking (`consecutive_failures`) and error diagnosis (`last_error`) columns.
- [x] Migrate SQLite and PostgreSQL schemas (`supabase_schema_v2.sql`) and clean dummy test records.

## Milestone 11: Remote Relay Switching & Isolated Network Fallback
- [x] Add `@router.post("/{id}/switch")` FastAPI endpoint for toggling smart plug power relays remotely.
- [x] Implement Tuya Cloud API command fallback (`{"commands": [{"code": "switch_1", "value": on}]}`) when local TCP socket connects fail due to router client isolation.
- [x] Add immediate optimistic switch toggle feedback on the admin interface.

## Milestone 12: Dual Database Portal (Local SQLite & Cloud PostgreSQL)
- [x] Build `DatabasePortalService` supporting connection pooling for both Local SQLite (`washqueue.db`) and Cloud PostgreSQL (`Supabase`).
- [x] Create administrative routes: `GET /api/admin/database/status`, `GET /api/admin/database/table-data`, and `POST /api/admin/database/query`.
- [x] Implement Read-Only safety guardrail allowing `SELECT`, `WITH`, `PRAGMA`, and `EXPLAIN` while rejecting destructive statements (`DROP`, `DELETE`, `TRUNCATE`).
- [x] Build Admin Portal **Tab 3: DATABASE_PORTAL** with database switcher, table browser tabs, pagination, and interactive SQL console with JSON export.

## Milestone 13: Dribbble Minimal Mobile & Desktop UI Transformation
- [x] Redesign resident dashboard ([`frontend/app/pages/index.vue`](file:///d:/lab/projects/washqueue/frontend/app/pages/index.vue)) using Nuxt 4 and Lucide icons.
- [x] Responsive layout: luxury centered mobile frame on desktop, edge-to-edge native app feel on mobile.
- [x] iOS Dynamic Island, 5G signal indicator, and battery status bar.
- [x] Light & Dark mode toggle with persistent transition aesthetics.
- [x] **My Active Wash Card**: live duration meter, % progress bar against 45-min cycle, power state checklist.
- [x] Top-right quick settings button linking directly to the Admin Portal.
- [x] Floating bottom dock navigation (`Waves`, `Disc`, `User`).

## Milestone 14: Student Registration, Double-Sharing Rooms & Privacy Guardrails
- [x] Implement `POST /api/auth/register` and `POST /api/auth/login` with SHA-256 + salt password hashing.
- [x] Add multi-resident double-sharing room support (composite key uniqueness on `Name + Room Number`).
- [x] Build Student Sign-In / Registration modal on client dashboard with `localStorage` session persistence.
- [x] Anonymize public machine occupancy views (`"Occupied by Resident"` vs `"Your Active Appliance"`).
- [x] Expose unmasked student details on Admin views for audit integrity.

## Milestone 15: Targeted Separate Pings, 4-Hour Power Analytics & Live Search
- [x] Separate ping actions into two distinct buttons: **`🔔 Ping Occupant`** (nudge resident to collect clothes) and **`🛡️ Alert Admin`** (escalate unattended laundry to hostel warden).
- [x] Add historical telemetry endpoint `GET /api/smart-plugs/{id}/history?hours=4` tagging `source: "local"` (1s WS density) vs `source: "cloud"` (periodic fallback).
- [x] Build interactive 4-Hour Power Graph SVG modal with smooth emerald gradient (`#10b981`), cyan diamond points (`#06b6d4`), hover tooltips, and real-time WebSocket append.
- [x] Implement real-time search filter bar in Admin Tab 4 (Users & Settings) with **`Shared`** room badges for double-sharing rooms.
- [x] Reorganize Admin portal into 4 structured tabs with collapsible quick metrics header banner and light theme as default.

## Milestone 16: Visual Graph & WebSocket Threshold Calibration Studio
- [x] Build `PATCH /api/smart-plugs/{id}/calibration` endpoint with atomic batch update for similar machines.
- [x] Create `ThresholdTunerModal.vue` with 1-click appliance profile presets (Front-Load Eco, Top-Load Heavy, Commercial Dryer, Custom).
- [x] Implement draggable horizontal guide lines on live SVG chart (Emerald for Active Running Cutoff, Amber for Soak/Pause Cutoff).
- [x] Add colored backdrop zones on the SVG chart (Emerald for Active Wash Zone, Amber for Soak Debounce Zone, Slate for Standby).
- [x] Provide real-time state simulator banner with live load readouts, soak countdown timers, and live WebSocket updates.
- [x] Add `🎛️ Tune Thresholds` action button on smart plug cards in Admin Tab 2.

## Milestone 17: Modern Layout Overhaul (Desktop Sidebar & Mobile Header)
- [x] Eliminate awkward centered mobile-frame container on desktop in favor of a modern full-width layout.
- [x] Build sticky desktop left navigation sidebar (`AppSidebar`) housing Home, Appliances Hub, Resident Profile, Settings, Admin shortcut, and Common Login.
- [x] Build native mobile top header (`AppTopHeader`) with notification bell, settings, and user avatar as the sole mobile gateway to Profile.
- [x] Streamline mobile bottom dock (`MobileBottomNav`) to `Home` and `Appliances` only with live available unit counter badge.

## Milestone 18: Tabular Telemetry & Dual Typography Engine
- [x] Establish **Plus Jakarta Sans** as primary application typeface for high readability, geometric structure, and crisp headings.
- [x] Implement **JetBrains Mono** across all numerical metrics, live stopwatch (`runningMinutes`), wattages (`340W`, `0W`), status pill badges (`46m ON`, `DONE (18m)`), grid voltages, and database rows.
- [x] Apply `-webkit-font-smoothing: antialiased`, `-moz-osx-font-smoothing: grayscale`, and `font-variant-numeric: tabular-nums` globally to eliminate digit shifting and layout twitch during real-time telemetry ticks.

## Milestone 19: Unified Common Login Portal & Admin Visual Alignment
- [x] Build unified authentication hub at `/login` serving both Resident Students and Hostel Administrators.
- [x] Implement role switcher with 1-tap demo credentials for students (`Room 214 • Akshat`) and operators (`PIN 1234`).
- [x] Realign Operator Admin Console (`/admin`) to match the desktop left sidebar navigation, top telemetry stream header, and color palette.

## Milestone 20: Codebase Modularization & Dead Code Elimination
- [x] Audit codebase for redundancy and delete 7 orphaned legacy components (`frontend/app/components/student/*` and `AdminHeader.vue`).
- [x] Modularize `frontend/app/pages/index.vue` from 1,370 monolithic lines down to ~500 lines by creating 8 focused single-responsibility components in `frontend/app/components/hub/`.
- [x] Modularize `frontend/app/pages/admin.vue` layout into `AdminSidebar.vue` and `AdminTopHeader.vue`.
- [x] Verify full production build compilation (`npm run build`) with zero errors across all routes.

## Milestone 21: Reusable SVG Logo & Multi-Tier Institutional Branding
- [x] Create standalone `<AppLogo />` Vue component (`frontend/app/components/AppLogo.vue`) encapsulating custom SVG vector graphic.
  - Supports `mode="full"` (440×120 wordmark with washer drum mark, "Wash", sky-blue "Queue", and tagline) and `mode="icon"` (aspect-square 100×100 mark).
  - Automatically resolves dark/light theme state from `useAppTheme()` to render "Wash" in `#FFFFFF` on dark backgrounds and `#191D24` on light backgrounds.
  - Generates collision-proof instance-scoped SVG gradient IDs (`wq-grad-[id]`, `wave-grad-[id]`).
- [x] Create composite `<AppBranding />` component (`frontend/app/components/common/AppBranding.vue`) rendering Logo + Divider + University/Organization + Hostel/Residence Hall.
- [x] Build `useHostelBranding()` composable managing reactive state and `localStorage` persistence for organization and hostel identity.
- [x] Build full Institutional Branding Management Suite in Admin Tab 4 (`UsersSettingsTab.vue`):
  - Inputs for organization name, acronym, and logo (URL or local image file upload).
  - Inputs for hostel name, floor location, and crest (URL or local image file upload).
  - Live side-by-side Light Mode and Dark Mode preview cards showing real-time rendering.
  - One-click reset to factory defaults.
- [x] Integrate composite branding across Mobile Header, Desktop Header, Dashboard Sidebar, Admin Sidebar, and Login Portal.

## Milestone 22: Comprehensive Font Color, Contrast & Theme Parity Audit
- [x] Audit all components across frontend codebase for hardcoded low-contrast colors and dark-only containers.
- [x] Eliminate all occurrences of legacy prototype color `#86948a` across `UsersSettingsTab.vue`, `DatabasePortalTab.vue`, `IotTab.vue`, `FleetTab.vue`, `PowerGraphModal.vue`, and `ThresholdTunerModal.vue`.
- [x] Convert modal close buttons (`✕`) to adaptive hover states (`text-slate-400 hover:text-white hover:bg-slate-800` in dark mode, `text-slate-500 hover:text-slate-900 hover:bg-slate-100` in light mode).
- [x] Update database record tables and SQL query tables in `DatabasePortalTab.vue` from hardcoded black boxes to adaptive light/dark surfaces.
- [x] Convert instantaneous power gauge box in `IotTab.vue` to theme-adaptive card.
- [x] Verify font family consistency: **Plus Jakarta Sans** for UI and **JetBrains Mono** with `tabular-nums` for all telemetry and data tables.
- [x] Execute clean production build with `npm run build` (0 errors, Exit code 0).

## Milestone 23: Washing Machine Card 4-Hour Power Consumption Popup
- [x] Implement backend endpoint `GET /api/machines/{id}/power-history?hours=4` returning full 4-hour telemetry time-series for resident inspection (no admin PIN required).
- [x] Enhance shared `<PowerGraphModal>` with dynamic wall-clock timestamps (`HH:mm`) and vertical grid lines across the X-axis (`-4h`, `-3h`, `-2h`, `-1h`, `Now`).
- [x] Make `<ApplianceCard>` fully tappable with hover affordance and click handler emitting `view-history`.
- [x] Add quick-trigger `4h 📈` button in the appliance card header and a `📈 4h Graph` pill next to current draw.
- [x] Add `📈 4h Power Curve` action button in `<HomeHeroMachine>` for the active claimed wash load.
- [x] Implement automatic fallback to realistic 4-hour simulated washing machine curve for offline demo reliability.
- [x] Mount `<PowerGraphModal>` in `frontend/app/pages/index.vue` with real-time WebSocket tick integration.
- [x] Verify production build (`npm run build` exit code 0).

## Milestone 24: Role-Based Separation & Elimination of Prototype View-Switchers
- [x] Remove prototype `"Admin Console"` navigation link (`/admin`) from the resident sidebar (`AppSidebar.vue`).
- [x] Remove `"Operator Admin Console"` button from the student settings modal (`SettingsModal.vue`).
- [x] Add an authentic `<LogOut />` action directly into the resident profile card in `AppSidebar.vue` linking cleanly to `/login`.
- [x] Remove prototype `"Resident Hub View"` (`/`) and `"Common Login Portal"` (`/login`) navigation links from the admin console sidebar (`AdminSidebar.vue`).
- [x] Remove the mobile header's `"Resident Hub"` icon button from `AdminTopHeader.vue`.
- [x] Update the header link on the locked admin PIN screen from `"Resident Hub"` to `"Login Portal"` (`/login`).
- [x] Consolidate user authentication and role-based routing through the unified `/login` portal.
- [x] Verify production build (`npm run build` exit code 0).

## Milestone 25: Washing Machine Telemetry Logging, Machine Archetypes, SQLite WAL & Visual Calibration Studio
- [x] Discovered, authenticated, and onboarded smart plug `d7fa4d27a2883bb4feqvhl` (`Washer 1 Smart Plug` at `192.168.1.15`).
- [x] Resolved Windows multi-homed / Tailscale route metric 0 packet collision by implementing automatic local subnet interface binding in `TuyaLocalProvider`.
- [x] Standardized power & voltage scaling to align with Tuya hardware specifications (0.1W and 0.1V units).
- [x] Enabled SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and `synchronous=NORMAL` on `washqueue.db` for crash-resilient persistence and non-blocking concurrent reads/writes.
- [x] Built comprehensive CLI Telemetry & Tuning suite:
  - `record_telemetry.py`: 1-second high-density logger with live terminal monitor, cycle stage detection, and auto-tuning calibration report.
  - `simulate_wash_cycle.py`: Generates authentic multi-stage washing machine profiles into database and CSV for instant testing.
  - `tune_from_csv.py`: Offline benchmark tool for testing threshold combinations against any saved CSV run.
  - `export_telemetry.py`: Dumps stored time-series telemetry from SQLite to CSV/JSON.
  - `run_background_logger.py`: Headless background daemon for continuous passive logging.
- [x] Built Backend Endpoints for Visual Studio:
  - `POST /api/smart-plugs/{id}/auto-calibrate`: Automatic historical curve analyzer calculating baseline idle, soak pause, and recommended thresholds.
  - `POST /api/smart-plugs/{id}/simulate-cycle`: Injects a synthetic 25-minute test wash cycle into the database for immediate testing.
- [x] Upgraded `<ThresholdTunerModal>` in Admin Panel:
  - Added **⚡ Auto-Detect from Graph** button for 1-click automatic threshold discovery.
  - Added **🧪 Simulate Test Cycle** button for testing without physical machines.
  - Expanded to **6 real-world appliance profile presets** (Top-Load Deep Soak, Front-Load Inverter DD, Front-Load Heated, Compact Washer, Commercial Dryer, Custom).
  - Maintained interactive drag-and-drop horizontal threshold guide lines directly on the SVG power canvas.
- [x] Verified complete backend and frontend production builds (0 errors).

## Milestone 26: Socket Churn Elimination, Concurrency Locking & Adaptive Timeout Sensitivity Engine
- [x] Diagnosed "Device Unreachable" root cause: Tuya single-TCP socket limit (port 6668), `TIME_WAIT` TCB depletion, 802.11 DTIM sleep wake-up delays, and mobile app LAN lockouts.
- [x] Implemented Persistent Connection Pooling in `TuyaLocalProvider` via module-level cache `_device_pool` with `set_socketPersistent(True)` and `set_socketNODELAY(True)`, eliminating socket churn and slashing query latency to ~15ms.
- [x] Implemented Adaptive Timeout Sensitivity: 1.5s fast probe for persistent open sockets; 3.5s timeout with 2 retries and 0.2s delay for fresh connections and re-negotiations.
- [x] Implemented 3-Miss Grace Buffer in `telemetry_service.py`: Requires 3 consecutive failed polling ticks before transitioning `plug.is_online = False`, completely eliminating UI online/offline badge flickering.
- [x] Built Collision Cooldown Engine: 15-second cooldown window triggered on local socket conflicts (e.g. mobile app holding port 6668); routes traffic seamlessly through Tuya Cloud OpenAPI during cooldown before executing a quiet local probe.
- [x] Implemented Per-Device Asynchronous Locking: Wrapped device operations in `get_device_lock(device_id)` to serialize background polling and manual `/switch` toggles.
- [x] Created `BoundOutletDevice` subclassing `tinytuya.OutletDevice` to bind specifically to physical Wi-Fi NIC (`192.168.1.12`), completely eliminating unsafe global `socket.socket` monkey-patching.
- [x] Built Smart Dual-Mode into CLI Utilities (`read_plug.py` & `record_telemetry.py`): Automatically checks for running FastAPI backend and streams from local API/WebSocket to eliminate port 6668 competition.
- [x] Created and verified automated test suite in `backend/tests/test_socket_resilience.py` (7 tests, 100% pass).

## Milestone 27: Hostel Local Timezone Localization & 12h/24h Display Engine
- [x] Build system-wide timezone formatting architecture converting UTC ISO timestamps (`Z`) to local hostel timezone (default: `Asia/Kolkata` - Indian Standard Time).
- [x] Create `useAppTimezone()` frontend composable with reactive `formatDateTime()`, `formatTime()`, `formatDate()`, and 12-hour AM/PM vs 24-hour military clock display preference toggle.
- [x] Build Timezone & Clock Configuration Card in Operator Console Tab 4 (`UsersSettingsTab.vue`) allowing admins to select campus timezones and toggle time formatting.
- [x] Apply reactive timezone formatting across both Resident Hub (`AppTopHeader.vue`, `HomeHeroMachine.vue`, `ApplianceCard.vue`, `PowerGraphModal.vue`) and Operator Console (`FleetTab.vue`, `IotTab.vue`, `UsersSettingsTab.vue`, `DatabasePortalTab.vue`).
- [x] Verify timezone formatting in automated scripts and visual browser sessions.

## Milestone 28: Dynamic 1-Minute Rotating Cryptographic QR Code Station & Clean Onboarding
- [x] Eliminate all dummy demo credentials, "One-Tap Demo" buttons, and mock cascading university dropdowns.
- [x] Implement HMAC-SHA256 physical kiosk registration token generation in `qr_service.py` with 60-second rotation:
  $$\text{Token} = \text{hostel\_id} \,.\, \text{timestamp} \,.\, \text{nonce} \,.\, \text{HMAC}_{24}(\dots)$$
- [x] Implement a 360-second verification window (60s rotation on kiosk + 300s grace window once opened on student's mobile browser).
- [x] Add protected admin endpoints `GET /api/admin/onboarding-qr` (`X-Admin-PIN` required) and public verification endpoint `POST /api/admin/onboarding-qr/verify`.
- [x] Build dedicated Fullscreen Tablet Kiosk Mode (`AdminQrKioskModal.vue`) with high-contrast vector SVG QR code, circular countdown progress ring, and hostel branding.
- [x] Build "Hostel Desk QR Required" guidance view on `/login` preventing unverified signups while allowing existing residents to log in normally.
- [x] Display active 5-minute grace countdown timer and emerald "Hostel Desk Scan Verified" badge on student registration form.

## Milestone 29: Student Registration Request & Administrator Approval Workflow
- [x] Extend `User` model with `phone: str | None`, `status: str` (`"pending"` | `"approved"` | `"rejected"`), and `approved_at: datetime | None`.
- [x] Implement dynamic column migration `migrate_user_columns()` in `backend/app/main.py` for automated schema upgrading without data loss.
- [x] Enforce `status = "pending"` upon student registration in `POST /api/auth/register`.
- [x] Block sign-in attempts in `POST /api/auth/login` with HTTP 403 Forbidden for unapproved accounts with clear guidance messages.
- [x] Implement administrative approval endpoints in `routers/admin.py`: `GET /api/admin/pending-registrations`, `POST /api/admin/registrations/{id}/approve`, and `POST /api/admin/registrations/{id}/reject`.
- [x] Build live `PENDING_REGISTRATION_REQUESTS` queue card in Operator Console (`UsersSettingsTab.vue`) showing applicant name, room, mobile, and localized submission timestamp with 1-click Approve and Reject buttons.
- [x] Add status column with styled pill badges (`APPROVED`, `PENDING`, `REJECTED`) in the registered resident accounts table.
- [x] Implement confirmation screen on student login portal with guidance to await administrative approval.
- [x] Verify approval flow end-to-end via automated integration script and visual browser recording.







