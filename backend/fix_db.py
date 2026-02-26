import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_db():
    async with engine.begin() as conn:
        print("Fixing interview_sessions...")
        try:
            await conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN total_questions INTEGER DEFAULT 0;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN overall_score FLOAT;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN communication_score FLOAT;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN recommendation VARCHAR;"))
        except Exception as e: print(e)
        
        print("Fixing questions...")
        try:
            await conn.execute(text("ALTER TABLE questions ADD COLUMN question_order INTEGER DEFAULT 0;"))
        except Exception as e: print(e)
        
        print("Fixing answer_scores...")
        try:
            await conn.execute(text("ALTER TABLE answer_scores ADD COLUMN technical_score FLOAT;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE answer_scores ADD COLUMN behavior_flag VARCHAR;"))
        except Exception as e: print(e)
        
        print("Fixing interview_memory...")
        try:
            await conn.execute(text("ALTER TABLE interview_memory ADD COLUMN last_behavior_state VARCHAR;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE interview_memory ADD COLUMN token_usage INTEGER DEFAULT 0;"))
        except Exception as e: print(e)

        print("Fixing auth_users for Skills page...")
        try:
            await conn.execute(text("ALTER TABLE auth_users ADD COLUMN skills JSONB;"))
        except Exception as e: print(e)
        try:
            await conn.execute(text("ALTER TABLE auth_users ADD COLUMN resume_url VARCHAR(512);"))
        except Exception as e: print(e)

if __name__ == "__main__":
    asyncio.run(fix_db())
