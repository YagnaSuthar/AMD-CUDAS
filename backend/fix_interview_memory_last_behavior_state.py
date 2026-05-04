#!/usr/bin/env python3
"""Migration script: widen interview_memory.last_behavior_state to TEXT.

Fixes asyncpg.exceptions.StringDataRightTruncationError when the app stores
"behavior||feedback" strings that exceed VARCHAR(50).
"""

import asyncio
from sqlalchemy import text

from app.core.database import engine


async def main() -> None:
    async with engine.begin() as conn:
        # Ensure table exists
        await conn.execute(
            text(
                """
                ALTER TABLE interview_memory
                ALTER COLUMN last_behavior_state TYPE TEXT;
                """
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
