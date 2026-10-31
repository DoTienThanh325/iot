"""Pure streaming state transition; all thresholds are research defaults."""
from copy import deepcopy

import numpy as np


def evaluate_fall(times, xyz, previous, window_end, config):
    state = deepcopy(previous or {})
    history = state.setdefault("history", [])
    completed = []
    incomplete = False
    last_svm = state.get("last_svm", 1.0)
    for timestamp, vector in zip(times, xyz):
        if timestamp <= state.get("last_time", -float("inf")) + 1e-6:
            continue
        if timestamp - state.get("last_time", timestamp) > config.max_gap_seconds:
            incomplete = incomplete or bool(state.get("candidate"))
            state = {"history": []}
            history = state["history"]
            last_svm = 1.0
        svm = float(np.linalg.norm(vector))
        candidate = state.get("candidate")
        if candidate is None and svm >= config.impact_g and last_svm < config.impact_g:
            before = [row[1:] for row in history if timestamp - row[0] <= 1.0]
            enough = len(history) >= 2 and timestamp - history[0][0] >= 0.25
            state["candidate"] = {
                "time": timestamp, "peak_g": svm,
                "before": np.mean(before, axis=0).tolist() if before and enough else None,
                "after": [],
            }
            candidate = state["candidate"]
        if candidate is not None:
            elapsed = timestamp - candidate["time"]
            # Ignore the impact transient, then collect a fixed-duration post segment.
            if elapsed >= 0.5:
                candidate["after"].append([timestamp, *map(float, vector)])
            if elapsed >= config.post_seconds:
                after = candidate["after"]
                if candidate["before"] is None or len(after) < 3:
                    incomplete = True
                else:
                    post = np.array([row[1:] for row in after])
                    g_after = np.mean(post, axis=0)
                    g_before = np.asarray(candidate["before"])
                    denominator = np.linalg.norm(g_before) * np.linalg.norm(g_after)
                    if denominator < 1e-6:
                        incomplete = True
                    else:
                        angle = float(np.degrees(np.arccos(np.clip(
                            np.dot(g_before, g_after) / denominator, -1, 1))))
                        rms = float(np.sqrt(np.mean(np.sum((post - g_after) ** 2, axis=1))))
                        completed.append({
                            "status": "FALL_SUSPECTED" if angle >= config.tilt_degrees and rms <= config.immobility_rms else "REJECTED",
                            "event_start": candidate["time"], "event_end": timestamp,
                            "peak_g": candidate["peak_g"], "tilt_degrees": angle,
                            "dynamic_rms_g": rms,
                        })
                state.pop("candidate", None)
        history.append([float(timestamp), *map(float, vector)])
        while history and timestamp - history[0][0] > 1.0:
            history.pop(0)
        state["last_time"] = float(timestamp)
        state["last_svm"] = svm
        last_svm = svm
    if window_end - state.get("last_time", window_end) > config.max_gap_seconds:
        incomplete = incomplete or bool(state.get("candidate"))
        state = {"history": []}
    suspected = [item for item in completed if item["status"] == "FALL_SUSPECTED"]
    if suspected:
        status = "FALL_SUSPECTED"
    elif state.get("candidate"):
        status = "PENDING"
    elif incomplete:
        status = "INCOMPLETE"
    elif completed:
        status = "REJECTED"
    else:
        status = "NO_EVENT" if len(times) else "UNDETERMINED"
    quality = "VALID" if len(times) else "NO_DATA"
    if incomplete:
        quality = "INSUFFICIENT_DATA"
    return {"quality_status": quality, "analysis_status": status,
            "metrics": {"completed_candidates": completed, "vitals_status": "UNAVAILABLE"}}, state
