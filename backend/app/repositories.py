import datetime
from uuid import UUID
from typing import List, Optional
from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.models import Machine, Booking, Queue, SmartPlug, TelemetryReading, User
except ImportError:
    from .models import Machine, Booking, Queue, SmartPlug, TelemetryReading, User

class MachineRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[Machine]:
        result = await db.execute(
            select(Machine).order_by(Machine.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, machine_id: UUID) -> Optional[Machine]:
        result = await db.execute(
            select(Machine).where(Machine.id == machine_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(db: AsyncSession, machine_id: UUID, status: str) -> Optional[Machine]:
        await db.execute(
            update(Machine)
            .where(Machine.id == machine_id)
            .values(status=status)
        )
        return await MachineRepository.get_by_id(db, machine_id)

    @staticmethod
    async def create(db: AsyncSession, name: str, status: str = "available") -> Machine:
        machine = Machine(name=name, status=status)
        db.add(machine)
        await db.flush()
        return machine

    @staticmethod
    async def delete(db: AsyncSession, machine_id: UUID) -> bool:
        machine = await MachineRepository.get_by_id(db, machine_id)
        if not machine:
            return False
        await db.delete(machine)
        await db.flush()
        return True


class BookingRepository:
    @staticmethod
    async def get_active_booking(db: AsyncSession, machine_id: UUID) -> Optional[Booking]:
        result = await db.execute(
            select(Booking)
            .where(
                and_(
                    Booking.machine_id == machine_id,
                    Booking.cleared_at.is_(None)
                )
            )
            .order_by(Booking.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_booking(db: AsyncSession, machine_id: UUID, user_id: UUID, duration_minutes: int = 45) -> Booking:
        started_at = datetime.datetime.now(datetime.timezone.utc)
        estimated_end_at = started_at + datetime.timedelta(minutes=duration_minutes)
        
        booking = Booking(
            machine_id=machine_id,
            user_id=user_id,
            started_at=started_at,
            estimated_end_at=estimated_end_at
        )
        db.add(booking)
        await db.flush()
        return booking

    @staticmethod
    async def clear_booking(db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
        cleared_at = datetime.datetime.now(datetime.timezone.utc)
        await db.execute(
            update(Booking)
            .where(Booking.id == booking_id)
            .values(cleared_at=cleared_at)
        )
        result = await db.execute(
            select(Booking).where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_overdue_bookings(db: AsyncSession) -> List[Booking]:
        now = datetime.datetime.now(datetime.timezone.utc)
        result = await db.execute(
            select(Booking)
            .join(Machine, Booking.machine_id == Machine.id)
            .where(
                and_(
                    Booking.cleared_at.is_(None),
                    Booking.estimated_end_at <= now,
                    Machine.status == "in_use"
                )
            )
        )
        return list(result.scalars().all())


class QueueRepository:
    @staticmethod
    async def get_active_queue(db: AsyncSession, machine_id: UUID) -> List[Queue]:
        result = await db.execute(
            select(Queue)
            .where(
                and_(
                    Queue.machine_id == machine_id,
                    Queue.status.in_(["waiting", "notified"])
                )
            )
            .order_by(Queue.position.asc(), Queue.joined_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_next_in_queue(db: AsyncSession, machine_id: UUID) -> Optional[Queue]:
        result = await db.execute(
            select(Queue)
            .where(
                and_(
                    Queue.machine_id == machine_id,
                    Queue.status == "waiting"
                )
            )
            .order_by(Queue.position.asc(), Queue.joined_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def join_queue(db: AsyncSession, machine_id: UUID, user_id: UUID) -> Queue:
        existing_result = await db.execute(
            select(Queue)
            .where(
                and_(
                    Queue.machine_id == machine_id,
                    Queue.user_id == user_id,
                    Queue.status.in_(["waiting", "notified"])
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing

        pos_result = await db.execute(
            select(func.max(Queue.position))
            .where(
                and_(
                    Queue.machine_id == machine_id,
                    Queue.status.in_(["waiting", "notified"])
                )
            )
        )
        max_pos = pos_result.scalar()
        next_position = (max_pos or 0) + 1

        queue_entry = Queue(
            machine_id=machine_id,
            user_id=user_id,
            position=next_position,
            status="waiting",
            joined_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(queue_entry)
        await db.flush()
        return queue_entry

    @staticmethod
    async def update_queue_status(db: AsyncSession, queue_id: UUID, status: str) -> Optional[Queue]:
        await db.execute(
            update(Queue)
            .where(Queue.id == queue_id)
            .values(status=status)
        )
        result = await db.execute(
            select(Queue).where(Queue.id == queue_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def leave_queue(db: AsyncSession, machine_id: UUID, user_id: UUID) -> bool:
        result = await db.execute(
            select(Queue)
            .where(
                and_(
                    Queue.machine_id == machine_id,
                    Queue.user_id == user_id,
                    Queue.status.in_(["waiting", "notified"])
                )
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return False

        entry.status = "expired"
        await db.flush()
        
        active_entries = await QueueRepository.get_active_queue(db, machine_id)
        for index, active_entry in enumerate(active_entries):
            active_entry.position = index + 1
        
        await db.flush()
        return True


class UserRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession) -> List[User]:
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_pending_registrations(db: AsyncSession) -> List[User]:
        result = await db.execute(
            select(User)
            .where(User.status == "pending")
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def approve_registration(db: AsyncSession, user_id: UUID) -> Optional[User]:
        user = await UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        user.status = "approved"
        user.approved_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def reject_registration(db: AsyncSession, user_id: UUID) -> Optional[User]:
        user = await UserRepository.get_by_id(db, user_id)
        if not user:
            return None
        user.status = "rejected"
        await db.commit()
        await db.refresh(user)
        return user


class SmartPlugRepository:
    @staticmethod
    async def get_all(db: AsyncSession) -> List[SmartPlug]:
        result = await db.execute(select(SmartPlug).order_by(SmartPlug.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, plug_id: UUID) -> Optional[SmartPlug]:
        result = await db.execute(select(SmartPlug).where(SmartPlug.id == plug_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_mac(db: AsyncSession, mac_address: str) -> Optional[SmartPlug]:
        normalized = mac_address.lower().replace("-", ":")
        result = await db.execute(select(SmartPlug).where(func.lower(SmartPlug.mac_address) == normalized))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_device_id(db: AsyncSession, device_id: str) -> Optional[SmartPlug]:
        result = await db.execute(select(SmartPlug).where(SmartPlug.device_id == device_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_machine_id(db: AsyncSession, machine_id: UUID) -> Optional[SmartPlug]:
        result = await db.execute(select(SmartPlug).where(SmartPlug.machine_id == machine_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> SmartPlug:
        plug = SmartPlug(**kwargs)
        db.add(plug)
        await db.flush()
        return plug

    @staticmethod
    async def update(db: AsyncSession, plug_id: UUID, **kwargs) -> Optional[SmartPlug]:
        # Filter out None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if update_data:
            await db.execute(
                update(SmartPlug)
                .where(SmartPlug.id == plug_id)
                .values(**update_data)
            )
        return await SmartPlugRepository.get_by_id(db, plug_id)

    @staticmethod
    async def delete(db: AsyncSession, plug_id: UUID) -> bool:
        plug = await SmartPlugRepository.get_by_id(db, plug_id)
        if plug:
            await db.delete(plug)
            await db.flush()
            return True
        return False


class TelemetryRepository:
    @staticmethod
    async def get_latest_for_plug(db: AsyncSession, plug_id: UUID) -> Optional[TelemetryReading]:
        result = await db.execute(
            select(TelemetryReading)
            .where(TelemetryReading.plug_id == plug_id)
            .order_by(desc(TelemetryReading.recorded_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_history_for_plug(db: AsyncSession, plug_id: UUID, limit: int = 50) -> List[TelemetryReading]:
        result = await db.execute(
            select(TelemetryReading)
            .where(TelemetryReading.plug_id == plug_id)
            .order_by(desc(TelemetryReading.recorded_at))
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
