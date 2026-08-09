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

## Milestone 4: Nuxt 3 Frontend Init & Tailwind Integration
- [x] Initialize Nuxt 3 project structure in `frontend/`.
- [x] Add Tailwind CSS module and configure styles/typography.
- [x] Build main layout framework and responsive design grids.

## Milestone 5: Local Edge WebSockets & Real-Time Sync
- [x] Implement native FastAPI WebSocket ConnectionManager (`/ws`).
- [x] Connect Nuxt 3 frontend using custom `useLocalWebSocket` composable for zero-latency local LAN updates.
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
