from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class VitalsPayload(BaseModel):
    device_id: str
    ts: float = Field(..., description="UNIX timestamp in seconds")
    bpm: float
    spo2: float
    temp: float
    ax: float = 0.0
    ay: float = 0.0
    az: float = 1.0

class ECGPayload(BaseModel):
    device_id: str
    ts: float
    fs: int = 125
    samples: List[float]

class AlertPayload(BaseModel):
    device_id: str
    ts: float
    alert_type: str  # SOS_PRESSED, EDGE_FALL_DETECTED, RESPIRATORY_RISK, AFIB_HIGH_RISK
    bpm: Optional[float] = None
    max_svm: Optional[float] = None
    severity: str = "CRITICAL"
    is_acknowledged: bool = False

class AlertAcknowledgeRequest(BaseModel):
    is_acknowledged: bool = True

class InjectAFibRequest(BaseModel):
    device_id: str = "esp32_01"

class AIAnalysisRequest(BaseModel):
    device_id: str
    timestamp: float
    vitals: Dict[str, Any]  # {"bpm": [...], "spo2": [...], "temp": [...]}
    accel: Dict[str, Any]   # {"ax": [...], "ay": [...], "az": [...]}
    ecg: Dict[str, Any]     # {"samples": [...], "fs": 125}

class AIAnalysisResult(BaseModel):
    device_id: str
    timestamp: datetime
    context_status: str
    fall_status: str
    afib_detected: bool
    afib_probability: float
    hrv_metrics: Dict[str, Any]
    recommendation: str
