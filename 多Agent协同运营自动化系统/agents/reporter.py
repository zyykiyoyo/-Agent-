from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from core.agent import BaseAgent
from models.task import Task, TaskStatus
from models.message import Message, MessageType
from tools.file_tools import FileTools
from tools.notification import NotificationTools

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    """Generates reports, summaries, dashboards, and status communications."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "reporter", message_bus, task_manager)
        self._file_tools = FileTools()
        self._notifier = NotificationTools()
        self._report_history: list[dict] = []

    async def start(self):
        await super().start()
        self.bus.subscribe(MessageType.QUERY, self._handle_query)
        logger.info("ReporterAgent started")

    async def _handle_query(self, message: Message):
        query = message.content.get("query", "")
        if query == "list_reports":
            await self.send_message(message.sender, {
                "reports": self._report_history[-10:],
            }, MessageType.RESPONSE)

    async def execute_task(self, task_id: str, task_data: dict):
        task_type = task_data.get("name", "report")

        try:
            if "daily" in task_type or "status" in task_type:
                result = await self._generate_daily_report(task_data)
            elif "alert" in task_type or "incident" in task_type:
                result = await self._generate_incident_report(task_data)
            elif "summary" in task_type or "summary" in task_type:
                result = await self._generate_summary(task_data)
            else:
                result = await self._generate_custom_report(task_data)

            await self.complete_task(task_id, result)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def _generate_daily_report(self, task_data: dict) -> dict:
        metrics = task_data.get("metrics", {})
        date = datetime.now().strftime("%Y-%m-%d")

        report_content = f"""# Daily Operations Report
**Date:** {date}
**Generated:** {datetime.now().strftime('%H:%M:%S')}

## Key Metrics
- Tasks Completed: {metrics.get('completed_tasks', 'N/A')}
- Active Tasks: {metrics.get('active_tasks', 'N/A')}
- Failed Tasks: {metrics.get('failed_tasks', 'N/A')}
- Active Agents: {metrics.get('active_agents', 'N/A')}

## System Health
- Status: {metrics.get('overall_status', 'Unknown')}
"""
        filepath = await self._file_tools.save_report(
            f"daily_report_{date}", report_content
        )

        report = {
            "type": "daily",
            "date": date,
            "filepath": filepath,
            "metrics": metrics,
        }
        self._report_history.append(report)
        return report

    async def _generate_incident_report(self, task_data: dict) -> dict:
        incident = task_data.get("incident", "Unknown incident")
        severity = task_data.get("severity", "info")
        details = task_data.get("details", "")

        report_content = f"""# Incident Report
**Incident:** {incident}
**Severity:** {severity.upper()}
**Timestamp:** {datetime.now().isoformat()}

## Details
{details}

## Actions Taken
1. Incident detected and logged
2. Relevant agents notified
3. Report generated
"""
        filepath = await self._file_tools.save_report(
            f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}", report_content
        )

        self._notifier.send_alert(
            f"Incident: {incident}", details, severity
        )

        report = {
            "type": "incident",
            "incident": incident,
            "severity": severity,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat(),
        }
        self._report_history.append(report)
        return report

    async def _generate_summary(self, task_data: dict) -> dict:
        data = task_data.get("data", {})
        title = task_data.get("title", "Summary Report")

        lines = [f"# {title}", f"**Generated:** {datetime.now().isoformat()}", ""]
        for key, value in data.items():
            lines.append(f"- **{key}:** {value}")

        report_content = "\n".join(lines)
        filepath = await self._file_tools.save_report(
            f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}", report_content
        )

        report = {"type": "summary", "title": title, "filepath": filepath}
        self._report_history.append(report)
        return report

    async def _generate_custom_report(self, task_data: dict) -> dict:
        title = task_data.get("title", "Custom Report")
        sections = task_data.get("sections", {})

        lines = [f"# {title}", f"**Generated:** {datetime.now().isoformat()}", ""]
        for section_title, content in sections.items():
            lines.append(f"## {section_title}")
            lines.append(str(content))
            lines.append("")

        report_content = "\n".join(lines)
        filepath = await self._file_tools.save_report(
            f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}", report_content
        )

        report = {"type": "custom", "title": title, "filepath": filepath}
        self._report_history.append(report)
        return report
