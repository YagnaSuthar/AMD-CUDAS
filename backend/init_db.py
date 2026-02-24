import asyncio
import logging
from app.core.database import engine, Base
from app.models.interview import * # Ensure all models are loaded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # This will create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
