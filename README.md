# WashQueue - Hostel Laundry Management & Smart Plug Telemetry System

**WashQueue** is a real-time hostel laundry management appliance built with a **Nuxt 3** frontend, **FastAPI** backend, **Embedded SQLite & Cloud DB Sync**, **Native WebSockets (`/ws`)**, and **Wipro / Tuya Local Smart Plug Telemetry**.

---

## Technical Stack & Architecture

- **Frontend**: Nuxt 3 (Vue 3), Tailwind CSS, Native WebSocket Client (`useLocalWebSocket`), `@supabase/supabase-js` (Cloud fallback)
- **Backend Engine**: FastAPI, SQLAlchemy 2.0, `aiosqlite`, `asyncpg`, Pydantic v2, `tinytuya`
- **Smart Plug Integration**: Provider-agnostic local socket polling over LAN (zero cloud fees, 2-minute soak debounce)
- **Database Architecture**: Embedded SQLite (`washqueue.db`) primary database + Event-Driven Cloud Sync Engine with an offline replay queue
- **Python Project Management**: Powered natively by **`uv`** (`pyproject.toml`, `uv.lock`, `uv run`)

For deep-dive architectural diagrams and data flows, see [docs/architecture.md](file:///d:/lab/projects/washqueue/docs/architecture.md).
Project tracking milestones can be reviewed in [docs/milestones.md](file:///d:/lab/projects/washqueue/docs/milestones.md).

---

## Setup Instructions

### 1. Database Setup
- **Local Edge Database**: Out of the box, WashQueue automatically creates and seeds [washqueue.db](file:///d:/lab/projects/washqueue/backend/washqueue.db) using SQLite upon backend startup. Zero database setup required!
- **Cloud Database (Optional for remote 4G/5G mobile access)**: Run [supabase_schema_v2.sql](file:///d:/lab/projects/washqueue/supabase_schema_v2.sql) in your Supabase SQL editor.

### 2. Backend Environment Config
Create a `.env` file in the `backend/` directory (optional for cloud sync):
```env
# Optional: Set DATABASE_URL if connecting to external PostgreSQL/Supabase
# DATABASE_URL="postgresql://postgres:password@localhost:5432/laundry"
ADMIN_PIN="1234"
TELEMETRY_POLL_INTERVAL=10
```

### 3. Frontend Environment Config
Create a `.env` file in the `frontend/` directory:
```env
API_BASE_URL="http://localhost:8000"
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_KEY="your-supabase-anon-public-key"
```

---

## Running the Application Locally with `uv`

### Step A: Start the FastAPI Backend using `uv`
Ensure Python 3.11+ and `uv` are installed:

```bash
cd backend

# Synchronize dependencies natively with uv
uv sync

# Run verification tests using uv
uv run python verify_smart_plugs.py
uv run python verify_backend.py

# Start the FastAPI dev server with auto-reload using uv
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`.

### Step B: Start the Nuxt 3 Frontend
Open a separate terminal window:

```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000`.

---

## Key Features & Operations

1. **Local Smart Plug LAN Telemetry**:
   - Polled over TCP port 6668 via `tinytuya`.
   - Power draw spikes (`>= 10W`) auto-start machine cycles.
   - Low power (`< 5W`) triggers a **2-minute soak debounce window** before marking cycles complete (`idle_full`).

2. **PIN-Protected Admin Portal (`/admin`)**:
   - Access at `http://localhost:3000/admin` (Default PIN: `1234`).
   - **User Identity Unmasking**: Admins see exact student names, emails, and active booking details.
   - **Smart Plug Manager**: Register, edit, test LAN sockets, and remove smart plugs.

3. **Student Privacy Dashboard (`/`)**:
   - Anonymized student view showing machine availability, live power badges (`⚡ 120W`), waitlist position, and countdown timers.

4. **Hybrid Edge-Cloud Resilience**:
   - Operates 100% offline during internet outages.
   - Replays buffered events to Cloud DB when internet connectivity recovers.

---

## Running via Docker Compose with Hot-Reloading

```bash
docker compose up --build
```
- **Backend Hot-Reload**: Editing any `.py` file inside `backend/app/` will instantly trigger Uvicorn auto-reload inside the container (powered by `WATCHFILES_FORCE_POLLING=true`).
- **Frontend Hot-Reload**: Editing any `.vue` or `.ts` file inside `frontend/` will trigger instant Vite HMR updates in the browser (powered by `CHOKIDAR_USEPOLLING=true`).

- Student Dashboard: `http://localhost:3000`
- Admin Portal: `http://localhost:3000/admin`
- Interactive API Docs: `http://localhost:8000/docs`

