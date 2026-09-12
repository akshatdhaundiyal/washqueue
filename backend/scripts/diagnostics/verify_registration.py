import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend root is in sys.path (three levels up from backend/scripts/diagnostics/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from app.database import Base
from app.models import User
from app.schemas import StudentRegisterRequest, StudentLoginRequest
from app.routers.auth import register_student, login_student, delete_student_profile

async def test_registration_flow():
    print("Testing Student Registration with University, College, and Hostel...")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # 1. Register student with campus details
        req = StudentRegisterRequest(
            name="Rahul Sharma",
            room_number="B-304",
            password="securePassword123",
            email="rahul@nit.internal",
            university="National Institute of Technology",
            college="Faculty of Engineering & Technology",
            hostel="Mega Hostel Block 1"
        )
        registered = await register_student(req, db)
        print(f"[OK] Registered Student: {registered.name}")
        print(f"     University: {registered.university}")
        print(f"     College: {registered.college}")
        print(f"     Hostel: {registered.hostel}")
        print(f"     Room: {registered.room_number}")

        assert registered.name == "Rahul Sharma"
        assert registered.room_number == "B-304"
        assert registered.university == "National Institute of Technology"
        assert registered.college == "Faculty of Engineering & Technology"
        assert registered.hostel == "Mega Hostel Block 1"

        # 2. Login as the student and verify credentials
        login_req = StudentLoginRequest(
            room_number="B-304",
            password="securePassword123",
            name="Rahul Sharma"
        )
        logged_in = await login_student(login_req, db)
        print(f"[OK] Logged in successfully: {logged_in.name} in Room {logged_in.room_number}")
        assert logged_in.university == "National Institute of Technology"
        assert logged_in.hostel == "Mega Hostel Block 1"

        # 3. Update existing user's campus details
        update_req = StudentRegisterRequest(
            name="Rahul Sharma",
            room_number="B-304",
            password="newPassword456",
            email="rahul_new@nit.internal",
            university="National Institute of Technology",
            college="Faculty of Engineering & Technology",
            hostel="Mega Hostel Block 2"
        )
        updated = await register_student(update_req, db)
        print(f"[OK] Re-registration/update successful. New Hostel: {updated.hostel}")
        assert updated.hostel == "Mega Hostel Block 2"

        # 4. Self-delete student profile
        del_resp = await delete_student_profile(updated.id, db)
        print(f"[OK] Self-delete profile response: {del_resp['message']}")
        assert del_resp["status"] == "success"

        # Verify user is gone from db
        deleted_user = await db.get(User, updated.id)
        assert deleted_user is None
        print("[OK] Confirmed user completely purged from database.")

    print("\nAll Registration, Campus, and Self-Deletion tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_registration_flow())
