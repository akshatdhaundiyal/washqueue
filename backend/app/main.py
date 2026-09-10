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
    # Auto-seed initial machines and users if empty
    from sqlalchemy import select
    try:
        from app.database import async_session
        from app.models import Machine, User
    except ImportError:
        from .database import async_session
        from .models import Machine, User


    async with async_session() as db:
        res = await db.execute(select(Machine))
        if not res.scalars().first():
            initial_machines = [
                Machine(name="Washer 1", status="available"),
                Machine(name="Washer 2", status="available"),
                Machine(name="Washer 3", status="available"),
                Machine(name="Washer 4", status="available"),
                Machine(name="Dryer 1", status="available"),
                Machine(name="Dryer 2", status="available"),
                Machine(name="Dryer 3", status="available"),
                Machine(name="Dryer 4", status="available"),
            ]
            db.add_all(initial_machines)
            
            import uuid
            initial_users = [
                User(id=uuid.UUID('11111111-1111-1111-1111-111111111111'), name="Alex (User A)", email="alex@hostel.edu", is_admin=False),
                User(id=uuid.UUID('22222222-2222-2222-2222-222222222222'), name="Blake (User B)", email="blake@hostel.edu", is_admin=False),
                User(id=uuid.UUID('33333333-3333-3333-3333-333333333333'), name="Charlie (User C)", email="charlie@hostel.edu", is_admin=False),
                User(id=uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), name="Hostel Admin", email="admin@hostel.edu", is_admin=True),
            ]
            db.add_all(initial_users)
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
