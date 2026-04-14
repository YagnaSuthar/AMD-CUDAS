import asyncio
from app.core.database import async_session_factory
from app.models.auth import AuthUser
from app.core.security import hash_password
from sqlalchemy import update

async def main():
    async with async_session_factory() as db:
        # Hash the targeted password
        hashed_pwd = hash_password('12121212')
        # Update all students with the new hashed password
        await db.execute(update(AuthUser).where(AuthUser.role == 'STUDENT').values(hashed_password=hashed_pwd))
        await db.commit()
        print('Successfully updated password for all students to 12121212.')

if __name__ == "__main__":
    asyncio.run(main())
