import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_login_migration():
    async with engine.begin() as conn:
        print("Adding must_reset_password column to auth_users...")
        # Check if column exists first to avoid error if already present
        result = await conn.execute(text("""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_name = 'auth_users' AND column_name = 'must_reset_password';
        """))
        if result.scalar() == 0:
            await conn.execute(text("ALTER TABLE auth_users ADD COLUMN must_reset_password BOOLEAN DEFAULT FALSE;"))
            print("Column 'must_reset_password' added successfully.")
        else:
            print("Column 'must_reset_password' already exists.")
            
        print("Ensuring hashed_password is nullable...")
        await conn.execute(text("ALTER TABLE auth_users ALTER COLUMN hashed_password DROP NOT NULL;"))
        print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(fix_login_migration())
