import asyncio
from functools import partial
import logging
from time import perf_counter
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.schemas.v2 import AnalyzeRequestV2, AnalyzeResponseV2
from app.services.analysis import analyze_window
from app.services.errors import PersistenceUnavailable, WindowConflict

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health/live")
async def live():
    return {"status": "alive"}


@router.get("/health/ready")
async def ready(request: Request):
    runtime = request.app.state.runtime
    storage = await runtime["store"].ready()
    predictor = runtime["predictor"]
    if not storage or not predictor.ready:
        raise HTTPException(503, detail={"status": "not_ready", "storage_ready": storage,
                                        "model_ready": predictor.ready})
    return {"status": "ready", "storage_mode": runtime["config"].storage_mode,
            "model_loaded": predictor.model is not None,
            "degraded": predictor.model is None or runtime["config"].storage_mode == "memory"}


@router.post("/api/v2/analyze", response_model=AnalyzeResponseV2)
async def analyze(payload: AnalyzeRequestV2, request: Request):
    started = perf_counter()
    request_id = uuid.uuid4().hex
    runtime = request.app.state.runtime
    config, predictor, store = runtime["config"], runtime["predictor"], runtime["store"]
    if not predictor.ready:
        raise HTTPException(503, "Required model unavailable")
    duration = (payload.end_time - payload.start_time).total_seconds()
    if duration > config.max_window_seconds:
        raise HTTPException(422, "Window exceeds configured duration limit")
    arrays = [payload.accel.ax if payload.accel else [], payload.ecg.samples if payload.ecg else []]
    for samples in arrays:
        if len(samples) > config.max_samples:
            raise HTTPException(422, "Sensor exceeds configured sample limit")
    if payload.ecg and payload.ecg.fs <= 2 * config.ecg_high_hz:
        raise HTTPException(422, "ECG sample rate must exceed twice the configured high cutoff")
    try:
        await asyncio.wait_for(runtime["semaphore"].acquire(), timeout=config.acquire_timeout)
    except TimeoutError:
        raise HTTPException(429, "Analysis capacity reached", headers={"Retry-After": "1"}) from None
    try:
        transition = partial(analyze_window, payload, predictor=predictor, config=config,
                             persistence_status=store.persistence_status)
        result = await store.transact(payload, transition)
        logger.info("analysis_complete request=%s device=%s window=%s duration_seconds=%.4f source=%s persistence=%s",
                    request_id, payload.device_id, payload.window_id, perf_counter() - started,
                    result["afib"]["inference_source"], result["persistence_status"])
        return result
    except WindowConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except PersistenceUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception:
        logger.exception("analysis_failed request=%s device=%s window=%s",
                         request_id, payload.device_id, payload.window_id)
        raise HTTPException(500, detail={"code": "ANALYSIS_FAILED", "request_id": request_id}) from None
    finally:
        runtime["semaphore"].release()
