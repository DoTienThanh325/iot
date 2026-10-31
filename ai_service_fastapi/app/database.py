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

async def connect_to_mongo(config=None):
    uri = config.mongo_uri if config else MONGO_URI
    name = config.mongo_db if config else MONGO_DB
    timeout = config.mongo_timeout_ms if config else 3000
    logger.info("Creating MongoDB client (credentials omitted).")
    db.client = AsyncIOMotorClient(
        uri, serverSelectionTimeoutMS=timeout, connectTimeoutMS=timeout,
        socketTimeoutMS=timeout, tz_aware=True,
    )
    db.db = db.client[name]

async def close_mongo_connection():
    if db.client:
        db.client.close()
    db.client = None
    db.db = None

async def save_ai_result(result_doc: dict):
    if db.db is not None:
        try:
            res = await db.db.ai_results.insert_one(result_doc)
            result_doc["_id"] = str(res.inserted_id)
            return result_doc
        except Exception as e:
            logger.error("Failed to save legacy AI result (%s)", type(e).__name__)
    return result_doc
