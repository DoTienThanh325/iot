import logging
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.database import connect_to_mongo, close_mongo_connection, save_ai_result
from app.modules.context_aware import evaluate_context
from app.modules.fall_detect import evaluate_fall
from app.modules.ecg_analysis import extract_hrv_features
from app.modules.afib_detect import afib_detector
from app.config import Settings
from app.database import db
from app.algorithms.v2.afib import AFibPredictor
from app.api.v2 import router as v2_router
from app.api.body_limit import BodyLimitMiddleware
from app.services.state_store import MemoryStore, MongoStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_service.main")

class AnalyzePayload(BaseModel):
    device_id: str
    timestamp: Optional[float] = None
    vitals: Dict[str, Any] = Field(default_factory=dict)
    accel: Dict[str, Any] = Field(default_factory=dict)
    ecg: Dict[str, Any] = Field(default_factory=dict)

@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Settings.from_env()
    try:
        await connect_to_mongo(config)
        predictor = AFibPredictor(config)
        predictor.load()
        store = MemoryStore(config) if config.storage_mode == "memory" else MongoStore(
            db.client, db.db, config.mongo_timeout_ms)
        try:
            await store.initialize()
        except Exception as exc:
            logger.warning("V2 storage initialization failed (%s)", type(exc).__name__)
        app.state.runtime = {"config": config, "predictor": predictor, "store": store,
                             "semaphore": asyncio.Semaphore(config.max_concurrency)}
        if config.storage_mode == "memory":
            logger.warning("V2 memory demo mode: use one worker; no crash durability.")
        logger.info("AI Service lifespan initialized.")
        yield
    finally:
        await close_mongo_connection()
        logger.info("AI Service lifespan shutdown.")

app = FastAPI(
    title="AI Stroke Risk & Signal Processing Service",
    version="1.0.0",
    lifespan=lifespan
)
app.include_router(v2_router)
app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # Do not echo NaN/Inf, raw sensor arrays, or non-serializable validator contexts.
    errors = [{key: error[key] for key in ("loc", "msg", "type")}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai_service_fastapi",
        "model_loaded": afib_detector.model is not None
    }

@app.post("/api/v1/analyze")
async def analyze_sensor_window(payload: AnalyzePayload):
    device_id = payload.device_id
    ts_val = payload.timestamp if payload.timestamp is not None else datetime.now(timezone.utc).timestamp()
    try:
        dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise HTTPException(422, "Invalid timestamp") from None

    vitals = payload.vitals or {}
    accel = payload.accel or {}
    ecg = payload.ecg or {}

    spo2_list = vitals.get("spo2", [])
    bpm_list = vitals.get("bpm", [])
    ax = accel.get("ax", [])
    ay = accel.get("ay", [])
    az = accel.get("az", [])
    samples = ecg.get("samples", [])
    fs = ecg.get("fs", 125)

    # 1. Module 1: Context-aware SpO2 & Motion filter
    context_res = evaluate_context(spo2_list, ax, ay, az)

    # 2. Module 2: Fall Detection
    fall_res = evaluate_fall(ax, ay, az, bpm_list)

    # 3. Module 3: ECG Preprocessing & HRV extraction
    ecg_res = extract_hrv_features(samples, fs)
    hrv_features = ecg_res.get("features")

    # 4. Module 4: AFib & Stroke Risk Classification
    if hrv_features is not None:
        afib_res = afib_detector.classify(hrv_features)
    else:
        afib_res = {
            "afib_detected": False,
            "afib_probability": 0.0,
            "decision_class": ecg_res.get("status", "NO_ECG"),
            "recommendation": ecg_res.get("message", "Chưa có tín hiệu ECG hợp lệ.")
        }

    # Consolidated Result Document
    ai_doc = {
        "device_id": device_id,
        "timestamp": dt,
        "context_status": context_res["context_status"],
        "context_severity": context_res["severity"],
        "fall_status": fall_res["fall_status"],
        "afib_detected": afib_res["afib_detected"],
        "afib_probability": afib_res["afib_probability"],
        "decision_class": afib_res["decision_class"],
        "hrv_metrics": hrv_features if hrv_features else {},
        "recommendation": afib_res["recommendation"],
        "details": {
            "context": context_res,
            "fall": fall_res,
            "ecg_status": ecg_res.get("status")
        }
    }

    # Persist directly into MongoDB collection ai_results
    await save_ai_result(ai_doc)

    # Format output for response (convert datetime to ISO string)
    response_data = dict(ai_doc)
    response_data["timestamp"] = dt.isoformat()
    if "_id" in response_data:
        response_data["_id"] = str(response_data["_id"])

    return response_data
