from __future__ import annotations
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from models.task import Task, TaskStatus
from models.message import Message

logger = logging.getLogger(__name__)


class JSONDatabase:
    """Simple JSON file-based database for persistence."""

    def __init__(self, data_dir: str = "data"):
        self._base = Path(data_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path(self, collection: str) -> Path:
        return self._base / f"{collection}.json"

    async def insert(self, collection: str, doc_id: str, data: dict) -> bool:
        async with self._lock:
            docs = await self._load(collection)
            docs[doc_id] = {**data, "_id": doc_id, "_updated": datetime.now().isoformat()}
            return await self._save(collection, docs)

    async def update(self, collection: str, doc_id: str, data: dict) -> bool:
        async with self._lock:
            docs = await self._load(collection)
            if doc_id not in docs:
                return False
            docs[doc_id].update(data)
            docs[doc_id]["_updated"] = datetime.now().isoformat()
            return await self._save(collection, docs)

    async def get(self, collection: str, doc_id: str) -> Optional[dict]:
        async with self._lock:
            docs = await self._load(collection)
            return docs.get(doc_id)

    async def list(self, collection: str, limit: int = 100) -> list[dict]:
        async with self._lock:
            docs = await self._load(collection)
            items = sorted(docs.values(), key=lambda x: x.get("_updated", ""), reverse=True)
            return items[:limit]

    async def delete(self, collection: str, doc_id: str) -> bool:
        async with self._lock:
            docs = await self._load(collection)
            if doc_id not in docs:
                return False
            del docs[doc_id]
            return await self._save(collection, docs)

    async def _load(self, collection: str) -> dict:
        path = self._path(collection)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Error loading %s: %s", collection, e)
            return {}

    async def _save(self, collection: str, data: dict) -> bool:
        path = self._path(collection)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error("Error saving %s: %s", collection, e)
            return False

    async def count(self, collection: str) -> int:
        async with self._lock:
            docs = await self._load(collection)
            return len(docs)

    async def query(self, collection: str, **filters) -> list[dict]:
        async with self._lock:
            docs = await self._load(collection)
            results = []
            for doc in docs.values():
                match = True
                for key, value in filters.items():
                    if key not in doc or doc[key] != value:
                        match = False
                        break
                if match:
                    results.append(doc)
            return results

    async def save_task(self, task: Task) -> bool:
        return await self.insert("tasks", task.id, task.to_dict())

    async def save_message(self, message: Message) -> bool:
        data = {
            "id": message.id,
            "type": message.type.name,
            "sender": message.sender,
            "recipient": message.recipient,
            "content": message.content,
            "correlation_id": message.correlation_id,
            "timestamp": message.timestamp,
        }
        return await self.insert("messages", message.id, data)
