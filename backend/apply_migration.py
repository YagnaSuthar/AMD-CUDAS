import asyncio
from sqlalchemy import text
from app.core.database import engine

async def apply_migration():
    async with engine.begin() as conn:
        print("Adding 'verification_token_expiry' column to 'auth_users' table...")
        await conn.execute(text("""
            ALTER TABLE auth_users 
            ADD COLUMN IF NOT EXISTS verification_token_expiry TIMESTAMP WITH TIME ZONE;
        """))
        print("Migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
