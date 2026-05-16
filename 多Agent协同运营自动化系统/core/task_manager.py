from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional

from models.task import Task, TaskStatus, TaskPriority
from models.message import Message, MessageType

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task lifecycle: creation, assignment, tracking, and completion."""

    def __init__(self, message_bus):
        self._bus = message_bus
        self._tasks: dict[str, Task] = {}
        self._agent_tasks: defaultdict[str, list[str]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def create_task(
        self,
        name: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        agent_type: str = "",
        source_agent: str = "",
        metadata: dict = None,
        parent_task_id: str = None,
    ) -> Task:
        task = Task(
            name=name,
            description=description,
            priority=priority,
            agent_type=agent_type,
            source_agent=source_agent,
            metadata=metadata or {},
            parent_task_id=parent_task_id,
        )
        async with self._lock:
            self._tasks[task.id] = task

        await self._bus.publish(Message(
            type=MessageType.TASK_ASSIGN,
            sender="task-manager",
            recipient=agent_type,
            content={"task_id": task.id, "name": name, "description": description, "priority": priority.name},
        ))
        logger.info("Task created: %s (%s) [%s]", task.id, name, priority.name)
        return task

    async def assign_task(self, task_id: str, agent_name: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.PENDING:
                return False
            task.status = TaskStatus.ASSIGNED
            task.agent_type = agent_name
            task.updated_at = datetime.now().isoformat()
            self._agent_tasks[agent_name].append(task_id)
        return True

    async def update_task_status(
        self, task_id: str, status: TaskStatus, result: dict = None, error: str = None
    ) -> Optional[Task]:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task.update_status(status, result, error)

        await self._bus.publish(Message(
            type=MessageType.TASK_RESULT,
            sender="task-manager",
            content={
                "task_id": task_id,
                "status": status.name,
                "result": result,
                "error": error,
            },
            correlation_id=task_id,
        ))
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def get_tasks(
        self, status: Optional[TaskStatus] = None, agent_type: str = "",
        limit: int = 50
    ) -> list[Task]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if agent_type:
            tasks = [t for t in tasks if t.agent_type == agent_type]
        tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        return tasks[:limit]

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                return False
            task.update_status(TaskStatus.CANCELLED)
        return True

    async def get_agent_load(self, agent_name: str) -> dict:
        async with self._lock:
            task_ids = self._agent_tasks.get(agent_name, [])
            running = sum(1 for tid in task_ids if self._tasks.get(tid) and self._tasks[tid].status == TaskStatus.RUNNING)
            pending = sum(1 for tid in task_ids if self._tasks.get(tid) and self._tasks[tid].status == TaskStatus.PENDING)
            return {"total": len(task_ids), "running": running, "pending": pending}

    def get_stats(self) -> dict:
        total = len(self._tasks)
        by_status = defaultdict(int)
        for t in self._tasks.values():
            by_status[t.status.name] += 1
        return {"total": total, "by_status": dict(by_status)}
