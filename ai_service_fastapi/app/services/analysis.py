from copy import deepcopy
import hashlib
import json

import numpy as np

from app.algorithms.v2.context import evaluate_context
from app.algorithms.v2.ecg import extract_features
from app.algorithms.v2.fall import evaluate_fall
from app.schemas.v2 import AnalyzeResponseV2
from app.services.aggregation import aggregate
from app.services.errors import WindowConflict


def analyze_window(request, previous, predictor, config, persistence_status):
    """Pure transition: neither mutate previous state nor perform I/O."""
    state = deepcopy(previous or {})
    policy_fields = ["max_gap_seconds", "spo2_low", "spo2_clear", "spo2_confirm_seconds",
                     "spo2_clear_seconds", "impact_g", "tilt_degrees", "post_seconds",
                     "immobility_rms", "ecg_min_seconds", "ecg_low_hz", "ecg_high_hz",
                     "afib_warning_score", "afib_high_score"]
    policy = {name: getattr(config, name) for name in policy_fields}
    policy["algorithm_version"] = "research-v2.0"
    policy["model_sha256"] = predictor.metadata["model_sha256"] if predictor.metadata else None
    signature = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
    if state.get("policy_signature", signature) != signature:
        raise WindowConflict("POLICY_CHANGED: use a new session")
    state["policy_signature"] = signature
    start, end = request.start_time.timestamp(), request.end_time.timestamp()
    last_end = state.get("last_end")
    if last_end is not None and end <= last_end + 1e-6:
        raise WindowConflict("OUT_OF_ORDER: window must add new time")
    if last_end is not None and start - last_end > config.max_gap_seconds:
        # Individual algorithms mark pending events incomplete across gaps.
        state.pop("afib_event", None)
    times = np.array([], dtype=float)
    xyz = np.empty((0, 3))
    motion = None
    if request.accel:
        sensor = request.accel
        times = start + np.arange(len(sensor.ax)) / sensor.fs
        xyz = np.column_stack([sensor.ax, sensor.ay, sensor.az]).astype(float)
        if sensor.unit == "m/s2":
            xyz /= 9.80665
        # A changed sample rate invalidates an unfinished post-impact segment.
        if state.get("accel_fs") is not None and state["accel_fs"] != sensor.fs:
            if state.get("fall", {}).get("candidate"):
                raise WindowConflict("SAMPLE_RATE_CHANGED: use a new session")
        state["accel_fs"] = sensor.fs
        if request.vitals and request.vitals.spo2:
            vt = [sample.timestamp.timestamp() for sample in request.vitals.spo2]
            aligned = xyz[(times >= min(vt) - 0.5) & (times <= max(vt) + 0.5)]
            if len(aligned) >= 2:
                motion = float(np.std(np.linalg.norm(aligned, axis=1)))
    samples = [(sample.timestamp.timestamp(), float(sample.value))
               for sample in request.vitals.spo2] if request.vitals else []
    context, context_state = evaluate_context(samples, motion, state.get("context"), end, config)
    fall, fall_state = evaluate_fall(times, xyz, state.get("fall"), end, config)
    if request.vitals and len(request.vitals.bpm) >= 2:
        bpm = request.vitals.bpm
        fall["metrics"].update(vitals_status="AVAILABLE", delta_bpm=abs(bpm[-1].value - bpm[0].value))
    ecg_window = request.ecg
    ecg = extract_features(ecg_window.samples if ecg_window else None,
                           ecg_window.fs if ecg_window else 125, config,
                           ecg_window.lead_off if ecg_window else False)
    afib = predictor.classify(ecg)
    state["max_gap_seconds"] = config.max_gap_seconds
    events, severity, recommendation = aggregate(request, context, fall, afib, state)
    state.update(context=context_state, fall=fall_state, last_end=end)
    response = AnalyzeResponseV2(
        device_id=request.device_id, session_id=request.session_id, window_id=request.window_id,
        start_time=request.start_time, end_time=request.end_time,
        context=context, fall=fall, ecg=ecg, afib=afib, events=events,
        overall_severity=severity, recommendation=recommendation,
        persistence_status=persistence_status,
    )
    return response.model_dump(mode="json"), state
