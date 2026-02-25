"""Check what test data exists in the database."""
import asyncio
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.models.interview import User, StudentProfile, InterviewSession

async def check_db():
    async with async_session_factory() as s:
        # Count records
        users = (await s.execute(select(func.count()).select_from(User))).scalar()
        profiles = (await s.execute(select(func.count()).select_from(StudentProfile))).scalar()
        sessions = (await s.execute(select(func.count()).select_from(InterviewSession))).scalar()
        
        print(f"=== Database Summary ===")
        print(f"  Users:             {users}")
        print(f"  StudentProfiles:   {profiles}")
        print(f"  InterviewSessions: {sessions}")
        print()
        
        # Show user details
        rows = (await s.execute(select(User))).scalars().all()
        if rows:
            print("--- Users ---")
            for u in rows:
                print(f"  id={u.id}  email={u.email}  role={u.role}")
            print()
        
        # Show profile details
        rows2 = (await s.execute(select(StudentProfile))).scalars().all()
        if rows2:
            print("--- Student Profiles ---")
            for p in rows2:
                print(f"  student_id={p.student_id}  exp_years={p.experience_years}")
            print()
        
        # Show session details
        rows3 = (await s.execute(select(InterviewSession))).scalars().all()
        if rows3:
            print("--- Interview Sessions ---")
            for sess in rows3:
                print(f"  id={sess.id}  student_id={sess.student_id}  status={sess.status}")

if __name__ == "__main__":
    asyncio.run(check_db())
