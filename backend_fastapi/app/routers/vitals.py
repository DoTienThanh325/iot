from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.database import db

router = APIRouter(prefix="/api/vitals", tags=["Vitals"])

@router.get("")
async def get_recent_vitals(
    device_id: str = Query(..., description="Device ID e.g. esp32_01"),
    limit: int = Query(60, ge=1, le=500, description="Number of recent records to retrieve")
):
    if db.db is None:
        raise HTTPException(status_code=503, detail="Database not ready")
    
    cursor = db.db.vitals.find({"device_id": device_id}).sort("timestamp", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    
    # Format documents for JSON output
    for doc in records:
        doc["_id"] = str(doc["_id"])
        if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
            doc["timestamp"] = doc["timestamp"].isoformat()
            
    # Return chronologically ascending
    return list(reversed(records))
