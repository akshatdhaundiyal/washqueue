import asyncio
import datetime
import uuid

# Native module imports within the backend workspace
from app.database import Base
from app.models import Machine, Booking, Queue
from app.repositories import MachineRepository, BookingRepository, QueueRepository
from app.scheduler import check_and_update_overdue_bookings

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

async def run_test():
    print("Initializing test in-memory database...")
    # Use SQLite async
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as db:
        print("\n--- Test 1: Seed Machines ---")
        m1 = Machine(name="Washer 1", status="available")
        m2 = Machine(name="Dryer 1", status="available")
        db.add_all([m1, m2])
        await db.commit()
        
        machines = await MachineRepository.get_all(db)
        assert len(machines) == 2
        m1_id = machines[0].id
        print(f"Seeded 2 machines. Washer 1 ID: {m1_id}")
        
        print("\n--- Test 2: Claim Machine (in_use) ---")
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        
        # Claim
        machine = await MachineRepository.update_status(db, m1_id, "in_use")
        booking = await BookingRepository.create_booking(db, m1_id, user_a, duration_minutes=45)
        await db.commit()
        print(f"Machine status: {machine.status}")
        print(f"Booking registered for user: {booking.user_id}")
        print(f"Estimated End At: {booking.estimated_end_at}")
        
        assert machine.status == "in_use"
        assert booking.machine_id == m1_id
        
        print("\n--- Test 3: Join Waitlist Queue ---")
        q_entry = await QueueRepository.join_queue(db, m1_id, user_b)
        await db.commit()
        print(f"Queue entry created. Position: {q_entry.position}, Status: {q_entry.status}")
        
        assert q_entry.status == "waiting"
        assert q_entry.position == 1
        
        print("\n--- Test 4: Scheduler Overdue check ---")
        # Backdate the booking's end time to make it overdue
        booking.estimated_end_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        db.add(booking)
        await db.commit()
        
        print("Mocked end time as overdue. Running scheduler tick...")
        updated = await check_and_update_overdue_bookings(db)
        await db.commit()
        print(f"Scheduler updated list: {updated}")
        
        # Verify machine status transitioned to idle_full
        machine_status = (await MachineRepository.get_by_id(db, m1_id)).status
        print(f"Machine current status: {machine_status}")
        assert machine_status == "idle_full"
        assert len(updated) == 1
        
        print("\n--- Test 5: Clear Machine & Notify Queue ---")
        # Clear the active booking
        active_booking = await BookingRepository.get_active_booking(db, m1_id)
        if active_booking:
            await BookingRepository.clear_booking(db, active_booking.id)
            
        # Mark machine available
        await MachineRepository.update_status(db, m1_id, "available")
        
        # Check queue
        next_user = await QueueRepository.get_next_in_queue(db, m1_id)
        if next_user:
            await QueueRepository.update_queue_status(db, next_user.id, "notified")
            
        await db.commit()
        
        # Fetch updated details
        cleared_machine = await MachineRepository.get_by_id(db, m1_id)
        active_queue = await QueueRepository.get_active_queue(db, m1_id)
        
        print(f"Cleared machine status: {cleared_machine.status}")
        print(f"Queue front status: {active_queue[0].status} for user {active_queue[0].user_id}")
        
        assert cleared_machine.status == "available"
        assert active_queue[0].status == "notified"
        
        print("\n--- Test 6: Notified User Claims ---")
        # Try claiming as the notified user
        await MachineRepository.update_status(db, m1_id, "in_use")
        new_booking = await BookingRepository.create_booking(db, m1_id, user_b, duration_minutes=45)
        await QueueRepository.update_queue_status(db, active_queue[0].id, "expired")
        await db.commit()
        
        post_claim_queue = await QueueRepository.get_active_queue(db, m1_id)
        print(f"Post-claim active queue length: {len(post_claim_queue)}")
        assert len(post_claim_queue) == 0
        
        print("\nAll backend logic assertions passed successfully!")

if __name__ == "__main__":
    asyncio.run(run_test())
