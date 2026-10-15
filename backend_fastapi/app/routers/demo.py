import time
import math
import numpy as np
import httpx
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.schemas import InjectAFibRequest
from app.services.buffer_batch import buffer_manager
from app.services.websocket_manager import ws_manager
from app.services.alert_router import alert_router

router = APIRouter(prefix="/api/demo", tags=["Demo"])

def generate_afib_ecg_sample(duration_sec: float = 10.0, fs: int = 125):
    """
    Synthesize an ECG signal displaying Atrial Fibrillation:
    - Irregular RR intervals (random / highly variable: ~490, 880, 530, 920 ms)
    - Absent P waves replaced by fibrillatory waves (f-waves: 4-7 Hz noise)
    - Normal QRS complexes at irregular timestamps
    """
    total_samples = int(duration_sec * fs)
    t = np.linspace(0, duration_sec, total_samples)
    
    # 1. Baseline wander + Fibrillatory waves (4-8 Hz high-frequency low-amplitude oscillation)
    ecg = 0.08 * np.sin(2 * np.pi * 5.5 * t) + 0.05 * np.sin(2 * np.pi * 7.2 * t)
    
    # 2. Generate irregular R peaks with alternating RR intervals [490, 880, 530, 920, 480, 890, ...]
    rr_intervals_ms = [490, 880, 530, 920, 480, 890, 520, 930, 470, 860, 540, 910, 480, 870]
    current_time_sec = 0.2
    
    for rr in rr_intervals_ms:
        if current_time_sec >= duration_sec:
            break
        peak_idx = int(current_time_sec * fs)
        # Add QRS complex (narrow spike)
        for offset, amp in [(-2, -0.15), (-1, -0.3), (0, 1.4), (1, -0.4), (2, -0.1)]:
            idx = peak_idx + offset
            if 0 <= idx < total_samples:
                ecg[idx] += amp
        
        # Add T wave (~180ms after R peak)
        t_peak_idx = peak_idx + int(0.18 * fs)
        for offset, amp in [(-4, 0.05), (-2, 0.15), (0, 0.25), (2, 0.15), (4, 0.05)]:
            idx = t_peak_idx + offset
            if 0 <= idx < total_samples:
                ecg[idx] += amp

        current_time_sec += (rr / 1000.0)

    # Convert to 10-bit ADC integer values centered around 512
    scaled_samples = (ecg * 200 + 512).astype(int).tolist()
    return scaled_samples

@router.post("/inject-afib")
async def inject_afib(req: InjectAFibRequest):
    """
    Demo Scenario 3: Injects a 10s Atrial Fibrillation ECG dataset for the given device
    and immediately requests AI Service analysis.
    """
    device_id = req.device_id
    now_ts = time.time()
    samples = generate_afib_ecg_sample(duration_sec=10.0, fs=125)

    # 1. Push to ring buffer & batch queue
    ecg_payload = {
        "device_id": device_id,
        "ts": now_ts,
        "fs": 125,
        "samples": samples
    }
    await buffer_manager.push_ecg(ecg_payload)

    # Also push vitals with elevated/tachycardic BPM
    vitals_payload = {
        "device_id": device_id,
        "ts": now_ts,
        "bpm": 115.0,
        "spo2": 97.0,
        "temp": 36.8,
        "ax": 0.01,
        "ay": 0.02,
        "az": 0.99
    }
    await buffer_manager.push_vitals(vitals_payload)

    # 2. Broadcast ECG and Vitals to WebSocket clients
    await ws_manager.broadcast(device_id, {"event_type": "ECG", "data": ecg_payload})
    await ws_manager.broadcast(device_id, {"event_type": "VITALS", "data": vitals_payload})

    # 3. Direct trigger to AI Service for instantaneous demo response
    ai_window = {
        "device_id": device_id,
        "timestamp": now_ts,
        "vitals": {
            "bpm": [112.0, 115.0, 118.0],
            "spo2": [97.0, 97.5, 97.0],
            "temp": [36.8, 36.8, 36.8]
        },
        "accel": {
            "ax": [0.01, 0.02, 0.01],
            "ay": [0.02, 0.01, 0.02],
            "az": [0.99, 0.98, 0.99],
            "svm": [0.99, 0.98, 0.99]
        },
        "ecg": {
            "samples": samples,
            "fs": 125
        }
    }

    ai_result = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{settings.AI_SERVICE_URL}/api/v1/analyze", json=ai_window)
            if resp.status_code == 200:
                ai_result = resp.json()
                await ws_manager.broadcast(device_id, {
                    "event_type": "AI_RESULT",
                    "data": ai_result
                })
                # Trigger alert if high risk
                if ai_result.get("afib_detected") or ai_result.get("afib_probability", 0) >= 0.70:
                    await alert_router.route_alert({
                        "device_id": device_id,
                        "alert_type": "AFIB_HIGH_RISK",
                        "severity": "CRITICAL",
                        "message": "Phát hiện bất thường điện tim (Rung nhĩ - AFib) - Khuyến nghị tầm soát nguy cơ đột quỵ!"
                    })
    except Exception as e:
        return {
            "status": "injected_to_buffer",
            "message": f"Injected AFib ECG waveform, but direct AI Service call failed: {e}",
            "device_id": device_id
        }

    return {
        "status": "success",
        "message": "Successfully injected AFib ECG signal and analyzed by AI Service",
        "device_id": device_id,
        "ai_result": ai_result
    }
