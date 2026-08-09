import logging
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.repositories import BookingRepository, MachineRepository
except ImportError:
    from repositories import BookingRepository, MachineRepository

logger = logging.getLogger("laundry-scheduler")
logger.setLevel(logging.INFO)

# Setup basic logging format if not already done
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

async def check_and_update_overdue_bookings(db: AsyncSession):
    """
    Checks active bookings that have exceeded their estimated end time.
    Sets the corresponding machines to 'idle_full'.
    """
    logger.info("Running overdue bookings check...")
    overdue_bookings = await BookingRepository.get_overdue_bookings(db)
    updated_machines = []

    for booking in overdue_bookings:
        machine = await MachineRepository.update_status(db, booking.machine_id, "idle_full")
        if machine:
            logger.info(
                f"Machine '{machine.name}' (ID: {machine.id}) has finished its cycle "
                f"(ended at {booking.estimated_end_at}). Status updated to 'idle_full'."
            )
            updated_machines.append({
                "machine_id": str(machine.id),
                "name": machine.name,
                "booking_id": str(booking.id),
                "estimated_end_at": booking.estimated_end_at.isoformat()
            })

    if overdue_bookings:
        logger.info(f"Scheduler complete. Updated {len(updated_machines)} machines to 'idle_full'.")
    else:
        logger.info("No overdue bookings found.")

    return updated_machines
