import asyncio
from sqlalchemy import text
from app.core.database import engine

async def apply_goal_migration():
    async with engine.begin() as conn:
        print("Adding goal field to auth_users table...")
        await conn.execute(text("ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS goal TEXT;"))
        print("Goal field migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_goal_migration())
