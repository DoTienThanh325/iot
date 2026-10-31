from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def window(start=0, seconds=10, window_id="w1", **sensors):
    return {
        "device_id": "demo", "session_id": "session-1", "window_id": window_id,
        "start_time": (BASE + timedelta(seconds=start)).isoformat(),
        "end_time": (BASE + timedelta(seconds=start + seconds)).isoformat(),
        **sensors,
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: Settings(storage_mode="memory")))
    with TestClient(app) as test_client:
        yield test_client
