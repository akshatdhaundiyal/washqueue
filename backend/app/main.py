import asyncio
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.database import engine, Base, get_db
    from app.routers.auth import router as auth_router
    from app.routers.machines import router as machines_router
    from app.routers.admin import router as admin_router
    from app.routers.smart_plugs import router as smart_plugs_router
    from app.routers.websocket import router as websocket_router
    from app.scheduler import check_and_update_overdue_bookings
    from app.telemetry_service import start_telemetry_polling_loop
    from app.cloud_sync_service import start_cloud_sync_worker
    from app.config import settings
except ImportError:
    from .database import engine, Base, get_db
    from .routers.auth import router as auth_router
    from .routers.machines import router as machines_router
    from .routers.admin import router as admin_router
    from .routers.smart_plugs import router as smart_plugs_router
    from .routers.websocket import router as websocket_router
    from .scheduler import check_and_update_overdue_bookings
    from .telemetry_service import start_telemetry_polling_loop
    from .cloud_sync_service import start_cloud_sync_worker
    from .config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def migrate_user_columns(sync_conn):
            try:
                # Check for SQLite table columns
                cursor = sync_conn.connection.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cursor.fetchall()]
                if columns:
                    for col in ["university", "college", "hostel"]:
                        if col not in columns:
                            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} VARCHAR")
            except Exception:
                pass

        await conn.run_sync(migrate_user_columns)
    # Ensure baseline Washer 1, Admin User, and real Smart Plug exist if empty (clean initial startup)
    from sqlalchemy import select
    try:
        from app.database import async_session
        from app.models import Machine, User, SmartPlug
    except ImportError:
        from .database import async_session
        from .models import Machine, User, SmartPlug

    async with async_session() as db:
        res = await db.execute(select(Machine))
        w1 = res.scalars().first()
        if not w1:
            w1 = Machine(name="Washer 1", status="available")
            db.add(w1)
            await db.flush()

        res_user = await db.execute(select(User).where(User.is_admin.is_(True)))
        if not res_user.scalars().first():
            import uuid
            admin_user = User(
                id=uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                name="Hostel Admin",
                email="admin@hostel.edu",
                role="admin",
                is_admin=True
            )
            db.add(admin_user)

        res_plug = await db.execute(select(SmartPlug))
        if not res_plug.scalars().first():
            import os
            dev_id = os.getenv("TUYA_DEVICE_ID", "d7fa4d27a2883bb4feqvhl")
            dev_ip = os.getenv("TUYA_DEVICE_IP", "192.168.1.15")
            dev_key = os.getenv("TUYA_LOCAL_KEY", "X@iLAIv|R(t(/(su")
            dev_mac = os.getenv("TUYA_DEVICE_MAC", "d8:1f:12:48:94:c7")
            if dev_id and dev_key and w1:
                db.add(SmartPlug(
                    machine_id=w1.id,
                    name="Washer 1 Smart Plug",
                    device_id=dev_id,
                    local_key=dev_key,
                    ip_address=dev_ip,
                    mac_address=dev_mac,
                    protocol_version="3.3",
                    power_threshold_running=10.0,
                    power_threshold_idle=5.0,
                    debounce_seconds=120,
                    is_online=True
                ))
        await db.commit()

    # Launch background workers
    telemetry_task = asyncio.create_task(
        start_telemetry_polling_loop(interval_seconds=settings.telemetry_poll_interval)
    )
    cloud_sync_task = asyncio.create_task(
        start_cloud_sync_worker(interval_seconds=15)
    )
    yield
    # Cancel background tasks and dispose connection pool on shutdown
    telemetry_task.cancel()
    cloud_sync_task.cancel()
    await engine.dispose()

app = FastAPI(
    title="WashQueue Hostel Laundry Management API",
    description="Hybrid Edge-Cloud backend with local smart plug telemetry, WebSocket broadcasts, & cloud sync.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(machines_router)
app.include_router(admin_router)
app.include_router(smart_plugs_router)
app.include_router(websocket_router)



@app.post("/api/scheduler/tick")
async def run_scheduler_tick(db: AsyncSession = Depends(get_db)):
    """
    Lightweight background scheduler task endpoint.
    Checks for bookings where estimated_end_at <= current_time and
    moves the machine status automatically to 'idle_full'.
    """
    updated_machines = await check_and_update_overdue_bookings(db)
    return {
        "status": "success",
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_count": len(updated_machines),
        "updated_machines": updated_machines
    }

@app.get("/")
async def root():
    return {
        "app": "Hostel Laundry Management API",
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
