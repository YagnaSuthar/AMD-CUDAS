import asyncio
from sqlalchemy import text
from app.core.database import engine

async def apply_migration():
    async with engine.begin() as conn:
        print("Adding github_username to auth_users...")
        await conn.execute(text("ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS github_username VARCHAR(100);"))
        
        print("Adding project_structure to projects...")
        await conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS project_structure JSONB;"))
        
        print("Verification fields migration applied successfully.")

if __name__ == "__main__":
    asyncio.run(apply_migration())
