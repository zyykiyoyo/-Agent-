from __future__ import annotations
import uuid
from enum import Enum, auto
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


class MessageType(Enum):
    TASK_ASSIGN = auto()
    TASK_RESULT = auto()
    TASK_PROGRESS = auto()
    AGENT_REGISTER = auto()
    AGENT_HEARTBEAT = auto()
    AGENT_STATUS = auto()
    QUERY = auto()
    RESPONSE = auto()
    ALERT = auto()
    REPORT = auto()
    SYSTEM = auto()
    CUSTOM = auto()


@dataclass
class Message:
    id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    type: MessageType = MessageType.CUSTOM
    sender: str = ""
    recipient: str = ""  # empty means broadcast
    content: dict = field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def reply(self, content: dict, msg_type: MessageType = MessageType.RESPONSE) -> Message:
        return Message(
            type=msg_type,
            sender=self.recipient,
            recipient=self.sender,
            content=content,
            correlation_id=self.id,
        )
