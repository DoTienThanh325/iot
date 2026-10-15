import asyncio
import logging
import httpx
from app.config import settings
from app.services.buffer_batch import buffer_manager
from app.services.websocket_manager import ws_manager
from app.services.alert_router import alert_router

logger = logging.getLogger("backend.ai_client")

class AIClient:
    def __init__(self):
        self.is_running = False

    async def start_sliding_window_worker(self):
        """
        Sliding Window Task: Every 5 seconds, collects the 10-second window
        from RingBuffer for all active devices and sends to AI Service via HTTPX.
        """
        self.is_running = True
        logger.info("AI Sliding Window Client Worker started.")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while self.is_running:
                try:
                    await asyncio.sleep(5.0)
                    active_devices = list(buffer_manager.ring_buffers.keys())
                    
                    for device_id in active_devices:
                        window_data = buffer_manager.get_sliding_window(device_id)
                        if not window_data:
                            continue
                        
                        # Only send if we have meaningful data
                        if len(window_data["vitals"]["spo2"]) < 3 and len(window_data["ecg"]["samples"]) < 200:
                            continue

                        await self._send_to_ai_service(client, window_data)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in AI client sliding window worker: {e}", exc_info=True)

    async def _send_to_ai_service(self, client: httpx.AsyncClient, window_data: dict):
        url = f"{settings.AI_SERVICE_URL}/api/v1/analyze"
        device_id = window_data["device_id"]
        try:
            response = await client.post(url, json=window_data)
            if response.status_code == 200:
                result = response.json()
                logger.info(f"AI Result for {device_id}: Context={result.get('context_status')}, Fall={result.get('fall_status')}, AFib={result.get('afib_detected')}")
                
                # 1. Broadcast AI analysis result to WebSocket
                await ws_manager.broadcast(device_id, {
                    "event_type": "AI_RESULT",
                    "data": result
                })

                # 2. Check for critical triggers to route into Alert Router
                if result.get("context_status") == "RESPIRATORY_RISK":
                    await alert_router.route_alert({
                        "device_id": device_id,
                        "alert_type": "RESPIRATORY_RISK",
                        "severity": "CRITICAL",
                        "message": "Nguy cơ suy hô hấp cấp (SpO2 < 92% khi bất động)!"
                    })
                elif result.get("context_status") == "SENSOR_LOOSE":
                    await alert_router.route_alert({
                        "device_id": device_id,
                        "alert_type": "SENSOR_LOOSE",
                        "severity": "NOISE",
                        "message": "Nhiễu tín hiệu / Lỏng cảm biến SpO2 do chuyển động."
                    })

                if result.get("fall_status") == "FALL_CONFIRMED":
                    await alert_router.route_alert({
                        "device_id": device_id,
                        "alert_type": "FALL_CONFIRMED",
                        "severity": "CRITICAL",
                        "message": "Bệnh nhân ngã / Mất ý thức (Xác nhận đa biến)!"
                    })

                if result.get("afib_detected") or result.get("afib_probability", 0) >= 0.70:
                    await alert_router.route_alert({
                        "device_id": device_id,
                        "alert_type": "AFIB_HIGH_RISK",
                        "severity": "CRITICAL",
                        "message": "Phát hiện bất thường điện tim (Rung nhĩ - AFib) - Khuyến nghị tầm soát nguy cơ đột quỵ!"
                    })
            else:
                logger.warning(f"AI Service responded with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Failed to communicate with AI Service at {url}: {e}")

ai_client = AIClient()
