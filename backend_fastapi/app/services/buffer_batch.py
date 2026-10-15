import asyncio
import logging
import math
from collections import deque
from datetime import datetime
from typing import Dict, Any, List
from app.database import db

logger = logging.getLogger("backend.buffer_batch")

class BufferBatchManager:
    def __init__(self):
        self.vitals_queue = asyncio.Queue()
        self.ecg_queue = asyncio.Queue()
        self.accel_queue = asyncio.Queue()

        # In-memory sliding ring buffer for last 10 seconds of data per device
        # Key: device_id -> { "vitals": deque(maxlen=20), "ecg": deque(maxlen=1500), "accel": deque(maxlen=100) }
        self.ring_buffers: Dict[str, Dict[str, deque]] = {}
        self.is_running = False

    def _get_device_ring(self, device_id: str) -> Dict[str, deque]:
        if device_id not in self.ring_buffers:
            self.ring_buffers[device_id] = {
                "vitals": deque(maxlen=30),       # ~30s of vitals @ 1Hz
                "ecg": deque(maxlen=1500),        # ~12s of ECG samples @ 125Hz
                "accel": deque(maxlen=100)        # ~30-50s of accel readings
            }
        return self.ring_buffers[device_id]

    async def push_vitals(self, payload: dict):
        device_id = payload.get("device_id")
        ts = payload.get("ts", datetime.utcnow().timestamp())
        dt = datetime.utcfromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow()
        
        # 1. Update in-memory RingBuffer
        ring = self._get_device_ring(device_id)
        ring["vitals"].append({
            "timestamp": ts,
            "bpm": payload.get("bpm"),
            "spo2": payload.get("spo2"),
            "temp": payload.get("temp")
        })

        ax = payload.get("ax", 0.0)
        ay = payload.get("ay", 0.0)
        az = payload.get("az", 1.0)
        svm = math.sqrt(ax**2 + ay**2 + az**2)
        
        ring["accel"].append({
            "timestamp": ts,
            "ax": ax,
            "ay": ay,
            "az": az,
            "svm": svm
        })

        # 2. Push to Queues for Batch Writing into MongoDB Time-Series Collections
        vitals_doc = {
            "device_id": device_id,
            "timestamp": dt,
            "bpm": payload.get("bpm"),
            "spo2": payload.get("spo2"),
            "temp": payload.get("temp")
        }
        await self.vitals_queue.put(vitals_doc)

        accel_doc = {
            "device_id": device_id,
            "timestamp": dt,
            "ax": ax,
            "ay": ay,
            "az": az,
            "svm": svm
        }
        await self.accel_queue.put(accel_doc)

    async def push_ecg(self, payload: dict):
        device_id = payload.get("device_id")
        ts = payload.get("ts", datetime.utcnow().timestamp())
        dt = datetime.utcfromtimestamp(ts) if isinstance(ts, (int, float)) else datetime.utcnow()
        fs = payload.get("fs", 125)
        samples = payload.get("samples", [])

        ring = self._get_device_ring(device_id)
        ring["ecg"].extend(samples)

        ecg_doc = {
            "device_id": device_id,
            "timestamp": dt,
            "fs": fs,
            "samples": samples
        }
        await self.ecg_queue.put(ecg_doc)

    def get_sliding_window(self, device_id: str) -> Dict[str, Any]:
        """Fetches up to last 10 seconds of data for AI analysis"""
        if device_id not in self.ring_buffers:
            return None
        ring = self.ring_buffers[device_id]
        
        vitals_list = list(ring["vitals"])[-10:]
        accel_list = list(ring["accel"])[-10:]
        ecg_samples = list(ring["ecg"])[-1250:]  # 10s @ 125Hz = 1250 samples

        return {
            "device_id": device_id,
            "timestamp": datetime.utcnow().timestamp(),
            "vitals": {
                "bpm": [v["bpm"] for v in vitals_list if v.get("bpm") is not None],
                "spo2": [v["spo2"] for v in vitals_list if v.get("spo2") is not None],
                "temp": [v["temp"] for v in vitals_list if v.get("temp") is not None]
            },
            "accel": {
                "ax": [a["ax"] for a in accel_list],
                "ay": [a["ay"] for a in accel_list],
                "az": [a["az"] for a in accel_list],
                "svm": [a["svm"] for a in accel_list]
            },
            "ecg": {
                "samples": ecg_samples,
                "fs": 125
            }
        }

    async def start_batch_worker(self):
        """Worker flushes queues every 3 seconds or when queue contains >= 50 items"""
        self.is_running = True
        logger.info("Batch DB Worker started.")
        while self.is_running:
            try:
                await asyncio.sleep(3.0)
                await self._flush_queue(self.vitals_queue, "vitals")
                await self._flush_queue(self.accel_queue, "accel")
                await self._flush_queue(self.ecg_queue, "ecg")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch worker: {e}", exc_info=True)

    async def _flush_queue(self, queue: asyncio.Queue, collection_name: str, max_batch: int = 100):
        items = []
        while not queue.empty() and len(items) < max_batch:
            try:
                item = queue.get_nowait()
                items.append(item)
                queue.task_done()
            except asyncio.QueueEmpty:
                break

        if items and db.db is not None:
            try:
                await db.db[collection_name].insert_many(items, ordered=False)
                logger.debug(f"Flushed {len(items)} items to collection '{collection_name}'")
            except Exception as e:
                logger.error(f"Failed to batch insert into {collection_name}: {e}")

buffer_manager = BufferBatchManager()
