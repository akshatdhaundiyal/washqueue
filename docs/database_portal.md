# Dual Database Portal Guide (Local SQLite & Cloud PostgreSQL)

The **WashQueue Dual Database Portal** is an administrative tool built directly into the Admin dashboard (`/admin`) that allows hostel operators to inspect tables, browse records, and execute custom SQL queries across both the local edge database and the remote cloud database.

---

## 1. Supported Database Targets

| Target | Engine / Dialect | Primary Location | Purpose |
| :--- | :--- | :--- | :--- |
| **🖥️ Local Edge** | SQLite (`sqlite+aiosqlite`) | `backend/washqueue.db` | Primary offline-first storage on the edge appliance for zero-latency local operations. |
| **☁️ Cloud Storage** | PostgreSQL (`asyncpg`) | Supabase / Remote Postgres | Secondary cloud database used for remote phone queries and WebPush notifications. |

---

## 2. Configuration

### Local Database
No setup needed. Defaults to `sqlite+aiosqlite:///./washqueue.db`.

### Cloud Database (Supabase)
To query the cloud database through the portal, add the connection string to `backend/.env`:

```env
CLOUD_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```
*(Alternatively, `SUPABASE_DATABASE_URL` is also supported.)*

> [!NOTE]
> If `CLOUD_DATABASE_URL` is omitted, the portal will clearly show `🟡 Cloud Not Configured` with setup instructions, while the Local SQLite database remains 100% operational.

---

## 3. Features

### A. Target Switcher & Connection Health
* Easily toggle between `🖥️ Local (SQLite)` and `☁️ Cloud (Supabase)`.
* Instant connection indicator: `🟢 LOCAL ONLINE (sqlite)` or `🟢 CLOUD ONLINE (postgresql)`.

### B. Table Browser & Row Counts
* Automatically discovers public tables in the target database (`machines`, `smart_plugs`, `telemetry_readings`, `users`, `bookings`, `queue`).
* Displays real-time row count badges on each table tab.
* Clicking any table tab loads paginated records (Previous / Next navigation) with column headers and cell values.

### C. Interactive SQL Query Console
* Code-styled dark SQL textarea with preset query chips:
  * `SELECT * FROM smart_plugs;`
  * `SELECT * FROM telemetry_readings ORDER BY recorded_at DESC LIMIT 20;`
  * `SELECT * FROM machines;`
  * `SELECT * FROM users;`
* **Execution Telemetry**: Displays exact query execution duration (e.g. `⏱️ 0.93 ms | 8 rows returned`).
* **Dynamic Tabular Grid**: Handles arbitrary columns, nulls, booleans, and timestamps.
* **📥 Export JSON Button**: One-click download of the active query results for offline analysis.

---

## 4. Security & Safety Guardrails

To prevent accidental data loss from the browser console, the query runner enforces a **strict Read-Only guardrail**:

1. **Permitted Statements**: Only queries starting with `SELECT`, `WITH`, `PRAGMA`, or `EXPLAIN` are executed.
2. **Blocked Statements**: Any destructive SQL statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`) are rejected immediately with an HTTP 400 error.
3. **PIN Authentication**: Access requires the `X-Admin-PIN` header (`ADMIN_PIN` configured in `.env`).
