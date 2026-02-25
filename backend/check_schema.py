import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_schema():
    async with engine.connect() as conn:
        # Check auth_users columns
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'auth_users'
            ORDER BY column_name;
        """))
        columns = result.fetchall()
        
        # Check if the specific column exists
        result_specific = await conn.execute(text("""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_name = 'auth_users' AND column_name = 'verification_token_expiry';
        """))
        has_column = result_specific.scalar() > 0

        with open("schema_output.txt", "w") as f:
            f.write(f"Verification of 'verification_token_expiry': {'FOUND' if has_column else 'MISSING'}\n\n")
            f.write("Columns in 'auth_users' table:\n")
            for col in columns:
                f.write(f"  - {col[0]} ({col[1]})\n")
        print(f"Schema checked. Column verification_token_expiry: {'FOUND' if has_column else 'MISSING'}")

if __name__ == "__main__":
    asyncio.run(check_schema())
