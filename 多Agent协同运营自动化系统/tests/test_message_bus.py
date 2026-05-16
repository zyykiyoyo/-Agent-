import pytest
from models.message import Message, MessageType
from core.message_bus import MessageBus


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    bus = MessageBus()
    received = []

    async def handler(msg):
        received.append(msg)

    bus.subscribe(MessageType.SYSTEM, handler)
    msg = Message(type=MessageType.SYSTEM, sender="test", content={"key": "value"})
    await bus.publish(msg)

    assert len(received) == 1
    assert received[0].sender == "test"
    assert received[0].content["key"] == "value"


@pytest.mark.asyncio
async def test_agent_subscription():
    bus = MessageBus()
    received = []

    async def handler(msg):
        received.append(msg)

    bus.subscribe_agent("agent1", handler)
    msg = Message(type=MessageType.CUSTOM, sender="orchestrator", recipient="agent1", content={})
    await bus.publish(msg)

    assert len(received) == 1


@pytest.mark.asyncio
async def test_request_response():
    bus = MessageBus()

    async def responder(msg):
        reply = msg.reply({"status": "ok"})
        await bus.publish(reply)

    bus.subscribe(MessageType.QUERY, responder)

    req = Message(type=MessageType.QUERY, sender="test", recipient="system", content={"query": "ping"})
    response = await bus.request(req, timeout=5)

    assert response is not None
    assert response.content["status"] == "ok"


@pytest.mark.asyncio
async def test_history():
    bus = MessageBus()
    for i in range(5):
        await bus.publish(Message(type=MessageType.SYSTEM, sender=f"sender-{i}", content={}))

    history = bus.get_history(limit=3)
    assert len(history) == 3
