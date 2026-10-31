"""Atomic result/state commits. Mongo mode requires transactions (replica set/mongos)."""
import asyncio
from copy import deepcopy
import hashlib
import json
import logging

import anyio
from pymongo import ReadPreference, timeout
from pymongo.errors import CollectionInvalid, DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.services.errors import PersistenceUnavailable, WindowConflict

logger = logging.getLogger(__name__)


def identity(request):
    session = json.dumps([request.device_id, request.session_id], separators=(",", ":"))
    key = hashlib.sha256(session.encode()).hexdigest()
    window = hashlib.sha256(json.dumps([key, request.window_id]).encode()).hexdigest()
    content = hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True,
                                        separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return key, window, content


class MemoryStore:
    """Explicit demo mode: one process, bounded capacity, no crash durability."""
    persistence_status = "memory_only"

    def __init__(self, config):
        self.config = config
        self.states = {}
        self.results = {}
        self.lock = asyncio.Lock()

    async def ready(self):
        return True

    async def initialize(self):
        pass

    async def transact(self, request, transition):
        key, window, content = identity(request)
        async with self.lock:
            if window in self.results:
                old = self.results[window]
                if old["content"] != content:
                    raise WindowConflict("WINDOW_CONTENT_CONFLICT")
                return deepcopy(old["result"])
            if len(self.results) >= self.config.max_windows_memory or (key not in self.states and len(self.states) >= self.config.max_sessions):
                raise PersistenceUnavailable("Demo memory capacity reached; start a new process or use MongoDB")
            result, state = await anyio.to_thread.run_sync(transition, deepcopy(self.states.get(key, {})))
            self.states[key] = state
            self.results[window] = {"content": content, "result": deepcopy(result)}
            return result


class MongoStore:
    persistence_status = "stored"

    def __init__(self, client, database, timeout_ms):
        self.client = client
        self.database = database
        self.timeout_ms = timeout_ms
        self.initialized = False

    async def initialize(self):
        if not await self.ready(check_initialized=False):
            return
        await self.database.ai_results_v2.create_index(
            [("device_id", 1), ("session_id", 1), ("window_id", 1)], unique=True)
        await self.database.ai_results_v2.create_index([("device_id", 1), ("start_time", 1)])
        try:
            await self.database.create_collection("ai_sessions_v2")
        except CollectionInvalid:
            pass  # Another worker may already have created the collection.
        self.initialized = True

    async def ready(self, check_initialized=True):
        if check_initialized and not self.initialized:
            try:
                await self.initialize()
            except PyMongoError:
                return False
            if not self.initialized:
                return False
        try:
            hello = await self.client.admin.command("hello")
            return bool(hello.get("logicalSessionTimeoutMinutes") is not None and
                        (hello.get("setName") or hello.get("msg") == "isdbgrid"))
        except PyMongoError:
            return False

    async def transact(self, request, transition):
        if not self.initialized:
            if not await self.ready():
                raise PersistenceUnavailable("MongoDB replica set with transactions is required for v2")
        key, window, content = identity(request)

        async def callback(session):
            prior = await self.database.ai_results_v2.find_one({"_id": window}, session=session)
            if prior:
                if prior["content_hash"] != content:
                    raise WindowConflict("WINDOW_CONTENT_CONFLICT")
                return prior["result"]
            previous = await self.database.ai_sessions_v2.find_one({"_id": key}, session=session)
            result, state = await anyio.to_thread.run_sync(
                transition, deepcopy(previous["state"] if previous else {}))
            # A single transaction writes both ledger and state. A conflicting write
            # causes with_transaction to retry the side-effect-free callback.
            await self.database.ai_sessions_v2.replace_one(
                {"_id": key}, {"_id": key, "state": state}, upsert=True, session=session)
            await self.database.ai_results_v2.insert_one({
                "_id": window, "device_id": request.device_id, "session_id": request.session_id,
                "window_id": request.window_id, "start_time": request.start_time,
                "content_hash": content, "result": result,
            }, session=session)
            return result

        try:
            # Bound the complete transaction/retry budget, not just one socket read.
            with timeout(3 * self.timeout_ms / 1000):
                for attempt in range(3):
                    try:
                        async with await self.client.start_session() as session:
                            return await session.with_transaction(
                                callback, read_concern=ReadConcern("snapshot"),
                                write_concern=WriteConcern("majority", wtimeout=self.timeout_ms),
                                read_preference=ReadPreference.PRIMARY,
                                max_commit_time_ms=self.timeout_ms,
                            )
                    except DuplicateKeyError:
                        # Concurrent first-window upserts can race before a state exists.
                        # Retry the whole transaction against the committed row.
                        if attempt == 2:
                            raise
        except PyMongoError as exc:
            # Do not expose credentials or driver internals in HTTP error details.
            logger.warning("V2 persistence failed (%s)", type(exc).__name__)
            raise PersistenceUnavailable("No confirmed MongoDB commit; retry the same window identity") from exc
