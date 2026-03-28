"""
One-time migration: Fix interview FK constraints to reference auth_users instead of users.
Also cleans up orphaned rows whose student_id doesn't exist in auth_users.
Run:  python fix_interview_fk.py
"""
import asyncio, asyncpg, os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
# asyncpg needs postgresql:// not postgresql+asyncpg://
DSN = DATABASE_URL.replace("+asyncpg", "")


async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # ── interview_sessions ───────────────────────────────────────
        # Drop old FK
        await conn.execute("""
            ALTER TABLE interview_sessions
            DROP CONSTRAINT IF EXISTS interview_sessions_student_id_fkey;
        """)
        # Delete orphaned rows whose student_id is not in auth_users
        deleted = await conn.execute("""
            DELETE FROM interview_sessions
            WHERE student_id NOT IN (SELECT id FROM auth_users);
        """)
        print(f"[CLEANUP] interview_sessions orphans removed: {deleted}")
        # Add new FK
        await conn.execute("""
            ALTER TABLE interview_sessions
            ADD CONSTRAINT interview_sessions_student_id_fkey
            FOREIGN KEY (student_id) REFERENCES auth_users(id) ON DELETE CASCADE;
        """)
        print("[OK] interview_sessions.student_id -> auth_users.id")

        # ── student_profiles ─────────────────────────────────────────
        await conn.execute("""
            ALTER TABLE student_profiles
            DROP CONSTRAINT IF EXISTS student_profiles_student_id_fkey;
        """)
        deleted2 = await conn.execute("""
            DELETE FROM student_profiles
            WHERE student_id NOT IN (SELECT id FROM auth_users);
        """)
        print(f"[CLEANUP] student_profiles orphans removed: {deleted2}")
        await conn.execute("""
            ALTER TABLE student_profiles
            ADD CONSTRAINT student_profiles_student_id_fkey
            FOREIGN KEY (student_id) REFERENCES auth_users(id) ON DELETE CASCADE;
        """)
        print("[OK] student_profiles.student_id -> auth_users.id")

    finally:
        await conn.close()

asyncio.run(main())
print("Done — FK constraints updated.")
