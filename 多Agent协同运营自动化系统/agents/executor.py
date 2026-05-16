from __future__ import annotations
import asyncio
import logging
import random

from core.agent import BaseAgent
from models.task import Task, TaskStatus
from models.message import Message, MessageType
from tools.web_tools import WebTools
from tools.file_tools import FileTools

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """Action executor: carries out operational tasks, automations, and commands."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "executor", message_bus, task_manager)
        self._web_tools = WebTools()
        self._file_tools = FileTools()

    async def start(self):
        await super().start()
        logger.info("ExecutorAgent started")

    async def execute_task(self, task_id: str, task_data: dict):
        task_type = task_data.get("name", "execute")

        try:
            if "deploy" in task_type or "release" in task_type:
                result = await self._execute_deploy(task_data)
            elif "backup" in task_type:
                result = await self._execute_backup(task_data)
            elif "cleanup" in task_type or "maintain" in task_type:
                result = await self._execute_cleanup(task_data)
            elif "notify" in task_type or "send" in task_type:
                result = await self._execute_notification(task_data)
            elif "process" in task_type or "batch" in task_type:
                result = await self._execute_batch(task_data)
            else:
                result = await self._execute_generic(task_data)

            await self.complete_task(task_id, result)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def _execute_deploy(self, task_data: dict) -> dict:
        target = task_data.get("target", "unknown")
        version = task_data.get("version", "v1.0.0")

        steps = [
            {"step": "validate", "status": "passed"},
            {"step": "build", "status": "completed", "output": f"{target}-{version}.zip"},
            {"step": "test", "status": "passed", "tests_passed": 42, "tests_failed": 0},
        ]

        success = random.random() > 0.1  # 90% success rate
        if success:
            steps.append({"step": "deploy", "status": "completed", "target": target})
            return {
                "action": "deploy",
                "target": target,
                "version": version,
                "success": True,
                "steps": steps,
            }
        else:
            return {
                "action": "deploy",
                "success": False,
                "error": "Deployment validation failed",
                "steps": steps,
            }

    async def _execute_backup(self, task_data: dict) -> dict:
        source = task_data.get("source", "/data")
        dest = task_data.get("destination", "/backup")

        await self.report_progress(self._active_task.id if self._active_task else "", 0.5)
        await asyncio.sleep(0.1)  # Simulate work

        return {
            "action": "backup",
            "source": source,
            "destination": dest,
            "size_mb": round(random.uniform(10, 500), 2),
            "success": True,
        }

    async def _execute_cleanup(self, task_data: dict) -> dict:
        target = task_data.get("target", "temp")
        files_removed = random.randint(0, 50)
        space_freed_mb = round(random.uniform(0, 200), 2)
        return {
            "action": "cleanup",
            "target": target,
            "files_removed": files_removed,
            "space_freed_mb": space_freed_mb,
            "success": True,
        }

    async def _execute_notification(self, task_data: dict) -> dict:
        channel = task_data.get("channel", "console")
        title = task_data.get("title", "Notification")
        message = task_data.get("message", "")

        logger.info("[NOTIFY:%s] %s: %s", channel, title, message)
        return {
            "action": "notify",
            "channel": channel,
            "title": title,
            "delivered": True,
        }

    async def _execute_batch(self, task_data: dict) -> dict:
        items = task_data.get("items", [])
        operation = task_data.get("operation", "process")
        processed = 0
        errors = 0

        for item in items:
            try:
                # Simulate processing
                processed += 1
            except Exception:
                errors += 1

        return {
            "action": "batch",
            "operation": operation,
            "total": len(items),
            "processed": processed,
            "errors": errors,
        }

    async def _execute_generic(self, task_data: dict) -> dict:
        command = task_data.get("command", "noop")
        params = task_data.get("params", {})
        return {
            "action": command,
            "params": params,
            "status": "executed",
            "result": f"Command '{command}' completed successfully",
        }
