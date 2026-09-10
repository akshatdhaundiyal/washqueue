# WashQueue - Hostel Laundry Management & Smart Plug Telemetry System

**WashQueue** is a real-time hostel laundry management appliance built with a **Nuxt 4 / Vue 3** frontend, **FastAPI** backend, **Embedded SQLite & Cloud DB Sync**, **Native WebSockets (`/ws`)**, and **Wipro / Tuya Local Smart Plug Telemetry**.

---

## Technical Stack & Architecture

- **Frontend**: Nuxt 4 (Vue 3), Tailwind CSS (`darkMode: 'class'`), Native WebSocket Client (`useLocalWebSocket`), Lucide Icons, `@supabase/supabase-js` (Cloud fallback)
- **Typography Engine**: **Plus Jakarta Sans** (Primary UI & headings) paired with **JetBrains Mono** (`tabular-nums`, live stopwatch, power draws, voltages, telemetry counters, IP/MAC addresses)
- **Backend Engine**: FastAPI, SQLAlchemy 2.0, `aiosqlite`, `asyncpg`, Pydantic v2, `tinytuya`
- **Smart Plug Integration**: Provider-agnostic local socket polling over LAN (port 6668, 1-second interval, zero cloud fees, 2-minute soak debounce) with automatic Tuya OpenAPI cloud fallback
- **Database Architecture**: Embedded SQLite (`washqueue.db`) primary database + Event-Driven Cloud Sync Engine with an offline replay queue
- **Python Project Management**: Powered natively by **`uv`** (`pyproject.toml`, `uv.lock`, `uv run`)

For deep-dive architectural diagrams and data flows, see [docs/architecture.md](docs/architecture.md).  
Project tracking milestones can be reviewed in [docs/milestones.md](docs/milestones.md).  
For smart plug telemetry details, see [docs/smart_plug_telemetry.md](docs/smart_plug_telemetry.md).  
For database portal documentation, see [docs/database_portal.md](docs/database_portal.md).

---

## Key Features & Capabilities

### 1. Reusable SVG Logo & Brand Hierarchy Component
- **`<AppLogo />` ([`AppLogo.vue`](file:///d:/lab/projects/washqueue/frontend/app/components/AppLogo.vue))**: Globally auto-imported component rendering the custom SVG vector lockup.
  - Supports `mode="full"` (complete 440×120 wordmark with washer drum mark, "Wash", sky-blue "Queue", and "HOSTEL LAUNDRY IOT" tagline) and `mode="icon"` (aspect-square 100×100 mark).
  - **Auto-Theme Adaptive**: Automatically resolves active theme from `useAppTheme()`—"Wash" renders in `#FFFFFF` in dark mode and `#191D24` in light mode with zero configuration.
  - **Collision-Proof Gradients**: Dynamically namespaces SVG linear gradient IDs per instance to prevent DOM gradient collisions.
- **`<AppBranding />` ([`AppBranding.vue`](file:///d:/lab/projects/washqueue/frontend/app/components/common/AppBranding.vue))**: Composite branding lockup displaying:
  1. WashQueue Logo (Icon or Full)
  2. Vertical Divider
  3. University / Organization Logo & Name
  4. Hostel / Residence Hall Name & Crest

### 2. Institutional Branding Customization Suite
- **Admin Configuration Portal ([`UsersSettingsTab.vue`](file:///d:/lab/projects/washqueue/frontend/app/components/admin/UsersSettingsTab.vue))**:
  - Located in Tab 4 ("Users & Settings") of the Operator Admin Console.
  - Allows operators to configure **University/Organization Name**, **Short Code**, and **Logo** (via URL or local file upload).
  - Allows configuration of **Hostel/Hall Name**, **Floor Location**, and **Hostel Crest/Logo** (via URL or local file upload).
  - **Live Header Preview**: Instantaneous side-by-side Light Mode and Dark Mode preview cards showing real-time header rendering as you edit.
  - **Auto-Persistence**: Saves immediately to `localStorage` via [`useHostelBranding.ts`](file:///d:/lab/projects/washqueue/frontend/app/composables/useHostelBranding.ts) and syncs across all headers, sidebars, and the login portal.

### 3. Modern Responsive Layout (Desktop Left Column + Mobile Header)
- **Desktop View**: Clean left navigation sidebar (`<aside>`) containing branding, navigation tabs (**Home Status**, **Appliances Hub**, **Resident Profile**, **Settings**), Admin Console shortcut, Common Login shortcut, light/dark theme switcher, and bottom resident preview.
- **Mobile View**: Edge-to-edge native mobile header with **AppBranding**, **Notification Bell**, **Settings**, and **User Avatar** (the sole mobile navigation route to Profile). Clean floating bottom pill dock for fast switching between **Home** and **Appliances** with live free machine counter badge.

### 4. Tabular Telemetry, Typography & Color Consistency
- **Plus Jakarta Sans**: High x-height, contemporary geometric typography for all interface labels, headings, modal dialogs, and buttons.
- **JetBrains Mono**: Crisp monospace digits with `tabular-nums` (`font-variant-numeric: tabular-nums`) applied across all timers (`28 min running`), live wattages (`340W`, `0W`), appliance badges (`46m ON`, `DONE (18m)`), grid voltages (`234.1V`), and database query outputs. Digits never twitch or shift when incrementing.
- **100% Theme Color Parity**: Full audit completed—eliminated legacy low-contrast colors (`#86948a`) and dark-only table containers. Light mode provides high-contrast, beautiful slate typography and crisp borders across all admin tabs, modals, and tables.

### 5. Unified Common Login Portal (`/login`)
- Dual-role authentication hub serving both **Resident Students** and **Hostel Administrators**.
- **Student Role**: Sign in or Register with Full Name, Room Number (with double-sharing room support), and Password, plus 1-tap demo login (`Room 214 • Akshat`).
- **Admin Role**: Security PIN verification with 1-tap demo fill (`PIN 1234`), storing session securely in `sessionStorage` and redirecting directly into `/admin`.

### 6. Operator Admin Console (`/admin`)
- Built with the exact same left sidebar navigation structure as the main app.
- 4 comprehensive operator management modules:
  1. **Fleet & Bookings Hub**: Real-time status, motor power indicators, and student identities.
  2. **Smart Plugs & Tuya IoT Nodes**: 1-second telemetry readings, relay remote toggles, and calibration modals.
  3. **Database Portal**: Interactive SQL execution console and schema viewer with JSON export.
  4. **Users & Settings**: Searchable resident directory with multi-sharing room badges, and the new **Institution & Hostel Branding Portal**.
- Desktop telemetry header with live sub-10ms WebSocket connection indicator and 1-second auto-refresh toggle.

### 7. Modular Component Architecture
- Completely refactored from large monolithic templates into focused, single-responsibility components:
  - `frontend/app/components/hub/`: `AppSidebar.vue`, `AppTopHeader.vue`, `HomeHeroMachine.vue`, `OverviewCards.vue`, `ApplianceCard.vue`, `ResidentProfileView.vue`, `SettingsModal.vue`, `MobileBottomNav.vue`.
  - `frontend/app/components/admin/`: `AdminSidebar.vue`, `AdminTopHeader.vue`, `AdminMetricsBanner.vue`, `AdminAuthOverlay.vue`, `FleetTab.vue`, `IotTab.vue`, `DatabasePortalTab.vue`, `UsersSettingsTab.vue`, etc.
  - `frontend/app/components/common/`: `AppLogo.vue`, `AppBranding.vue`.

### 8. Student Registration & Multi-Sharing Room Support
- Uniqueness is keyed on `(Student Name, Room Number)`. Roommates share the same room number without credential collisions.
- **Public Dashboard (`/`)**: Displays anonymized status (**`"Occupied by Resident"`**) to protect privacy while showing live cycle progress and power state.
- **Operator Console (`/admin`)**: Unmasks exact student identities (**Name**, **Room Number**, **Start Time**) for management auditing.

### 9. Smart Plug Telemetry & 4-Hour Power Graph
- **Card-Tap Resident Telemetry**: Tapping any washing machine card on the student dashboard pops up its **4-hour historical power consumption curve**.
- **Dynamic Wall-Clock X-Axis**: Displays actual formatted local time labels (`HH:mm`, e.g. `08:30 (-4h)`, `09:30 (-3h)`, `10:30 (-2h)`, `11:30 (-1h)`, `12:30 (Live)`) with vertical time grid lines.
- **Public History API**: `GET /api/machines/{id}/power-history?hours=4` returns chronological power telemetry without requiring an admin PIN.
- **Dual-Series Curves**:
  - **🟢 Local LAN / WebSocket (`#10b981`)**: Smooth solid emerald gradient curve for ~1-second high-density local telemetry.
  - **🔷 Tuya Cloud Fallback (`#06b6d4`, `◆`)**: Cyan diamond point markers and dashed connector lines.
- **Instant Hover Readout**: Hovering any point on the SVG chart displays exact timestamp, Watts, Volts, and telemetry source (`● LOCAL_WS` vs `◆ TUYA_CLOUD`).
- **Offline Simulation**: Automatically generates a realistic 4-hour cycle curve (motor agitation, soak pauses, high-speed spin, cooldown) for demo machines or when smart plugs are offline.

### 10. Strict Role-Based Architecture & Authentication
- **Unified Login Portal (`/login`)**: Single authentic point of entry for residents (Student ID / Room Number) and operators (Admin PIN).
- **Zero Prototype Clutter**: Eliminated redundant developer toggle buttons (`"Admin Console"` link removed from student navigation, `"Resident Hub"` link removed from operator console).
- **Resident Navigation**: 100% focused on student laundry workflows (**Home Status**, **Appliances Hub**, **Resident Profile**, **Settings**) with an authentic `<LogOut />` button attached to the Resident Profile card.
- **Operator Console**: Exclusively dedicated to hostel fleet management, IoT telemetry, database inspection, and institutional identity, protected by a secure **`Lock Admin Session`** control.

---

## Setup Instructions

### 1. Database Setup
- **Local Edge Database**: Out of the box, WashQueue automatically creates and seeds `backend/washqueue.db` using SQLite upon backend startup. Zero database setup required!
- **Cloud Database (Optional for remote 4G/5G mobile access)**: Run `supabase_schema_v2.sql` in your Supabase SQL editor.

### 2. Backend Environment Config
Create a `.env` file in the `backend/` directory:
```env
ADMIN_PIN="1234"
TELEMETRY_POLL_INTERVAL=1
# Optional: Set CLOUD_DATABASE_URL if connecting to external PostgreSQL/Supabase
# CLOUD_DATABASE_URL="postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres"
```

### 3. Frontend Environment Config
Create a `.env` file in the `frontend/` directory:
```env
API_BASE_URL="http://localhost:8000"
```

---

## Running the Application Locally with `uv`

### Step A: Start the FastAPI Backend using `uv`
Ensure Python 3.11+ and `uv` are installed:

```bash
cd backend

# Synchronize dependencies natively with uv
uv sync

# Start the FastAPI dev server with auto-reload using uv
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`.

### Step B: Start the Nuxt 4 Frontend
Open a separate terminal window:

```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000`.

---

## Running via Docker Compose

```bash
docker compose up --build
```
- **Student Dashboard**: `http://localhost:3000`
- **Operator Console**: `http://localhost:3000/admin` (Default PIN: `1234`)
- **Common Login Portal**: `http://localhost:3000/login`
- **Interactive API Docs**: `http://localhost:8000/docs`
