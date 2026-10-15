from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional
from bson import ObjectId
from app.database import db
from app.schemas import AlertAcknowledgeRequest

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("")
async def get_alerts(
    device_id: Optional[str] = Query(None, description="Optional device ID filter"),
    type: str = Query("all", description="'emergency', 'ai', or 'all'"),
    limit: int = Query(50, ge=1, le=200)
):
    if db.db is None:
        raise HTTPException(status_code=503, detail="Database not ready")

    query = {}
    if device_id:
        query["device_id"] = device_id

    results = {"alerts": [], "ai_results": []}

    if type in ["all", "emergency"]:
        cursor = db.db.alerts.find(query).sort("timestamp", -1).limit(limit)
        alerts_list = await cursor.to_list(length=limit)
        for doc in alerts_list:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                doc["timestamp"] = doc["timestamp"].isoformat()
        results["alerts"] = alerts_list

    if type in ["all", "ai"]:
        ai_query = {}
        if device_id:
            ai_query["device_id"] = device_id
        cursor_ai = db.db.ai_results.find(ai_query).sort("timestamp", -1).limit(limit)
        ai_list = await cursor_ai.to_list(length=limit)
        for doc in ai_list:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                doc["timestamp"] = doc["timestamp"].isoformat()
        results["ai_results"] = ai_list

    return results

@router.patch("/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: str = Path(..., description="MongoDB ObjectID of the alert"),
    body: AlertAcknowledgeRequest = AlertAcknowledgeRequest()
):
    if db.db is None:
        raise HTTPException(status_code=503, detail="Database not ready")

    try:
        obj_id = ObjectId(alert_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

    update_res = await db.db.alerts.update_one(
        {"_id": obj_id},
        {"$set": {"is_acknowledged": body.is_acknowledged}}
    )
    if update_res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "success", "alert_id": alert_id, "is_acknowledged": body.is_acknowledged}
