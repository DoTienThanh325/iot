import json
import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("backend.websocket")

class ConnectionManager:
    def __init__(self):
        # Maps device_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        if device_id not in self.active_connections:
            self.active_connections[device_id] = []
        self.active_connections[device_id].append(websocket)
        logger.info(f"WebSocket client connected for device: {device_id}. Total: {len(self.active_connections[device_id])}")

    def disconnect(self, websocket: WebSocket, device_id: str):
        if device_id in self.active_connections:
            if websocket in self.active_connections[device_id]:
                self.active_connections[device_id].remove(websocket)
            if not self.active_connections[device_id]:
                del self.active_connections[device_id]
        logger.info(f"WebSocket client disconnected for device: {device_id}")

    async def broadcast(self, device_id: str, message: dict):
        if device_id in self.active_connections:
            payload = json.dumps(message)
            disconnected = []
            for connection in self.active_connections[device_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Error sending message to websocket client: {e}")
                    disconnected.append(connection)
            for dead in disconnected:
                self.disconnect(dead, device_id)

ws_manager = ConnectionManager()
