from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

try:
    from app.database import get_db
    from app.schemas import (
        MachineResponse, BookingResponse, QueueResponse,
        MachineDetailResponse, ClaimRequest, PingRequest, QueueJoinRequest
    )
    from app.repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        SmartPlugRepository, TelemetryRepository
    )
except ImportError:
    from database import get_db
    from schemas import (
        MachineResponse, BookingResponse, QueueResponse,
        MachineDetailResponse, ClaimRequest, PingRequest, QueueJoinRequest
    )
    from repositories import (
        MachineRepository, BookingRepository, QueueRepository,
        SmartPlugRepository, TelemetryRepository
    )


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
    Allows a queued user to trigger an anonymous alert to the user holding the active booking.
    Only allowed when status is 'idle_full'.
    Returns the target owner's user_id so client can broadcast the notification.
    """
    machine = await MachineRepository.get_by_id(db, id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
        
    if machine.status != "idle_full":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pinging owner is only allowed when machine is idle_full"
        )
        
    active_booking = await BookingRepository.get_active_booking(db, id)
    if not active_booking:
        raise HTTPException(
            status_code=400,
            detail="No active booking found for this machine to ping"
        )
        
    # Log the ping (anonymous alert)
    import logging
    logger = logging.getLogger("laundry-api")
    logger.info(f"User {req.user_id} sent a ping alert to owner {active_booking.user_id} of Machine {machine.name}")
    
    return {
        "status": "success",
        "message": f"Owner of Machine '{machine.name}' has been pinged.",
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
