import asyncio
from sqlalchemy import text
from app.core.database import engine

async def apply_migration():
    async with engine.begin() as conn:
        print("Updating schema for approvals...")
        await conn.execute(text("ALTER TABLE colleges RENAME COLUMN status TO status_old;"))
        await conn.execute(text("ALTER TABLE colleges ADD COLUMN status VARCHAR(20) DEFAULT 'pending';"))
        await conn.execute(text("UPDATE colleges SET status = status_old;"))
        await conn.execute(text("ALTER TABLE colleges DROP COLUMN status_old;"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending';"))
        print("Migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
