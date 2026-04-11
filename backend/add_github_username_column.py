#!/usr/bin/env python3
"""
Migration script to add missing github_username column to auth_users table.
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine

async def add_github_username_column():
    """Add github_username column to auth_users table if it doesn't exist."""
    
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'auth_users' AND column_name = 'github_username'
            """))
            
            if not result.fetchone():
                print("Adding github_username column to auth_users table...")
                await conn.execute(text("""
                    ALTER TABLE auth_users 
                    ADD COLUMN github_username VARCHAR(100)
                """))
                print("✅ github_username column added successfully!")
            else:
                print("✅ github_username column already exists!")
                
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(add_github_username_column())
