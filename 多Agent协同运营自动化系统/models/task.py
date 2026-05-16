from __future__ import annotations
import uuid
from enum import Enum, auto
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(Enum):
    PENDING = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class Task:
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    agent_type: str = ""
    source_agent: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_task_id: Optional[str] = None
    subtasks: list[Task] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "status": self.status.name,
            "agent_type": self.agent_type,
            "source_agent": self.source_agent,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_task_id": self.parent_task_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        task = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            priority=TaskPriority[data.get("priority", "NORMAL")],
            status=TaskStatus[data.get("status", "PENDING")],
            agent_type=data.get("agent_type", ""),
            source_agent=data.get("source_agent", ""),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            parent_task_id=data.get("parent_task_id"),
        )
        return task

    def add_subtask(self, task: Task) -> None:
        task.parent_task_id = self.id
        self.subtasks.append(task)

    def update_status(self, status: TaskStatus, result: Optional[dict] = None, error: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error
