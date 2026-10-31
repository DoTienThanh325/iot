import asyncio
from datetime import timedelta

import pytest

from app.config import Settings
from app.main import app
from app.services.errors import PersistenceUnavailable
from tests.conftest import BASE, window


def test_missing_data_is_unknown_and_idempotent(client):
    payload = window()
    first = client.post("/api/v2/analyze", json=payload)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["context"]["metrics"]["mean_spo2"] is None
    assert result["afib"]["afib_detected"] is None
    assert result["afib"]["afib_probability"] is None
    assert result["overall_severity"] == "UNKNOWN"
    assert result["persistence_status"] == "memory_only"
    assert client.post("/api/v2/analyze", json=payload).json() == result
    assert len(app.state.runtime["store"].results) == 1


def test_conflicting_payload_and_order(client):
    payload = window()
    assert client.post("/api/v2/analyze", json=payload).status_code == 200
    assert client.post("/api/v2/analyze", json=window(seconds=11)).status_code == 409
    assert client.post("/api/v2/analyze", json=window(window_id="old")).status_code == 409


@pytest.mark.parametrize("field,value", [("fs", 0), ("fs", "125"), ("fs", True)])
def test_strict_numeric_schema(client, field, value):
    ecg = {"fs": 125, "unit": "mV", "samples": [0] * 1250}
    ecg[field] = value
    assert client.post("/api/v2/analyze", json=window(ecg=ecg)).status_code == 422


def test_invalid_timing_axes_and_timezone(client):
    payload = window(accel={"fs": 5, "unit": "g", "ax": [0] * 50, "ay": [0], "az": [1] * 50})
    assert client.post("/api/v2/analyze", json=payload).status_code == 422
    payload = window(ecg={"fs": 125, "unit": "mV", "samples": [0] * 100})
    assert client.post("/api/v2/analyze", json=payload).status_code == 422
    payload = window()
    payload["start_time"] = "2026-01-01T00:00:00"
    assert client.post("/api/v2/analyze", json=payload).status_code == 422


def test_nonfinite_and_unknown_fields(client):
    payload = window()
    payload["unknown"] = 10
    assert client.post("/api/v2/analyze", json=payload).status_code == 422
    import json
    raw = json.dumps(window(ecg={"fs": 125, "unit": "mV", "samples": [float("nan")] * 1250}))
    assert client.post("/api/v2/analyze", content=raw, headers={"Content-Type": "application/json"}).status_code == 422


def test_health_and_legacy_timestamp_zero(client, monkeypatch):
    async def fake_save(doc):
        return doc
    monkeypatch.setattr("app.main.save_ai_result", fake_save)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["degraded"] is True
    result = client.post("/api/v1/analyze", json={"device_id": "old", "timestamp": 0})
    assert result.status_code == 200
    assert result.json()["timestamp"] == "1970-01-01T00:00:00+00:00"


def test_critical_spo2_not_overwritten_by_missing_ecg(client):
    vitals = {"spo2": [{"timestamp": (BASE + timedelta(seconds=i)).isoformat(), "value": 89}
                        for i in range(20)]}
    result = client.post("/api/v2/analyze", json=window(seconds=20, vitals=vitals)).json()
    assert result["context"]["analysis_status"] == "LOW_SPO2_PERSISTENT"
    assert result["context"]["metrics"]["motion_status"] == "UNKNOWN"
    assert result["events"][0]["type"] == "LOW_SPO2"
    assert result["overall_severity"] == "CRITICAL"
    assert result["afib"]["afib_detected"] is None


def test_storage_failure_does_not_commit_state(client, monkeypatch):
    store = app.state.runtime["store"]
    async def unavailable(*args):
        raise PersistenceUnavailable("test unavailable")
    monkeypatch.setattr(store, "transact", unavailable)
    result = client.post("/api/v2/analyze", json=window())
    assert result.status_code == 503
    assert not store.states


def test_capacity_body_limit_and_semaphore(client):
    runtime = app.state.runtime
    runtime["config"] = Settings(storage_mode="memory", max_body_bytes=1024)
    assert client.post("/api/v2/analyze", content=b"x" * 1025).status_code == 413
    runtime["semaphore"] = asyncio.Semaphore(0)
    assert client.post("/api/v2/analyze", json=window()).status_code == 429


def test_memory_capacity_never_evicts_idempotency(client):
    store = app.state.runtime["store"]
    store.config = Settings(storage_mode="memory", max_windows_memory=1)
    payload = window()
    assert client.post("/api/v2/analyze", json=payload).status_code == 200
    assert client.post("/api/v2/analyze", json=window(start=10, window_id="w2")).status_code == 503
    assert client.post("/api/v2/analyze", json=payload).status_code == 200


def test_internal_failure_is_traceable_and_does_not_commit(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("injected algorithm failure")
    monkeypatch.setattr(app.state.runtime["predictor"], "classify", fail)
    response = client.post("/api/v2/analyze", json=window())
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "ANALYSIS_FAILED"
    assert len(response.json()["detail"]["request_id"]) == 32
    assert not app.state.runtime["store"].states
