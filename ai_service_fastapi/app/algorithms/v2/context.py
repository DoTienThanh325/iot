"""SpO2 persistence with explicit uncertainty and timestamp-based hysteresis."""
import numpy as np


def evaluate_context(samples, motion, previous, window_end, config):
    state = dict(previous or {})
    last = state.get("last_time")
    fresh = [(t, value) for t, value in samples if t > (last if last is not None else -float("inf"))]
    metrics = {"mean_spo2": None, "motion_std_svm": motion,
               "motion_status": "UNKNOWN" if motion is None else "AVAILABLE",
               "input_samples": len(fresh), "valid_samples": 0, "episodes": []}
    if not fresh:
        if last is not None and window_end - last > config.max_gap_seconds:
            state = {}
        return {"quality_status": "NO_DATA", "analysis_status": "UNDETERMINED",
                "metrics": metrics}, state
    values = np.array([v for _, v in fresh], dtype=float)
    valid = values > 0
    # Only flag isolated excursions bracketed by agreeing adjacent readings.
    # A global-window median could erase a sustained low segment when most of
    # the window is normal. Boundaries remain observations, not invented data.
    for index in range(1, len(values) - 1):
        left, value, right = values[index - 1:index + 2]
        close_in_time = fresh[index + 1][0] - fresh[index - 1][0] <= 2 * config.max_gap_seconds
        if close_in_time and abs(left - right) <= 1 and abs(value - (left + right) / 2) > 5:
            valid[index] = False
    metrics["valid_samples"] = int(valid.sum())
    metrics["rejected_ratio"] = float(1 - valid.mean())
    for (timestamp, value), accepted in zip(fresh, valid):
        if not accepted:
            state = {"last_time": timestamp}
            continue
        if "last_time" in state and timestamp - state["last_time"] > config.max_gap_seconds:
            state = {}
        state["last_time"] = timestamp
        if value < config.spo2_low:
            state.setdefault("low_since", timestamp)
            state.pop("clear_since", None)
            if timestamp - state["low_since"] >= config.spo2_confirm_seconds:
                state["active"] = True
        elif value >= config.spo2_clear:
            state.setdefault("clear_since", timestamp)
            if not state.get("active") or timestamp - state["clear_since"] >= config.spo2_clear_seconds:
                if state.get("active"):
                    metrics["episodes"].append({"event_start": state["low_since"],
                                                "event_end": timestamp, "persistent": True})
                state.pop("low_since", None)
                state["active"] = False
        else:
            state.pop("clear_since", None)
            if not state.get("active"):
                state.pop("low_since", None)
    if valid.sum() == 0:
        return {"quality_status": "LOW_QUALITY", "analysis_status": "UNDETERMINED",
                "metrics": metrics}, state
    metrics["mean_spo2"] = float(np.mean(values[valid]))
    metrics["median_spo2"] = float(np.median(values[valid]))
    motion_noise = motion is not None and motion > 0.15
    quality = "LOW_QUALITY" if motion_noise or valid.mean() < 0.8 else "VALID"
    if state.get("active"):
        status = "LOW_SPO2_PERSISTENT"
        metrics.update(event_start=state["low_since"], event_end=state["last_time"])
        metrics["episodes"].append({"event_start": state["low_since"],
                                    "event_end": state["last_time"], "persistent": True})
    elif state.get("low_since") is not None:
        status = "LOW_SPO2_SUSPECTED"
        metrics.update(event_start=state["low_since"], event_end=state["last_time"])
        metrics["episodes"].append({"event_start": state["low_since"],
                                    "event_end": state["last_time"], "persistent": False})
    elif metrics["median_spo2"] < config.spo2_clear:
        status = "BORDERLINE_SPO2"
    else:
        status = "NORMAL"
    if window_end - state.get("last_time", window_end) > config.max_gap_seconds:
        status, quality, state = "UNDETERMINED", "LOW_QUALITY", {}
        metrics.pop("event_start", None)
        metrics.pop("event_end", None)
    return {"quality_status": quality, "analysis_status": status, "metrics": metrics}, state
