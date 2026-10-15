import asyncio
import json
import logging
import aiomqtt
from app.config import settings
from app.services.alert_router import alert_router
from app.services.buffer_batch import buffer_manager
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("backend.mqtt_consumer")

class MQTTConsumer:
    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info(f"Connecting to MQTT Broker at {settings.MQTT_HOST}:{settings.MQTT_PORT}...")
        
        while self.is_running:
            try:
                async with aiomqtt.Client(hostname=settings.MQTT_HOST, port=settings.MQTT_PORT) as client:
                    logger.info("Connected to Mosquitto MQTT Broker!")
                    await client.subscribe("device/+/vitals")
                    await client.subscribe("device/+/ecg")
                    await client.subscribe("device/+/alert")
                    logger.info("Subscribed to device/+/vitals, device/+/ecg, and device/+/alert")

                    async for message in client.messages:
                        await self._process_message(message)
            except aiomqtt.MqttError as error:
                logger.warning(f"MQTT connection lost: {error}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                logger.info("MQTT Consumer task cancelled.")
                break
            except Exception as e:
                logger.error(f"Unexpected MQTT consumer error: {e}", exc_info=True)
                await asyncio.sleep(3)

    async def _process_message(self, message):
        try:
            topic = str(message.topic)
            payload_str = message.payload.decode("utf-8")
            data = json.loads(payload_str)
            
            parts = topic.split("/")
            if len(parts) < 3:
                return
            device_id = parts[1]
            channel = parts[2]
            
            if "device_id" not in data:
                data["device_id"] = device_id

            if channel == "alert":
                # 1. High-priority Alert routing
                await alert_router.route_alert(data)
                
            elif channel == "vitals":
                # 2. Push to buffer & batch write
                await buffer_manager.push_vitals(data)
                # 3. Stream to WebSocket
                await ws_manager.broadcast(device_id, {
                    "event_type": "VITALS",
                    "data": data
                })
                
            elif channel == "ecg":
                # 4. Push ECG to buffer & batch
                await buffer_manager.push_ecg(data)
                # 5. Stream ECG to WebSocket
                await ws_manager.broadcast(device_id, {
                    "event_type": "ECG",
                    "data": data
                })
        except json.JSONDecodeError:
            logger.error("Failed to decode MQTT JSON payload")
        except Exception as e:
            logger.error(f"Error handling MQTT message on {message.topic}: {e}", exc_info=True)

mqtt_consumer = MQTTConsumer()
