from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime
from app.database import db

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("")
async def get_history(
    device_id: str = Query(..., description="Device ID e.g. esp32_01"),
    start_ts: Optional[float] = Query(None, description="Start timestamp (Unix seconds)"),
    end_ts: Optional[float] = Query(None, description="End timestamp (Unix seconds)"),
    limit: int = Query(200, ge=1, le=1000)
):
    if db.db is None:
        raise HTTPException(status_code=503, detail="Database not ready")

    query = {"device_id": device_id}
    if start_ts is not None or end_ts is not None:
        query["timestamp"] = {}
        if start_ts is not None:
            query["timestamp"]["$gte"] = datetime.utcfromtimestamp(start_ts)
        if end_ts is not None:
            query["timestamp"]["$lte"] = datetime.utcfromtimestamp(end_ts)

    # 1. Fetch historical vitals
    vitals_cursor = db.db.vitals.find(query).sort("timestamp", -1).limit(limit)
    vitals = await vitals_cursor.to_list(length=limit)
    for v in vitals:
        v["_id"] = str(v["_id"])
        if "timestamp" in v and hasattr(v["timestamp"], "isoformat"):
            v["timestamp"] = v["timestamp"].isoformat()

    # 2. Fetch historical ECG segments (limit to 20 recent segments)
    ecg_cursor = db.db.ecg.find(query).sort("timestamp", -1).limit(min(limit, 20))
    ecg_records = await ecg_cursor.to_list(length=min(limit, 20))
    for e in ecg_records:
        e["_id"] = str(e["_id"])
        if "timestamp" in e and hasattr(e["timestamp"], "isoformat"):
            e["timestamp"] = e["timestamp"].isoformat()

    return {
        "device_id": device_id,
        "vitals_count": len(vitals),
        "vitals": list(reversed(vitals)),
        "ecg_count": len(ecg_records),
        "ecg": list(reversed(ecg_records))
    }
