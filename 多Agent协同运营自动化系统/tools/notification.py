from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationTools:
    """Notification and alerting tools for agents."""

    def __init__(self):
        self._alert_history: list[dict] = []

    def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channel: str = "console",
        metadata: dict = None,
    ) -> dict:
        alert = {
            "title": title,
            "message": message,
            "severity": severity,
            "channel": channel,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._alert_history.append(alert)

        level_map = {"info": "INFO", "warning": "WARNING", "error": "ERROR", "critical": "CRITICAL"}
        log_level = level_map.get(severity, "INFO")
        logger.log(
            getattr(logging, log_level, logging.INFO),
            "[%s] %s: %s", severity.upper(), title, message,
        )
        return alert

    def get_alert_history(self, limit: int = 20, severity: Optional[str] = None) -> list[dict]:
        alerts = self._alert_history
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        return alerts[-limit:]

    def generate_status_report(self, metrics: dict) -> str:
        lines = [
            f"# System Status Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Overview",
        ]

        if metrics.get("overall_status"):
            lines.append(f"- **Status:** {metrics['overall_status']}")

        lines.extend([
            f"- **Active Tasks:** {metrics.get('active_tasks', 'N/A')}",
            f"- **Completed Tasks:** {metrics.get('completed_tasks', 'N/A')}",
            f"- **Failed Tasks:** {metrics.get('failed_tasks', 'N/A')}",
            f"- **Active Agents:** {metrics.get('active_agents', 'N/A')}",
            "",
        ])

        if metrics.get("alerts"):
            lines.append("## Recent Alerts")
            for alert in metrics["alerts"][-5:]:
                sev = alert.get("severity", "info")
                icon = {"critical": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}
                lines.append(f"- {icon.get(sev, '•')} [{sev.upper()}] {alert.get('title', '')}")

        return "\n".join(lines)
