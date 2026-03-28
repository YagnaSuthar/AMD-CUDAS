import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_nullable():
    print("Altering auth_users.hashed_password to allow NULL...")
    async with engine.connect() as conn:
        try:
            await conn.execute(text("ALTER TABLE auth_users ALTER COLUMN hashed_password DROP NOT NULL"))
            await conn.commit()
            print("Successfully allowed NULL for hashed_password.")
        except Exception as e:
            print(f"Error: {e}")
            await conn.rollback()

if __name__ == "__main__":
    asyncio.run(fix_nullable())
