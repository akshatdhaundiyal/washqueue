import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

try:
    from app.database import get_db
    from app.models import User, Queue
    from app.schemas import StudentRegisterRequest, StudentLoginRequest, UserResponse
except ImportError:
    from ..database import get_db
    from ..models import User, Queue
    from ..schemas import StudentRegisterRequest, StudentLoginRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

def hash_password(password: str) -> str:
    """Hashes password with SHA-256 and constant salt."""
    salt = "washqueue_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

@router.post("/register", response_model=UserResponse)
async def register_student(req: StudentRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Registers a new student resident with Name, Room Number, and Password.
    Supports single and double-sharing rooms (multiple roommates sharing the same room number).
    """
    clean_name = req.name.strip()
    clean_room = req.room_number.strip().upper()

    if not clean_name or not clean_room or not req.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, Room Number, and Password are all required."
        )

    hashed = hash_password(req.password)

    # Check if this exact student (same name + room) already exists to update their credentials
    existing_user_query = await db.execute(
        select(User).where(
            User.room_number == clean_room,
            func.lower(User.name) == clean_name.lower()
        )
    )
    existing_user = existing_user_query.scalar_one_or_none()

    if existing_user:
        # Update existing student's password and email/campus affiliation
        existing_user.hashed_password = hashed
        if req.email:
            existing_user.email = req.email.strip()
        if req.university:
            existing_user.university = req.university.strip()
        if req.college:
            existing_user.college = req.college.strip()
        if req.hostel:
            existing_user.hostel = req.hostel.strip()
        await db.commit()
        await db.refresh(existing_user)
        return UserResponse.model_validate(existing_user)

    # Create new student user (allowing roommates in double sharing rooms)
    email_clean = req.email.strip() if req.email else f"{clean_name.lower().replace(' ', '')}.{clean_room.lower().replace(' ', '')}@hostel.internal"
    
    new_user = User(
        name=clean_name,
        room_number=clean_room,
        email=email_clean,
        hashed_password=hashed,
        role="student",
        is_admin=False,
        university=req.university.strip() if req.university else None,
        college=req.college.strip() if req.college else None,
        hostel=req.hostel.strip() if req.hostel else None
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse.model_validate(new_user)

@router.post("/login", response_model=UserResponse)
async def login_student(req: StudentLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticates a resident student by Room Number, Password, and optional Name (for double-sharing rooms).
    """
    clean_room = req.room_number.strip().upper()
    hashed = hash_password(req.password)

    # If student specified their name explicitly (useful in double-sharing rooms)
    if req.name and req.name.strip():
        clean_name = req.name.strip().lower()
        user_query = await db.execute(
            select(User).where(
                User.room_number == clean_room,
                func.lower(User.name) == clean_name
            )
        )
        user = user_query.scalar_one_or_none()
        if not user or user.hashed_password != hashed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials for {req.name.strip()} in Room {clean_room}."
            )
        return UserResponse.model_validate(user)

    # Otherwise query all residents registered to this room number
    users_query = await db.execute(
        select(User).where(User.room_number == clean_room)
    )
    room_residents = users_query.scalars().all()

    if not room_residents:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No residents registered for Room {clean_room}. Please register first."
        )

    # Match by password among room residents
    matching_users = [u for u in room_residents if u.hashed_password == hashed]

    if not matching_users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password for Room " + clean_room + "."
        )

    if len(matching_users) > 1:
        # Ambiguous matching in double sharing room if roommates share identical password
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple residents found in Room " + clean_room + ". Please enter your Name to specify your account."
        )

    return UserResponse.model_validate(matching_users[0])

@router.delete("/profile/{id}")
async def delete_student_profile(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Deletes the resident student profile and clears any active waitlist/queue entries.
    """
    user_query = await db.execute(select(User).where(User.id == id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found."
        )

    if user.is_admin or user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator profiles cannot be self-deleted via student portal."
        )

    # Clean up user's active queue waitlist entries
    await db.execute(delete(Queue).where(Queue.user_id == id))

    await db.delete(user)
    await db.commit()
    return {
        "status": "success",
        "message": f"Profile for {user.name} (Room {user.room_number}) has been permanently deleted."
    }
