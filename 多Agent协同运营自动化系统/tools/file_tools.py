from __future__ import annotations
import os
import json
import logging
import aiofiles
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FileTools:
    """File system tools for agents."""

    DEFAULT_BASE_DIR = Path("./data")

    @classmethod
    async def read_text(cls, filepath: str) -> Optional[str]:
        try:
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.error("Error reading %s: %s", filepath, e)
            return None

    @classmethod
    async def write_text(cls, filepath: str, content: str) -> bool:
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error("Error writing %s: %s", filepath, e)
            return False

    @classmethod
    async def read_json(cls, filepath: str) -> Optional[Any]:
        content = await cls.read_text(filepath)
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in %s: %s", filepath, e)
        return None

    @classmethod
    async def write_json(cls, filepath: str, data: Any) -> bool:
        try:
            return await cls.write_text(filepath, json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error("Error writing JSON to %s: %s", filepath, e)
            return False

    @classmethod
    async def list_files(cls, directory: str, pattern: str = "*") -> list[str]:
        try:
            from glob import glob
            return glob(os.path.join(directory, pattern))
        except Exception as e:
            logger.error("Error listing %s: %s", directory, e)
            return []

    @classmethod
    async def ensure_dir(cls, directory: str) -> bool:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error("Error creating dir %s: %s", directory, e)
            return False

    @classmethod
    async def save_report(cls, name: str, content: str, subdir: str = "reports") -> str:
        base = cls.DEFAULT_BASE_DIR / subdir
        base.mkdir(parents=True, exist_ok=True)
        filepath = base / f"{name}.md"
        await cls.write_text(str(filepath), content)
        return str(filepath)

    @classmethod
    async def log_event(cls, event_type: str, data: dict, subdir: str = "logs") -> str:
        base = cls.DEFAULT_BASE_DIR / subdir
        base.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        filename = f"{event_type}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        filepath = base / filename
        async with aiofiles.open(str(filepath), "a", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False) + "\n")
        return str(filepath)
