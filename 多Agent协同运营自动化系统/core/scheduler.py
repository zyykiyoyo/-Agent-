from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """Schedule periodic and delayed tasks within the agent system."""

    def __init__(self):
        self._jobs: list[dict] = []
        self._running = False
        self._task = None

    def add_job(self, name: str, callback: Callable, interval_seconds: int = 60, start_delay: int = 0):
        self._jobs.append({
            "name": name,
            "callback": callback,
            "interval": interval_seconds,
            "start_delay": start_delay,
            "last_run": None,
            "next_run": datetime.now() + timedelta(seconds=start_delay),
        })
        logger.info("Scheduled job: %s (every %ds)", name, interval_seconds)
        return self

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self):
        while self._running:
            now = datetime.now()
            for job in self._jobs:
                if job["next_run"] <= now:
                    try:
                        if asyncio.iscoroutinefunction(job["callback"]):
                            await job["callback"]()
                        else:
                            job["callback"]()
                    except Exception as e:
                        logger.error("Job %s failed: %s", job["name"], e)
                    finally:
                        job["last_run"] = now
                        job["next_run"] = now + timedelta(seconds=job["interval"])

            await asyncio.sleep(1)
