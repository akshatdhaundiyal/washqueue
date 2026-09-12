from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

try:
    from app.database import get_db
    from app.middleware.auth import require_admin_pin
    from app.config import settings
    from app.qr_service import generate_registration_token, verify_registration_token, get_lan_ip
    from app.schemas import (
        PinVerifyRequest, UserResponse, AdminMachineDetailResponse,
        AdminBookingResponse, AdminQueueResponse, SmartPlugResponse, TelemetryReadingResponse,
        SystemSettingsResponse, SystemSettingsUpdateRequest,
        OnboardingQrResponse, VerifyQrRequest
    )
    from app.repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        UserRepository, SmartPlugRepository, TelemetryRepository
    )
except ImportError:
    from ..database import get_db
    from ..middleware.auth import require_admin_pin
    from ..config import settings
    from ..qr_service import generate_registration_token, verify_registration_token, get_lan_ip
    from ..schemas import (
        PinVerifyRequest, UserResponse, AdminMachineDetailResponse,
        AdminBookingResponse, AdminQueueResponse, SmartPlugResponse, TelemetryReadingResponse,
        SystemSettingsResponse, SystemSettingsUpdateRequest,
        OnboardingQrResponse, VerifyQrRequest
    )
    from ..repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        UserRepository, SmartPlugRepository, TelemetryRepository
    )

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/verify-pin")
async def verify_admin_pin(req: PinVerifyRequest):
    """Verifies the 4-digit Admin PIN."""
    if req.pin == settings.admin_pin:
        return {"status": "success", "valid": True, "message": "Admin PIN authenticated successfully."}
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid Admin PIN."
    )

@router.get("/machines", response_model=List[AdminMachineDetailResponse], dependencies=[Depends(require_admin_pin)])
async def get_admin_machines(db: AsyncSession = Depends(get_db)):
    """
    Detailed machine list for Admins only.
    Resolves and exposes exact student identities (name & email) holding active bookings or in queue.
    """
    machines = await MachineRepository.get_all(db)
    response = []

    for machine in machines:
        active_booking = await BookingRepository.get_active_booking(db, machine.id)
        queue = await QueueRepository.get_active_queue(db, machine.id)
        plug = await SmartPlugRepository.get_by_machine_id(db, machine.id)

        # 1. Resolve Active Booking user details
        booking_data = None
        if active_booking:
            user = await UserRepository.get_by_id(db, active_booking.user_id)
            user_name = user.name if user else f"Student ({str(active_booking.user_id)[:6]})"
            user_email = user.email if user else None

            booking_data = AdminBookingResponse(
                id=active_booking.id,
                machine_id=active_booking.machine_id,
                user_id=active_booking.user_id,
                started_at=active_booking.started_at,
                estimated_end_at=active_booking.estimated_end_at,
                cleared_at=active_booking.cleared_at,
                user_name=user_name,
                user_email=user_email
            )

        # 2. Resolve Queue user details
        queue_data = []
        for q in queue:
            user = await UserRepository.get_by_id(db, q.user_id)
            user_name = user.name if user else f"Student ({str(q.user_id)[:6]})"
            user_email = user.email if user else None

            queue_data.append(
                AdminQueueResponse(
                    id=q.id,
                    machine_id=q.machine_id,
                    user_id=q.user_id,
                    joined_at=q.joined_at,
                    position=q.position,
                    status=q.status,
                    user_name=user_name,
                    user_email=user_email
                )
            )

        # 3. Resolve Smart Plug and Latest Telemetry
        plug_data = SmartPlugResponse.model_validate(plug) if plug else None
        latest_telemetry_data = None
        if plug:
            latest_reading = await TelemetryRepository.get_latest_for_plug(db, plug.id)
            if latest_reading:
                latest_telemetry_data = TelemetryReadingResponse.model_validate(latest_reading)

        response.append(
            AdminMachineDetailResponse(
                id=machine.id,
                name=machine.name,
                status=machine.status,
                active_booking=booking_data,
                queue=queue_data,
                smart_plug=plug_data,
                latest_telemetry=latest_telemetry_data
            )
        )

    return response

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(require_admin_pin)])
async def get_all_users(db: AsyncSession = Depends(get_db)):
    """List all registered users (Admin only)."""
    users = await UserRepository.get_all(db)
    return [UserResponse.model_validate(u) for u in users]

@router.get("/usage-stats", dependencies=[Depends(require_admin_pin)])
async def get_usage_stats(db: AsyncSession = Depends(get_db)):
    """Get system-wide laundry usage and telemetry statistics (Admin only)."""
    machines = await MachineRepository.get_all(db)
    plugs = await SmartPlugRepository.get_all(db)
    
    total_machines = len(machines)
    online_plugs = sum(1 for p in plugs if p.is_online)
    in_use_count = sum(1 for m in machines if m.status == "in_use")
    idle_full_count = sum(1 for m in machines if m.status == "idle_full")
    available_count = sum(1 for m in machines if m.status == "available")

    return {
        "total_machines": total_machines,
        "online_plugs": online_plugs,
        "status_breakdown": {
            "available": available_count,
            "in_use": in_use_count,
            "idle_full": idle_full_count
        }
    }

# ==========================================
# Database Portal Endpoints (Local & Cloud)
# ==========================================

class DatabaseQueryRequest(BaseModel):
    target: str = "local"
    query: str

@router.get("/database/status", dependencies=[Depends(require_admin_pin)])
async def get_database_status(target: str = "local"):
    """
    Returns connection health and table listing with row counts
    for the specified target ('local' or 'cloud').
    """
    try:
        from app.database_portal_service import DatabasePortalService
    except ImportError:
        from ..database_portal_service import DatabasePortalService

    return await DatabasePortalService.get_status(target)

@router.get("/database/table-data", dependencies=[Depends(require_admin_pin)])
async def get_database_table_data(
    target: str = "local",
    table_name: str = "machines",
    limit: int = 50,
    offset: int = 0
):
    """
    Returns schema columns and paginated row records for a given table.
    """
    try:
        from app.database_portal_service import DatabasePortalService
    except ImportError:
        from ..database_portal_service import DatabasePortalService

    try:
        return await DatabasePortalService.get_table_data(
            target=target,
            table_name=table_name,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/database/query", dependencies=[Depends(require_admin_pin)])
async def execute_database_query(req: DatabaseQueryRequest):
    """
    Executes a read-only SQL query against either Local (SQLite) or Cloud (PostgreSQL).
    """
    try:
        from app.database_portal_service import DatabasePortalService
    except ImportError:
        from ..database_portal_service import DatabasePortalService

    try:
        return await DatabasePortalService.execute_query(
            target=req.target,
            query_str=req.query
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================
# System Settings & Timezone Endpoints
# ==========================================

@router.get("/settings", response_model=SystemSettingsResponse)
async def get_admin_system_settings():
    """Retrieve system timezone and clock settings."""
    return SystemSettingsResponse(
        timezone=settings.timezone,
        default_timezone="Asia/Kolkata",
        server_time_utc=datetime.now(timezone.utc)
    )

@router.post("/settings", dependencies=[Depends(require_admin_pin)])
async def update_admin_system_settings(req: SystemSettingsUpdateRequest):
    """Update system timezone (Admin only)."""
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(req.timezone)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid IANA timezone identifier: '{req.timezone}'"
        )
    settings.timezone = req.timezone
    return {
        "status": "success",
        "timezone": settings.timezone,
        "message": f"System timezone successfully set to {settings.timezone}"
    }

# ==========================================
# 1-Minute Rotating Onboarding QR Endpoints
# ==========================================

@router.get("/onboarding-qr", response_model=OnboardingQrResponse, dependencies=[Depends(require_admin_pin)])
async def get_onboarding_qr(hostel_id: str = "block-b", base_url: str = None):
    """
    Generates a 60-second rotating cryptographic registration token.
    Used for front-desk kiosk screens and admin QR stations.
    """
    lan_ip = get_lan_ip()
    token_data = generate_registration_token(hostel_id=hostel_id, ttl_seconds=60)
    
    # Base URL defaults to detected LAN IP on port 3000 unless specified
    resolved_base = base_url.rstrip("/") if base_url else f"http://{lan_ip}:3000"
    reg_url = f"{resolved_base}/login?mode=register&token={token_data['token']}&hostel={hostel_id}"

    return OnboardingQrResponse(
        token=token_data["token"],
        hostel_id=hostel_id,
        ttl_seconds=60,
        expires_at=token_data["expires_at"],
        lan_ip=lan_ip,
        default_url=reg_url
    )

@router.post("/onboarding-qr/verify")
async def verify_onboarding_qr(req: VerifyQrRequest):
    """
    Validates a registration token.
    Publicly accessible so student's browser can verify token when opening QR link.
    """
    result = verify_registration_token(req.token, max_age_seconds=360)
    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Invalid or expired registration QR token.")
        )
    return {
        "status": "valid",
        "hostel_id": result.get("hostel_id", "block-b"),
        "remaining_seconds": result.get("remaining_seconds", 300),
        "message": "Token verified. Registration unlocked."
    }

@router.get("/pending-registrations", response_model=List[UserResponse], dependencies=[Depends(require_admin_pin)])
async def get_pending_registrations(db: AsyncSession = Depends(get_db)):
    """
    Returns list of all new student registration requests awaiting operator approval.
    """
    pending = await UserRepository.get_pending_registrations(db)
    return [UserResponse.model_validate(u) for u in pending]

@router.post("/registrations/{user_id}/approve", response_model=UserResponse, dependencies=[Depends(require_admin_pin)])
async def approve_resident_registration(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Approves a resident's registration request, enabling immediate login.
    """
    user = await UserRepository.approve_registration(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student registration request not found."
        )
    return UserResponse.model_validate(user)

@router.post("/registrations/{user_id}/reject", dependencies=[Depends(require_admin_pin)])
async def reject_resident_registration(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Rejects a resident's registration request.
    """
    user = await UserRepository.reject_registration(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student registration request not found."
        )
    return {
        "status": "success",
        "message": f"Registration request for {user.name} (Room {user.room_number}) has been rejected."
    }




