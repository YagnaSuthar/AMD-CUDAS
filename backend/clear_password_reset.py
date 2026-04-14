import asyncio
from app.core.database import async_session_factory
from app.models.auth import AuthUser
from sqlalchemy import update

async def main():
    async with async_session_factory() as db:
        # Prevent force-redirect to password reset for all students
        await db.execute(update(AuthUser).where(AuthUser.role == 'STUDENT').values(must_reset_password=False))
        await db.commit()
        print('Successfully cleared must_reset_password for all students.')

if __name__ == "__main__":
    asyncio.run(main())
