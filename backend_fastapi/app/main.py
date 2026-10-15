import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.services.websocket_manager import ws_manager
from app.services.buffer_batch import buffer_manager
from app.services.mqtt_consumer import mqtt_consumer
from app.services.ai_client import ai_client
from app.routers import vitals, alerts, history, demo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

background_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Connect MongoDB
    await connect_to_mongo()

    # 2. Start Background Services
    batch_task = asyncio.create_task(buffer_manager.start_batch_worker())
    mqtt_task = asyncio.create_task(mqtt_consumer.start())
    ai_task = asyncio.create_task(ai_client.start_sliding_window_worker())
    background_tasks.extend([batch_task, mqtt_task, ai_task])
    logger.info("All background tasks (MQTT, Batch DB Worker, AI Sliding Window) initialized.")

    yield

    # Shutdown
    logger.info("Shutting down background tasks...")
    buffer_manager.is_running = False
    mqtt_consumer.is_running = False
    ai_client.is_running = False

    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

    await close_mongo_connection()
    logger.info("Backend shutdown complete.")

app = FastAPI(
    title="IoT Stroke Monitoring Processing Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(vitals.router)
app.include_router(alerts.router)
app.include_router(history.router)
app.include_router(demo.router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "backend_fastapi",
        "mqtt_connected": mqtt_consumer.is_running,
        "batch_worker_running": buffer_manager.is_running,
        "ai_worker_running": ai_client.is_running
    }

@app.websocket("/ws/realtime/{device_id}")
async def websocket_realtime_endpoint(websocket: WebSocket, device_id: str):
    await ws_manager.connect(websocket, device_id)
    try:
        while True:
            # Keep-alive or client ping
            data = await websocket.receive_text()
            logger.debug(f"Received from WS client {device_id}: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, device_id)
    except Exception as e:
        logger.warning(f"WebSocket error for {device_id}: {e}")
        ws_manager.disconnect(websocket, device_id)
