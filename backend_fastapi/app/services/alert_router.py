import logging
from datetime import datetime
from app.database import db
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("backend.alert_router")

class AlertRouter:
    async def route_alert(self, payload: dict):
        """
        High-priority route: Bypasses queues to push directly to WebSocket (<200ms)
        and persists into the alerts collection in MongoDB.
        """
        device_id = payload.get("device_id")
        alert_type = payload.get("alert_type", "UNKNOWN_ALERT")
        severity = payload.get("severity", "CRITICAL")
        
        ts_val = payload.get("ts")
        if isinstance(ts_val, (int, float)):
            dt = datetime.utcfromtimestamp(ts_val)
        else:
            dt = datetime.utcnow()

        alert_doc = {
            "device_id": device_id,
            "timestamp": dt,
            "alert_type": alert_type,
            "severity": severity,
            "bpm": payload.get("bpm"),
            "max_svm": payload.get("max_svm"),
            "is_acknowledged": False,
            "message": payload.get("message", self._default_message(alert_type))
        }

        # 1. Immediate Broadcast to WebSocket (Zero queue latency)
        ws_event = {
            "event_type": "EMERGENCY_ALERT",
            "data": {
                **alert_doc,
                "timestamp": dt.isoformat()
            }
        }
        await ws_manager.broadcast(device_id, ws_event)
        logger.warning(f"HIGH-PRIORITY ALERT BROADCASTED: {alert_type} for device {device_id}")

        # 2. Persist to MongoDB alerts collection
        try:
            if db.db is not None:
                res = await db.db.alerts.insert_one(alert_doc)
                alert_doc["_id"] = str(res.inserted_id)
        except Exception as e:
            logger.error(f"Failed to persist alert to MongoDB: {e}")

        return alert_doc

    def _default_message(self, alert_type: str) -> str:
        messages = {
            "SOS_PRESSED": "Nút bấm khẩn cấp SOS được kích hoạt!",
            "EDGE_FALL_DETECTED": "Cảnh báo ngã khẩn cấp từ thiết bị đeo (Edge Fall)!",
            "FALL_CONFIRMED": "Bệnh nhân ngã / Mất ý thức (Xác nhận đa biến)!",
            "RESPIRATORY_RISK": "Nguy cơ suy hô hấp cấp (SpO2 < 92% khi bất động)!",
            "AFIB_HIGH_RISK": "Phát hiện bất thường điện tim (Rung nhĩ - AFib) - Khuyến nghị tầm soát nguy cơ đột quỵ!",
            "SENSOR_LOOSE": "Nhiễu tín hiệu / Lỏng cảm biến SpO2 do chuyển động."
        }
        return messages.get(alert_type, f"Cảnh báo hệ thống: {alert_type}")

alert_router = AlertRouter()
