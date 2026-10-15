import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("ai_service.database")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "iot_stroke_db")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    logger.info(f"AI Service connecting to MongoDB at {MONGO_URI}...")
    db.client = AsyncIOMotorClient(MONGO_URI)
    db.db = db.client[MONGO_DB]
    logger.info("AI Service connected to MongoDB.")

async def close_mongo_connection():
    if db.client:
        db.client.close()

async def save_ai_result(result_doc: dict):
    if db.db is not None:
        try:
            res = await db.db.ai_results.insert_one(result_doc)
            result_doc["_id"] = str(res.inserted_id)
            return result_doc
        except Exception as e:
            logger.error(f"Failed to save AI result to MongoDB: {e}")
    return result_doc
