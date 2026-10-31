"""Run only against an explicitly provided test replica-set URI."""
from concurrent.futures import ThreadPoolExecutor
import os
import uuid

from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import pytest

from app.config import Settings
from app.main import app
from tests.conftest import window

pytestmark = pytest.mark.integration


@pytest.fixture
def mongo_client(monkeypatch):
    uri = os.getenv("AI_TEST_MONGO_URI")
    if not uri:
        pytest.skip("Set AI_TEST_MONGO_URI to an isolated test replica set")
    name = "ai_service_test_" + uuid.uuid4().hex
    config = Settings(mongo_uri=uri, mongo_db=name, mongo_timeout_ms=3000)
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: config))
    with MongoClient(uri, serverSelectionTimeoutMS=3000) as observer:
        hello = observer.admin.command("hello")
        assert hello.get("setName") or hello.get("msg") == "isdbgrid"
        try:
            with TestClient(app) as client:
                assert client.get("/health/ready").status_code == 200
                yield client, observer[name]
        finally:
            # Only remove the randomly named database created by this fixture.
            observer.drop_database(name)


def test_mongo_atomic_idempotency_across_concurrent_requests(mongo_client):
    client, database = mongo_client
    payload = window()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, "/api/v2/analyze", json=payload) for _ in range(2)]
        responses = [future.result() for future in futures]
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert responses[0].json()["persistence_status"] == "stored"
    assert database.ai_results_v2.count_documents({}) == 1
    assert database.ai_sessions_v2.count_documents({}) == 1
    changed = window(seconds=11)
    assert client.post("/api/v2/analyze", json=changed).status_code == 409


def test_mongo_rolls_back_state_when_result_insert_fails(mongo_client, monkeypatch):
    client, database = mongo_client
    original = AsyncIOMotorCollection.insert_one

    async def fail_insert(collection, document, *args, **kwargs):
        if collection.name == "ai_results_v2":
            raise OperationFailure("injected result insert failure")
        return await original(collection, document, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(AsyncIOMotorCollection, "insert_one", fail_insert)
        assert client.post("/api/v2/analyze", json=window()).status_code == 503
    assert database.ai_results_v2.count_documents({}) == 0
    assert database.ai_sessions_v2.count_documents({}) == 0
    assert client.post("/api/v2/analyze", json=window()).status_code == 200
    assert database.ai_results_v2.count_documents({}) == 1
    assert database.ai_sessions_v2.count_documents({}) == 1
