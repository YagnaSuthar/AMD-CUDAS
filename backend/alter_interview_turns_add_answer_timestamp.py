#!/usr/bin/env python3
"""Migration script: add answer_timestamp + current_turn_id columns.

- Adds interview_turns.answer_timestamp (nullable)
- Adds interview_sessions.current_turn_id (nullable)

Safe to run multiple times.
"""

import asyncio
from sqlalchemy import text

from app.core.database import engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE interview_turns
                ADD COLUMN IF NOT EXISTS answer_timestamp TIMESTAMPTZ NULL;
                """
            )
        )

        # Allow NULL answers so a pending turn can exist before candidate responds.
        # This is safe even if existing rows are non-null.
        await conn.execute(
            text(
                """
                ALTER TABLE interview_turns
                ALTER COLUMN answer DROP NOT NULL;
                """
            )
        )

        await conn.execute(
            text(
                """
                ALTER TABLE interview_sessions
                ADD COLUMN IF NOT EXISTS current_turn_id UUID NULL;
                """
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
