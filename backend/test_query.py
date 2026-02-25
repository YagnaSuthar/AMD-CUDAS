import asyncio
from sqlalchemy import select
from app.core.database import engine, async_session_factory
from app.models.auth import AuthUser, College

async def test_query():
    print("Testing SQL query that was previously failing...")
    async with async_session_factory() as session:
        try:
            stmt = select(College, AuthUser).join(AuthUser, College.principal_id == AuthUser.id)
            result = await session.execute(stmt)
            data = result.all()
            print(f"Query successful! Found {len(data)} colleges.")
        except Exception as e:
            print(f"Query failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_query())
