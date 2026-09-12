from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
import datetime
from sqlalchemy import select

try:
    from app.database import get_db
    from app.schemas import (
        MachineCreate, MachineResponse, BookingResponse, QueueResponse,
        MachineDetailResponse, ClaimRequest, PingRequest, QueueJoinRequest,
        TelemetryHistoryResponse, TelemetryHistoryPoint
    )
    from app.models import TelemetryReading
    from app.repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        SmartPlugRepository, TelemetryRepository, UserRepository
    )
    from app.routers.websocket import ws_manager
except ImportError:
    from ..database import get_db
    from ..schemas import (
        MachineCreate, MachineResponse, BookingResponse, QueueResponse,
        MachineDetailResponse, ClaimRequest, PingRequest, QueueJoinRequest,
        TelemetryHistoryResponse, TelemetryHistoryPoint
    )
    from ..models import TelemetryReading
    from ..repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        SmartPlugRepository, TelemetryRepository, UserRepository
    )
    from ..routers.websocket import ws_manager


router = APIRouter(prefix="/api/machines", tags=["machines"])

@router.get("", response_model=List[MachineDetailResponse])
async def get_machines(db: AsyncSession = Depends(get_db)):
    """
    Get all machines with their active booking and current active queue list.
    Includes anonymized status for student dashboard.
    """
    machines = await MachineRepository.get_all(db)
    response = []
    for machine in machines:
        active_booking = await BookingRepository.get_active_booking(db, machine.id)
        queue = await QueueRepository.get_active_queue(db, machine.id)
        plug = await SmartPlugRepository.get_by_machine_id(db, machine.id)
        
        booking_data = None
        if active_booking:
            booking_data = BookingResponse.model_validate(active_booking)
            
        queue_data = [QueueResponse.model_validate(q) for q in queue]
        
        latest_power = None
        is_online = None
        if plug:
            is_online = plug.is_online
            reading = await TelemetryRepository.get_latest_for_plug(db, plug.id)
            if reading:
                latest_power = reading.power_w
        
        response.append(
            MachineDetailResponse(
                id=machine.id,
                name=machine.name,
                status=machine.status,
                active_booking=booking_data,
                queue=queue_data,
                latest_power_w=latest_power,
                is_plug_online=is_online
            )
        )
    return response


@router.post("", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(req: MachineCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new machine (e.g. Washer 1, Dryer 1).
    """
    machine = await MachineRepository.create(db, name=req.name.strip(), status=req.status or "available")
    await db.commit()
    return MachineResponse.model_validate(machine)


@router.delete("/{id}")
async def delete_machine(id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Deletes a machine and unlinks/cascades its bookings and queue entries.
    """
    deleted = await MachineRepository.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Machine not found")
    await db.commit()
    return {"status": "success", "message": "Machine deleted successfully"}


@router.post("/{id}/claim", response_model=MachineDetailResponse)
async def claim_machine(id: UUID, req: ClaimRequest, db: AsyncSession = Depends(get_db)):
    """
    Claims an available machine.
    Creates an active booking with estimated_end_at = now + 45 mins.
    If the claimant was in the queue (e.g. notified), marks their queue entry as expired.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if machine.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine is currently {machine.status} and cannot be claimed"
        )

    # Business Logic: If there is a notified user in the queue, only they should claim it
    active_queue = await QueueRepository.get_active_queue(db, id)
    notified_users = [q for q in active_queue if q.status == "notified"]
    
    if notified_users:
        # Check if the claimant is the notified user
        if notified_users[0].user_id != req.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This machine is reserved for the next user in the queue"
            )
        # Mark notified user's queue entry as expired since they are claiming it now
        await QueueRepository.update_queue_status(db, notified_users[0].id, "expired")
    else:
        # If the claiming user is in the queue as 'waiting', expire them too
        user_waiting = [q for q in active_queue if q.user_id == req.user_id and q.status == "waiting"]
        if user_waiting:
            await QueueRepository.update_queue_status(db, user_waiting[0].id, "expired")

    # Update machine status to in_use
    await MachineRepository.update_status(db, id, "in_use")
    
    # Create booking
    booking = await BookingRepository.create_booking(db, id, req.user_id, duration_minutes=45)
    await db.commit()
    
    # Reload and return detailed state
    updated_machine = await MachineRepository.get_by_id(db, id)
    updated_queue = await QueueRepository.get_active_queue(db, id)
    
    return MachineDetailResponse(
        id=updated_machine.id,
        name=updated_machine.name,
        status=updated_machine.status,
        active_booking=BookingResponse.model_validate(booking),
        queue=[QueueResponse.model_validate(q) for q in updated_queue]
    )


@router.post("/{id}/clear", response_model=MachineDetailResponse)
async def clear_machine(id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Clears the active booking for a machine and sets status to 'available'.
    If waitlisted users exist, shifts the next waiting user to 'notified'.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Clear active booking if exists
    active_booking = await BookingRepository.get_active_booking(db, id)
    if active_booking:
        await BookingRepository.clear_booking(db, active_booking.id)
        
    # Mark machine available
    await MachineRepository.update_status(db, id, "available")
    
    # If waitlist exists, notify the next user
    next_user = await QueueRepository.get_next_in_queue(db, id)
    if next_user:
        await QueueRepository.update_queue_status(db, next_user.id, "notified")
        
    await db.commit()
    
    # Reload details
    updated_machine = await MachineRepository.get_by_id(db, id)
    updated_booking = await BookingRepository.get_active_booking(db, id)
    updated_queue = await QueueRepository.get_active_queue(db, id)
    
    booking_data = BookingResponse.model_validate(updated_booking) if updated_booking else None
    
    return MachineDetailResponse(
        id=updated_machine.id,
        name=updated_machine.name,
        status=updated_machine.status,
        active_booking=booking_data,
        queue=[QueueResponse.model_validate(q) for q in updated_queue]
    )


@router.post("/{id}/ping")
async def ping_machine_owner(id: UUID, req: PingRequest, db: AsyncSession = Depends(get_db)):
    """
    Allows a student or queued user to trigger targeted alerts:
    - target='occupant': Notifies the machine occupant to collect clothes.
    - target='admin': Alerts hostel admin operator console regarding unattended load.
    - target='both': Dispatches dual notification.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    active_booking = await BookingRepository.get_active_booking(db, id)
    if not active_booking:
        raise HTTPException(
            status_code=400,
            detail="No active booking found on this machine to ping."
        )

    # Lookup resident holding the booking
    owner_user = await UserRepository.get_by_id(db, active_booking.user_id)
    owner_name = owner_user.name if owner_user else "Resident"
    owner_room = owner_user.room_number if owner_user else "Unknown Room"

    target = req.target.lower().strip() if req.target else "occupant"
    notify_occupant = target in ["occupant", "both"]
    notify_admin = target in ["admin", "both"]

    nudge_msg = f"Clothes finished on {machine.name}! Please collect your laundry from the drum."
    admin_alert_msg = f"Hostel Alert: Issue/Overdue reported for {machine.name} (Occupant: {owner_name}, Room {owner_room})."

    import asyncio
    asyncio.create_task(ws_manager.broadcast({
        "type": "nudge_alert",
        "machine_id": str(machine.id),
        "machine_name": machine.name,
        "owner_user_id": str(active_booking.user_id) if notify_occupant else None,
        "owner_room": owner_room,
        "target": target,
        "message": nudge_msg if notify_occupant else admin_alert_msg,
        "admin_message": admin_alert_msg if notify_admin else None,
        "notify_admin": notify_admin
    }))
    
    import logging
    logger = logging.getLogger("laundry-api")
    logger.info(f"User {req.user_id or 'Anonymous'} sent ping ({target}) for {machine.name} (Owner: {owner_name}, Room {owner_room})")
    
    if target == "admin":
        msg = f"Hostel admin alerted regarding {machine.name} (Room {owner_room})."
    elif target == "occupant":
        msg = f"Nudge sent directly to machine occupant ({owner_room}) to collect clothes."
    else:
        msg = f"Alert sent to both resident ({owner_room}) and hostel admin."

    return {
        "status": "success",
        "target": target,
        "message": msg,
        "owner_user_id": str(active_booking.user_id),
        "machine_name": machine.name
    }


@router.post("/{id}/queue/join", response_model=MachineDetailResponse)
async def join_queue(id: UUID, req: QueueJoinRequest, db: AsyncSession = Depends(get_db)):
    """
    User joins the virtual queue for a machine.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if machine.status == "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Machine is available, you can claim it directly instead of queuing"
        )
        
    await QueueRepository.join_queue(db, id, req.user_id)
    await db.commit()
    
    # Reload and return detailed state
    updated_machine = await MachineRepository.get_by_id(db, id)
    active_booking = await BookingRepository.get_active_booking(db, id)
    updated_queue = await QueueRepository.get_active_queue(db, id)
    
    booking_data = BookingResponse.model_validate(active_booking) if active_booking else None
    
    return MachineDetailResponse(
        id=updated_machine.id,
        name=updated_machine.name,
        status=updated_machine.status,
        active_booking=booking_data,
        queue=[QueueResponse.model_validate(q) for q in updated_queue]
    )


@router.post("/{id}/queue/leave", response_model=MachineDetailResponse)
async def leave_queue(id: UUID, req: QueueJoinRequest, db: AsyncSession = Depends(get_db)):
    """
    User leaves the virtual queue for a machine.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    success = await QueueRepository.leave_queue(db, id, req.user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="User was not found in the active queue for this machine"
        )
        
    await db.commit()
    
    # Reload and return detailed state
    updated_machine = await MachineRepository.get_by_id(db, id)
    active_booking = await BookingRepository.get_active_booking(db, id)
    updated_queue = await QueueRepository.get_active_queue(db, id)
    
    booking_data = BookingResponse.model_validate(active_booking) if active_booking else None
    
    return MachineDetailResponse(
        id=updated_machine.id,
        name=updated_machine.name,
        status=updated_machine.status,
        active_booking=booking_data,
        queue=[QueueResponse.model_validate(q) for q in updated_queue]
    )


@router.get("/{id}/power-history", response_model=TelemetryHistoryResponse)
async def get_machine_power_history(
    id: UUID,
    hours: int = 4,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns 4-hour historical power telemetry for this machine's linked smart plug.
    Publicly accessible to residents tapping on machine cards to view cycle power curves.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    plug = await SmartPlugRepository.get_by_machine_id(db, id)
    if not plug:
        return TelemetryHistoryResponse(
            plug_id=machine.id,
            plug_name=machine.name,
            hours=hours,
            peak_power_w=0.0,
            avg_power_w=0.0,
            local_points_count=0,
            cloud_points_count=0,
            series=[]
        )
        
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    result = await db.execute(
        select(TelemetryReading)
        .where(TelemetryReading.plug_id == plug.id)
        .where(TelemetryReading.recorded_at >= cutoff)
        .order_by(TelemetryReading.recorded_at.asc())
    )
    readings = result.scalars().all()
    if not readings:
        fallback_res = await db.execute(
            select(TelemetryReading)
            .where(TelemetryReading.plug_id == plug.id)
            .order_by(TelemetryReading.recorded_at.desc())
            .limit(150)
        )
        readings = list(reversed(fallback_res.scalars().all()))

    powers = [r.power_w for r in readings if r.power_w is not None]
    peak_w = max(powers) if powers else 0.0
    avg_w = sum(powers) / len(powers) if powers else 0.0
    local_count = sum(1 for r in readings if (getattr(r, "source", None) or "local") == "local")
    cloud_count = sum(1 for r in readings if getattr(r, "source", None) == "cloud")

    series = [
        TelemetryHistoryPoint(
            timestamp=(
                (r.recorded_at.replace(tzinfo=datetime.timezone.utc) if r.recorded_at.tzinfo is None else r.recorded_at)
                .isoformat().replace("+00:00", "Z")
            ) if r.recorded_at else "",
            power_w=round(r.power_w or 0.0, 1),
            voltage_v=round(r.voltage_v, 1) if r.voltage_v is not None else None,
            current_ma=round(r.current_ma, 1) if r.current_ma is not None else None,
            source=getattr(r, "source", None) or "local"
        )
        for r in readings
    ]

    return TelemetryHistoryResponse(
        plug_id=plug.id,
        plug_name=f"{machine.name} • {plug.name or 'Smart Plug'}",
        hours=hours,
        peak_power_w=round(peak_w, 1),
        avg_power_w=round(avg_w, 1),
        local_points_count=local_count,
        cloud_points_count=cloud_count,
        series=series
    )

