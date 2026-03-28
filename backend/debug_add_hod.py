import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.auth import AuthUser, AuthUserRole

async def test_add_user():
    async with async_session_factory() as session:
        # Find a principal
        result = await session.execute(select(AuthUser).where(AuthUser.role == "COLLEGE_PRINCIPAL"))
        principal = result.scalars().first()
        
        if not principal:
            print("No principal found to test with.")
            return

        print(f"Testing with principal: {principal.name} ({principal.id})")
        
        new_hod = AuthUser(
            name="Test HOD",
            email=f"test_hod_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password=None,
            role="HOD",
            parent_id=principal.id,
            is_verified=True,
            department="Computer Science",
            must_reset_password=True,
        )
        
        try:
            session.add(new_hod)
            await session.commit()
            print("Successfully added HOD in test.")
        except Exception as e:
            await session.rollback()
            print(f"FAILED to add HOD: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_add_user())
