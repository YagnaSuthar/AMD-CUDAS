import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_db():
    # Important: using a single transaction will abort on the first failure
    # and prevent subsequent ALTERs. To make this script idempotent, run each
    # statement with IF NOT EXISTS and in its own transaction.
    statements = [
        ("Fixing interview_sessions...", "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS total_questions INTEGER DEFAULT 0;"),
        ("Fixing interview_sessions...", "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS overall_score FLOAT;"),
        ("Fixing interview_sessions...", "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS communication_score FLOAT;"),
        ("Fixing interview_sessions...", "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS recommendation VARCHAR;"),
        ("Fixing questions...", "ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_order INTEGER DEFAULT 0;"),
        ("Fixing answer_scores...", "ALTER TABLE answer_scores ADD COLUMN IF NOT EXISTS technical_score FLOAT;"),
        ("Fixing answer_scores...", "ALTER TABLE answer_scores ADD COLUMN IF NOT EXISTS behavior_flag VARCHAR;"),
        ("Fixing interview_memory...", "ALTER TABLE interview_memory ADD COLUMN IF NOT EXISTS last_behavior_state VARCHAR;"),
        ("Fixing interview_memory...", "ALTER TABLE interview_memory ADD COLUMN IF NOT EXISTS token_usage INTEGER DEFAULT 0;"),
        ("Fixing auth_users for Skills page...", "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS skills JSONB;"),
        ("Fixing auth_users for Skills page...", "ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS resume_url VARCHAR(512);"),
        ("Fixing interview_pipelines...", "ALTER TABLE interview_pipelines ADD COLUMN IF NOT EXISTS round2_scheduled_at TIMESTAMPTZ;"),
    ]

    for header, sql in statements:
        print(header)
        try:
            async with engine.begin() as conn:
                await conn.execute(text(sql))
        except Exception as e:
            print(e)

if __name__ == "__main__":
    asyncio.run(fix_db())
