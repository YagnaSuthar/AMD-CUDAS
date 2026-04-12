import asyncio
from sqlalchemy import text
from app.core.database import engine

async def apply_migration():
    async with engine.begin() as conn:
        print("Updating schema for timetables...")
        # Add status column
        await conn.execute(text("ALTER TABLE timetables ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';"))
        # Add published_at column
        await conn.execute(text("ALTER TABLE timetables ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();"))
        print("Migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
