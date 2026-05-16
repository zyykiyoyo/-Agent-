from __future__ import annotations
import asyncio
import logging
from typing import Optional

from models.task import Task, TaskPriority, TaskStatus
from models.message import Message, MessageType
from core.message_bus import MessageBus
from core.task_manager import TaskManager

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents in the system."""

    def __init__(self, name: str, agent_type: str, message_bus: MessageBus, task_manager: TaskManager):
        self.name = name
        self.agent_type = agent_type
        self.bus = message_bus
        self.task_manager = task_manager
        self._running = False
        self._active_task: Optional[Task] = None

    async def start(self):
        """Start the agent, subscribe to messages."""
        self._running = True

        # Register with the message bus
        await self.bus.publish(
            Message(type=MessageType.AGENT_REGISTER, sender=self.name, content={
                "name": self.name, "type": self.agent_type
            })
        )

        self.bus.subscribe_agent(self.name, self._handle_direct_message)

        logger.info("Agent %s (%s) started", self.name, self.agent_type)

    async def stop(self):
        self._running = False
        logger.info("Agent %s stopped", self.name)

    async def _handle_task_assign(self, message):
        """Receive a task assignment from an orchestrator."""
        task_data = message.content
        if task_data.get("agent_type") and task_data["agent_type"] != self.agent_type:
            return

        task_id = task_data["task_id"]
        await self.task_manager.assign_task(task_id, self.name)
        await self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)
        await self.execute_task(task_id, task_data)

    async def _handle_direct_message(self, message):
        """Handle direct messages sent to this agent."""
        pass

    async def execute_task(self, task_id: str, task_data: dict):
        """Execute a task. Override in subclasses."""
        raise NotImplementedError

    async def send_message(self, recipient: str, content: dict, msg_type: MessageType = MessageType.CUSTOM):
        msg = Message(type=msg_type, sender=self.name, recipient=recipient, content=content)
        await self.bus.publish(msg)

    async def broadcast(self, content: dict, msg_type: MessageType = MessageType.CUSTOM):
        msg = Message(type=msg_type, sender=self.name, content=content)
        await self.bus.publish(msg)

    async def create_sub_task(
        self, name: str, description: str, agent_type: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        parent_task_id: str = None
    ) -> Task:
        return await self.task_manager.create_task(
            name=name, description=description,
            priority=priority, agent_type=agent_type,
            source_agent=self.name, parent_task_id=parent_task_id,
        )

    async def complete_task(self, task_id: str, result: dict = None):
        await self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED, result=result)

    async def fail_task(self, task_id: str, error: str):
        await self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error=error)

    async def report_progress(self, task_id: str, progress: float, message: str = ""):
        await self.bus.publish(Message(
            type=MessageType.TASK_PROGRESS, sender=self.name, content={
                "task_id": task_id, "progress": progress, "message": message,
            }
        ))
