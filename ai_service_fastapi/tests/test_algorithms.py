from datetime import timedelta

import numpy as np

from app.algorithms.v2.afib import AFibPredictor
from app.algorithms.v2.context import evaluate_context
from app.algorithms.v2.ecg import FEATURES, extract_features
from app.algorithms.v2.fall import evaluate_fall
from app.config import Settings
from tests.conftest import BASE, window


def test_spo2_cross_window_persistence_and_gaps():
    config = Settings()
    first, state = evaluate_context([(i, 89) for i in range(6)], None, {}, 6, config)
    assert first["analysis_status"] == "LOW_SPO2_SUSPECTED"
    second, state = evaluate_context([(i, 89) for i in range(4, 12)], None, state, 12, config)
    assert second["analysis_status"] == "LOW_SPO2_PERSISTENT"
    assert second["metrics"]["event_start"] == 0
    third, state = evaluate_context([(20, 89)], None, state, 21, config)
    assert third["analysis_status"] == "LOW_SPO2_SUSPECTED"
    assert state["low_since"] == 20


def test_spo2_motion_degrades_without_dismissing_low_reading():
    result, _ = evaluate_context([(i, 89) for i in range(20)], .5, {}, 20, Settings())
    assert result["quality_status"] == "LOW_QUALITY"
    assert result["analysis_status"] == "LOW_SPO2_PERSISTENT"


def test_spo2_clear_requires_observed_time():
    config = Settings()
    _, state = evaluate_context([(i, 89) for i in range(12)], 0, {}, 12, config)
    pending, state = evaluate_context([(i, 98) for i in range(12, 16)], 0, state, 16, config)
    assert pending["analysis_status"] == "LOW_SPO2_PERSISTENT"
    cleared, _ = evaluate_context([(i, 98) for i in range(16, 19)], 0, state, 19, config)
    assert cleared["analysis_status"] == "NORMAL"


def test_sustained_low_segment_is_not_removed_as_global_outlier():
    values = [(i, 89 if i < 12 else 98) for i in range(28)]
    result, _ = evaluate_context(values, 0, {}, 28, Settings(spo2_clear_seconds=30))
    assert result["analysis_status"] == "LOW_SPO2_PERSISTENT"
    assert result["metrics"]["valid_samples"] == 28


def test_spo2_event_preserved_if_cleared_before_window_end(client):
    readings = [{"timestamp": (BASE + timedelta(seconds=i)).isoformat(),
                 "value": 89 if i < 12 else 98} for i in range(30)]
    result = client.post("/api/v2/analyze", json=window(seconds=30, vitals={"spo2": readings})).json()
    assert result["context"]["analysis_status"] == "NORMAL"
    assert len(result["events"]) == 1
    assert result["events"][0]["type"] == "LOW_SPO2"
    assert result["overall_severity"] == "CRITICAL"


def fall_signal():
    times = np.arange(0, 6, .02)
    xyz = np.tile([0., 0., 1.], (len(times), 1))
    xyz[100] = [0, 0, 3]
    xyz[101:] = [1, 0, 0]
    return times, xyz


def test_fall_waits_and_matches_unsplit_signal():
    times, xyz = fall_signal()
    config = Settings()
    whole, _ = evaluate_fall(times, xyz, {}, 6, config)
    assert whole["analysis_status"] == "FALL_SUSPECTED"
    first, state = evaluate_fall(times[:101], xyz[:101], {}, 2.02, config)
    assert first["analysis_status"] == "PENDING"
    second, _ = evaluate_fall(times[90:], xyz[90:], state, 6, config)
    assert second["metrics"]["completed_candidates"] == whole["metrics"]["completed_candidates"]


def test_pending_fall_expires_incomplete():
    times, xyz = fall_signal()
    _, state = evaluate_fall(times[:101], xyz[:101], {}, 2.02, Settings())
    result, _ = evaluate_fall([], [], state, 10, Settings())
    assert result["analysis_status"] == "INCOMPLETE"


def test_ecg_known_periodic_peaks_and_polarity():
    fs = 125
    time = np.arange(fs * 20) / fs
    signal = np.zeros_like(time)
    for beat in np.arange(.5, 20, .8):
        signal += np.exp(-.5 * ((time - beat) / .018) ** 2)
    positive = extract_features(signal, fs, Settings())
    negative = extract_features(-signal, fs, Settings())
    assert positive["quality_status"] == "VALID"
    assert positive["metrics"]["peaks_count"] == 25
    assert abs(positive["metrics"]["features"]["HR_mean"] - 75) < 1
    assert positive["metrics"]["features"] == negative["metrics"]["features"]


def test_flat_and_short_do_not_claim_lead_off():
    assert extract_features([0] * 2500, 125, Settings())["analysis_status"] == "FLAT_SIGNAL"
    assert extract_features([0] * 400, 125, Settings())["analysis_status"] == "SHORT_WINDOW"
    assert extract_features([0] * 2500, 125, Settings(), lead_off=True)["analysis_status"] == "ECG_LEAD_OFF"


def test_high_single_feature_warns_and_is_not_a_probability():
    predictor = AFibPredictor(Settings())
    features = dict(zip(FEATURES, [75, 110, 0, 0, 0]))
    result = predictor.classify({"quality_status": "VALID", "metrics": {"features": features}})
    assert result["analysis_status"] == "IRREGULARITY_WARNING"
    assert result["afib_probability"] is None
    assert result["heuristic_score"] == .35


def test_fall_event_survives_non_afib(client):
    times, xyz = fall_signal()
    payload = window(seconds=6, accel={"fs": 50, "unit": "g", "ax": xyz[:, 0].tolist(),
                                     "ay": xyz[:, 1].tolist(), "az": xyz[:, 2].tolist()})
    result = client.post("/api/v2/analyze", json=payload).json()
    assert result["events"][0]["type"] == "FALL_SUSPECTED"
    assert result["overall_severity"] == "CRITICAL"


def test_acceleration_units_are_equivalent(client):
    _, xyz = fall_signal()
    results = []
    for index, (unit, factor) in enumerate([("g", 1), ("m/s2", 9.80665)]):
        sensor = xyz * factor
        payload = window(seconds=6, accel={"fs": 50, "unit": unit,
                         "ax": sensor[:, 0].tolist(), "ay": sensor[:, 1].tolist(), "az": sensor[:, 2].tolist()})
        payload["session_id"] = f"units-{index}"
        results.append(client.post("/api/v2/analyze", json=payload).json())
    assert results[0]["fall"]["analysis_status"] == results[1]["fall"]["analysis_status"] == "FALL_SUSPECTED"
