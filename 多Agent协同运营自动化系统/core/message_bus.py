from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from typing import Callable, Coroutine, Optional

from models.message import Message, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    """Central message bus for inter-agent communication."""

    def __init__(self):
        self._subscribers: dict[MessageType, list[Callable]] = defaultdict(list)
        self._agent_subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Message] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(self, msg_type: MessageType, callback: Callable) -> None:
        self._subscribers[msg_type].append(callback)

    def subscribe_agent(self, agent_name: str, callback: Callable) -> None:
        self._agent_subscribers[agent_name].append(callback)

    def unsubscribe(self, msg_type: MessageType, callback: Callable) -> None:
        if callback in self._subscribers.get(msg_type, []):
            self._subscribers[msg_type].remove(callback)

    async def publish(self, message: Message) -> list[Coroutine]:
        async with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        tasks = []

        # Notify type-based subscribers
        for callback in self._subscribers.get(message.type, []):
            tasks.append(self._safe_dispatch(callback, message))

        # Notify agent-specific subscribers
        for callback in self._agent_subscribers.get(message.recipient, []):
            tasks.append(self._safe_dispatch(callback, message))

        # Also notify agents subscribed to receive all messages of this type
        for callback in self._subscribers.get(MessageType.CUSTOM, []):
            tasks.append(self._safe_dispatch(callback, message))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_dispatch(self, callback, message):
        try:
            import inspect
            if inspect.iscoroutinefunction(callback):
                await callback(message)
            else:
                callback(message)
        except Exception as e:
            logger.error("Error dispatching message %s to %s: %s", message.id, callback.__name__, e)

    def get_history(self, limit: int = 50) -> list[Message]:
        return self._history[-limit:]

    async def request(self, message: Message, timeout: float = 30.0) -> Optional[Message]:
        """Send a request and wait for a response with the same correlation_id."""
        future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def response_handler(msg: Message) -> None:
            if msg.correlation_id == message.id and not future.done():
                future.set_result(msg)

        self.subscribe(MessageType.RESPONSE, response_handler)
        await self.publish(message)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Request %s timed out after %ss", message.id, timeout)
            return None
        finally:
            self.unsubscribe(MessageType.RESPONSE, response_handler)
