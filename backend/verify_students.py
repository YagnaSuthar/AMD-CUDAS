import asyncio
from app.core.database import async_session_factory
from app.models.auth import AuthUser
from sqlalchemy import update

async def main():
    async with async_session_factory() as db:
        await db.execute(update(AuthUser).where(AuthUser.role == 'STUDENT').values(is_verified=True))
        await db.commit()
        print('Successfully verified all students in the database.')

if __name__ == "__main__":
    asyncio.run(main())
