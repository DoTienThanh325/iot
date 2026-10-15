import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

logger = logging.getLogger("backend.database")

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}...")
    db.client = AsyncIOMotorClient(settings.MONGO_URI)
    db.db = db.client[settings.MONGO_DB]
    
    # Initialize Time-Series and Standard Collections
    existing_collections = await db.db.list_collection_names()
    
    ts_configs = [
        {"name": "vitals", "timeField": "timestamp", "metaField": "device_id", "granularity": "seconds"},
        {"name": "ecg", "timeField": "timestamp", "metaField": "device_id", "granularity": "seconds"},
        {"name": "accel", "timeField": "timestamp", "metaField": "device_id", "granularity": "seconds"},
    ]
    
    for ts in ts_configs:
        if ts["name"] not in existing_collections:
            try:
                await db.db.create_collection(
                    ts["name"],
                    timeseries={
                        "timeField": ts["timeField"],
                        "metaField": ts["metaField"],
                        "granularity": ts["granularity"]
                    }
                )
                logger.info(f"Created Time-Series collection: {ts['name']}")
            except Exception as e:
                logger.warning(f"Could not create timeseries collection {ts['name']} (standard collection will be used): {e}")

    # Create indexes for standard collections
    await db.db.alerts.create_index([("device_id", 1), ("timestamp", -1)])
    await db.db.ai_results.create_index([("device_id", 1), ("timestamp", -1)])
    logger.info("MongoDB initialized successfully.")

async def close_mongo_connection():
    if db.client:
        logger.info("Closing MongoDB connection...")
        db.client.close()
