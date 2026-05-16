from __future__ import annotations
import asyncio
import logging
import random
from datetime import datetime

from core.agent import BaseAgent
from models.task import Task, TaskStatus
from models.message import Message, MessageType
from tools.web_tools import WebTools
from tools.notification import NotificationTools

logger = logging.getLogger(__name__)


class MonitorAgent(BaseAgent):
    """Monitors system health, metrics, endpoints, and generates alerts."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "monitor", message_bus, task_manager)
        self._web_tools = WebTools()
        self._notifier = NotificationTools()
        self._monitored_endpoints: list[str] = []
        self._metrics_history: list[dict] = []
        self._max_history = 1000

    async def start(self):
        await super().start()
        self.bus.subscribe(MessageType.QUERY, self._handle_query)
        logger.info("MonitorAgent started")

    async def _handle_query(self, message: Message):
        query = message.content.get("query", "")
        if query == "system_health":
            await self.send_message(message.sender, {
                "status": "healthy",
                "metrics": self._get_latest_metrics(),
                "alert_count": len(self._notifier.get_alert_history()),
            }, MessageType.RESPONSE)

    async def execute_task(self, task_id: str, task_data: dict):
        task_type = task_data.get("name", "check")

        try:
            if "health" in task_type or "ping" in task_type:
                result = await self._run_health_check(task_data)
            elif "metric" in task_type or "collect" in task_type:
                result = await self._collect_metrics(task_data)
            elif "endpoint" in task_type:
                result = await self._check_endpoints(task_data)
            else:
                result = {"message": f"Unknown monitor task: {task_type}"}

            await self.complete_task(task_id, result)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def _run_health_check(self, task_data: dict) -> dict:
        checks = {
            "memory": random.uniform(40, 85),
            "cpu": random.uniform(10, 70),
            "disk": random.uniform(30, 90),
            "uptime_hours": random.uniform(48, 720),
        }

        alerts = []
        if checks["memory"] > 80:
            alerts.append(self._notifier.send_alert(
                "High Memory Usage", f"Memory at {checks['memory']:.1f}%",
                "warning"
            ))
        if checks["disk"] > 85:
            alerts.append(self._notifier.send_alert(
                "High Disk Usage", f"Disk at {checks['disk']:.1f}%",
                "warning"
            ))

        return {"status": "healthy" if not alerts else "degraded", "metrics": checks, "alerts": alerts}

    async def _collect_metrics(self, task_data: dict) -> dict:
        metric = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": round(random.uniform(10, 90), 2),
            "memory_usage": round(random.uniform(30, 95), 2),
            "request_count": random.randint(100, 10000),
            "error_rate": round(random.uniform(0, 5), 3),
            "response_time_ms": round(random.uniform(50, 500), 2),
        }
        self._metrics_history.append(metric)
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]
        return metric

    async def _check_endpoints(self, task_data: dict) -> dict:
        urls = task_data.get("urls", self._monitored_endpoints)
        if not urls:
            return {"message": "No endpoints configured", "endpoints": []}

        results = await self._web_tools.check_multiple_urls(urls)
        failed = [r for r in results if not r["reachable"]]

        for f in failed:
            self._notifier.send_alert(
                "Endpoint Down", f"{f['url']} is unreachable",
                "critical", metadata=f
            )

        return {"endpoints_checked": len(results), "healthy": len(results) - len(failed), "failed": failed}

    def add_endpoint(self, url: str):
        self._monitored_endpoints.append(url)

    def _get_latest_metrics(self) -> dict:
        return self._metrics_history[-1] if self._metrics_history else {}
