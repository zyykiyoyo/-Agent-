import pytest
from core.message_bus import MessageBus
from core.task_manager import TaskManager
from agents.orchestrator import OrchestratorAgent
from agents.monitor import MonitorAgent
from agents.analyzer import AnalyzerAgent
from agents.executor import ExecutorAgent
from agents.reporter import ReporterAgent


@pytest.mark.asyncio
async def test_orchestrator_agent_registration():
    bus = MessageBus()
    tm = TaskManager(bus)
    orch = OrchestratorAgent("test-orch", bus, tm)
    await orch.start()

    status = await orch.get_system_status()
    assert "agents" in status
    assert "tasks" in status

    await orch.stop()


@pytest.mark.asyncio
async def test_monitor_health_check():
    bus = MessageBus()
    tm = TaskManager(bus)
    monitor = MonitorAgent("test-mon", bus, tm)
    await monitor.start()

    task = await tm.create_task("health_check", "Test health check", agent_type="monitor")
    await monitor.execute_task(task.id, {"name": "health_check"})

    result = await tm.get_task(task.id)
    assert result is not None
    assert result.result is not None
    assert "metrics" in result.result

    await monitor.stop()


@pytest.mark.asyncio
async def test_analyzer_trend_analysis():
    bus = MessageBus()
    tm = TaskManager(bus)
    analyzer = AnalyzerAgent("test-ana", bus, tm)
    await analyzer.start()

    values = [10, 20, 30, 40, 50]
    task = await tm.create_task("trend_analysis", "Test trend analysis", agent_type="analyzer")
    await analyzer.execute_task(task.id, {"name": "trend_analysis", "values": values})

    result = await tm.get_task(task.id)
    assert result is not None
    assert result.result is not None
    assert "trend_analysis" in result.result
    assert result.result["trend_analysis"]["trend"] in ("growth", "rapid_growth")

    await analyzer.stop()


@pytest.mark.asyncio
async def test_executor_generic():
    bus = MessageBus()
    tm = TaskManager(bus)
    executor = ExecutorAgent("test-exec", bus, tm)
    await executor.start()

    task = await tm.create_task("execute", "Test execution", agent_type="executor")
    await executor.execute_task(task.id, {"name": "execute", "command": "test_cmd"})

    result = await tm.get_task(task.id)
    assert result is not None
    assert result.result is not None
    assert result.result.get("status") == "executed"

    await executor.stop()


@pytest.mark.asyncio
async def test_reporter_daily_report():
    bus = MessageBus()
    tm = TaskManager(bus)
    reporter = ReporterAgent("test-rep", bus, tm)
    await reporter.start()

    metrics = {
        "active_agents": 3,
        "active_tasks": 5,
        "completed_tasks": 10,
        "failed_tasks": 1,
        "overall_status": "healthy",
    }
    task = await tm.create_task("daily_report", "Test report", agent_type="reporter")
    await reporter.execute_task(task.id, {"name": "daily_report", "metrics": metrics})

    result = await tm.get_task(task.id)
    assert result is not None
    assert result.result is not None
    assert result.result.get("type") == "daily"

    await reporter.stop()
