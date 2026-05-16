from __future__ import annotations
import asyncio
import logging
import signal
from datetime import datetime
from typing import Optional

from core.message_bus import MessageBus
from core.task_manager import TaskManager
from core.scheduler import Scheduler
from storage.database import JSONDatabase

from agents.orchestrator import OrchestratorAgent
from agents.monitor import MonitorAgent
from agents.analyzer import AnalyzerAgent
from agents.planner import PlannerAgent
from agents.executor import ExecutorAgent
from agents.reporter import ReporterAgent

logger = logging.getLogger(__name__)


class AgentSystem:
    """Main system orchestrating all agents and services."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._start_time = datetime.now()
        self._running = False

        # Core infrastructure
        self._message_bus = MessageBus()
        self._task_manager = TaskManager(self._message_bus)
        self._scheduler = Scheduler()
        self._database = JSONDatabase(self.config.get("data_dir", "data"))

        # Agents
        self._agents: dict[str, BaseAgent] = {}
        self._dashboard = None

    async def startup(self):
        self._running = True
        logger.info("Starting Multi-Agent System...")

        # Create agents
        self._agents["orchestrator"] = OrchestratorAgent(
            "orchestrator", self._message_bus, self._task_manager
        )
        self._agents["monitor"] = MonitorAgent(
            "monitor", self._message_bus, self._task_manager
        )
        self._agents["analyzer"] = AnalyzerAgent(
            "analyzer", self._message_bus, self._task_manager
        )
        self._agents["planner"] = PlannerAgent(
            "planner", self._message_bus, self._task_manager
        )
        self._agents["executor"] = ExecutorAgent(
            "executor", self._message_bus, self._task_manager
        )
        self._agents["reporter"] = ReporterAgent(
            "reporter", self._message_bus, self._task_manager
        )

        # Start all agents
        for name, agent in self._agents.items():
            await agent.start()
            logger.info("Agent started: %s", name)

        # Set up scheduled jobs
        self._setup_scheduled_jobs()

        # Start scheduler
        await self._scheduler.start()

        logger.info("All agents started successfully")

    def _setup_scheduled_jobs(self):
        orchestrator = self._agents.get("orchestrator")
        monitor = self._agents.get("monitor")
        reporter = self._agents.get("reporter")

        if monitor:
            self._scheduler.add_job(
                "collect-metrics", self._scheduled_collect_metrics,
                interval_seconds=self.config.get("metrics_interval", 60),
                start_delay=5,
            )
        if reporter and orchestrator:
            self._scheduler.add_job(
                "status-report", self._scheduled_status_report,
                interval_seconds=self.config.get("report_interval", 300),
                start_delay=10,
            )
        if orchestrator:
            self._scheduler.add_job(
                "health-check", self._scheduled_health_check,
                interval_seconds=self.config.get("health_check_interval", 120),
                start_delay=3,
            )

    async def _scheduled_collect_metrics(self):
        monitor = self._agents.get("monitor")
        if monitor:
            task = await self._task_manager.create_task(
                "collect_metrics", "Scheduled metrics collection",
                agent_type="monitor", source_agent="scheduler",
            )
            await monitor.execute_task(task.id, {"name": "collect_metrics"})

    async def _scheduled_status_report(self):
        orchestrator = self._agents.get("orchestrator")
        reporter = self._agents.get("reporter")
        if orchestrator and reporter:
            status = await orchestrator.get_system_status()
            metrics = {
                "active_agents": status.get("active_agents", 0),
                "active_tasks": status.get("tasks", {}).get("by_status", {}).get("RUNNING", 0),
                "completed_tasks": status.get("tasks", {}).get("by_status", {}).get("COMPLETED", 0),
                "failed_tasks": status.get("tasks", {}).get("by_status", {}).get("FAILED", 0),
                "overall_status": "healthy",
            }
            task = await self._task_manager.create_task(
                "daily_report", "Scheduled daily report",
                agent_type="reporter", source_agent="scheduler",
            )
            await reporter.execute_task(task.id, {"name": "daily_report", "metrics": metrics})

    async def _scheduled_health_check(self):
        monitor = self._agents.get("monitor")
        if monitor:
            task = await self._task_manager.create_task(
                "health_check", "Scheduled health check",
                agent_type="monitor", source_agent="scheduler",
            )
            await monitor.execute_task(task.id, {"name": "health_check"})

    async def execute_action(self, action_name: str) -> dict:
        """Execute an action triggered from the dashboard."""
        action_map = {
            "status": self._action_status,
            "health_check": self._action_health_check,
            "collect_metrics": self._action_collect_metrics,
            "daily_report": self._action_daily_report,
            "create_plan": self._action_create_plan,
            "run_analysis": self._action_run_analysis,
            "cleanup": self._action_cleanup,
        }
        handler = action_map.get(action_name)
        if not handler:
            return {"error": f"Unknown action: {action_name}"}
        return await handler()

    async def _action_status(self) -> dict:
        orchestrator = self._agents.get("orchestrator")
        status = await orchestrator.get_system_status() if orchestrator else {}
        uptime = (datetime.now() - self._start_time).total_seconds()
        return {"result": {**status, "uptime": round(uptime, 1)}}

    async def _action_health_check(self) -> dict:
        monitor = self._agents.get("monitor")
        if not monitor:
            return {"error": "Monitor agent not available"}
        task = await self._task_manager.create_task(
            "health_check", "Manual health check",
            agent_type="monitor", source_agent="dashboard",
        )
        await monitor.execute_task(task.id, {"name": "health_check"})
        return {"result": {"task_id": task.id, "status": "completed", "data": task.result or {}}}

    async def _action_collect_metrics(self) -> dict:
        monitor = self._agents.get("monitor")
        if not monitor:
            return {"error": "Monitor agent not available"}
        task = await self._task_manager.create_task(
            "collect_metrics", "Manual metrics collection",
            agent_type="monitor", source_agent="dashboard",
        )
        await monitor.execute_task(task.id, {"name": "collect_metrics"})
        return {"result": {"task_id": task.id, "metrics": task.result or {}}}

    async def _action_daily_report(self) -> dict:
        reporter = self._agents.get("reporter")
        orchestrator = self._agents.get("orchestrator")
        if not reporter or not orchestrator:
            return {"error": "Required agents not available"}
        status = await orchestrator.get_system_status()
        metrics = {
            "active_agents": status.get("active_agents", 0),
            "active_tasks": status.get("tasks", {}).get("by_status", {}).get("RUNNING", 0),
            "completed_tasks": status.get("tasks", {}).get("by_status", {}).get("COMPLETED", 0),
            "failed_tasks": status.get("tasks", {}).get("by_status", {}).get("FAILED", 0),
            "overall_status": "healthy",
        }
        task = await self._task_manager.create_task(
            "daily_report", "Manual daily report",
            agent_type="reporter", source_agent="dashboard",
        )
        await reporter.execute_task(task.id, {"name": "daily_report", "metrics": metrics})
        return {"result": {"task_id": task.id, "report": task.result or {}}}

    async def _action_create_plan(self) -> dict:
        planner = self._agents.get("planner")
        if not planner:
            return {"error": "Planner agent not available"}
        task = await self._task_manager.create_task(
            "create_plan", "Create operation plan",
            agent_type="planner", source_agent="dashboard",
        )
        await planner.execute_task(task.id, {
            "name": "create_plan",
            "goal": "System optimization and maintenance",
            "constraints": {"budget": "standard", "timeframe": "normal"},
        })
        return {"result": {"task_id": task.id, "plan": task.result or {}}}

    async def _action_run_analysis(self) -> dict:
        analyzer = self._agents.get("analyzer")
        if not analyzer:
            return {"error": "Analyzer agent not available"}
        import random
        values = [random.uniform(10, 100) for _ in range(30)]
        task = await self._task_manager.create_task(
            "trend_analysis", "Run data trend analysis",
            agent_type="analyzer", source_agent="dashboard",
        )
        await analyzer.execute_task(task.id, {
            "name": "trend_analysis",
            "values": values,
            "threshold": 2.0,
        })
        return {"result": {"task_id": task.id, "analysis": task.result or {}}}

    async def _action_cleanup(self) -> dict:
        executor = self._agents.get("executor")
        if not executor:
            return {"error": "Executor agent not available"}
        task = await self._task_manager.create_task(
            "cleanup", "System cleanup task",
            agent_type="executor", source_agent="dashboard",
        )
        await executor.execute_task(task.id, {"name": "cleanup", "target": "temporary"})
        return {"result": {"task_id": task.id, "cleanup": task.result or {}}}

    async def shutdown(self):
        self._running = False
        logger.info("Shutting down...")
        await self._scheduler.stop()
        for name, agent in reversed(list(self._agents.items())):
            await agent.stop()
        logger.info("System shutdown complete")
