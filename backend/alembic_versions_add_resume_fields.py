"""
Migration script to add resume processing fields to AuthUser model.
Run this manually to update the database schema.
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy import text
from app.core.database import async_session_factory
from app.models.auth import AuthUser


async def add_resume_fields():
    """Add new columns to auth_users table if they don't exist."""
    
    async with async_session_factory() as db:
        # Check if columns exist and add them if needed
        columns_to_add = [
            ("resume_text", "TEXT"),
            ("resume_hash", "VARCHAR(64) UNIQUE"),
            ("projects", "JSONB"),
            ("project_summary", "TEXT"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists
                result = await db.execute(text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'auth_users' AND column_name = '{col_name}'
                """))
                if not result.scalar():
                    # Add column
                    await db.execute(text(f"""
                        ALTER TABLE auth_users 
                        ADD COLUMN {col_name} {col_type}
                    """))
                    print(f"Added column: {col_name}")
                else:
                    print(f"Column {col_name} already exists")
            except Exception as e:
                print(f"Error checking/adding column {col_name}: {e}")
        
        # Create index on resume_hash for faster lookups
        try:
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_auth_users_resume_hash 
                ON auth_users (resume_hash)
            """))
            print("Created/verified index on resume_hash")
        except Exception as e:
            print(f"Error creating index: {e}")
        
        await db.commit()
        print("Migration completed successfully")


if __name__ == "__main__":
    asyncio.run(add_resume_fields())
