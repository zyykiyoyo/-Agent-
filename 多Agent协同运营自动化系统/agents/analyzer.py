from __future__ import annotations
import asyncio
import logging

from core.agent import BaseAgent
from models.task import Task, TaskStatus
from models.message import Message, MessageType
from tools.data_tools import DataTools

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    """Analyzes data, detects patterns, generates insights and predictions."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "analyzer", message_bus, task_manager)
        self._data_tools = DataTools()

    async def start(self):
        await super().start()
        self.bus.subscribe(MessageType.QUERY, self._handle_query)
        logger.info("AnalyzerAgent started")

    async def _handle_query(self, message: Message):
        query = message.content.get("query", "")
        data = message.content.get("data")

        if query == "analyze_trend" and data:
            result = self._data_tools.trend_analysis(data)
            await self.send_message(message.sender, {"result": result}, MessageType.RESPONSE)
        elif query == "detect_anomalies" and data:
            result = self._data_tools.detect_anomalies(data)
            await self.send_message(message.sender, {"result": result}, MessageType.RESPONSE)
        elif query == "summarize" and data:
            fields = message.content.get("numeric_fields")
            result = self._data_tools.compute_summary(data, fields)
            await self.send_message(message.sender, {"result": result}, MessageType.RESPONSE)

    async def execute_task(self, task_id: str, task_data: dict):
        task_type = task_data.get("name", "analyze")

        try:
            if "trend" in task_type or "analyze" in task_type:
                result = await self._analyze_data(task_data)
            elif "anomaly" in task_type or "detect" in task_type:
                result = await self._detect_anomalies(task_data)
            elif "report" in task_type or "summarize" in task_type:
                result = await self._generate_insights(task_data)
            else:
                result = {"message": f"Unknown analysis type: {task_type}"}

            await self.complete_task(task_id, result)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def _analyze_data(self, task_data: dict) -> dict:
        values = task_data.get("values", [])
        if not values:
            return {"error": "No data provided"}

        labels = task_data.get("labels")
        trend = self._data_tools.trend_analysis(values, labels)

        summary = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "average": round(sum(values) / len(values), 2),
            "trend_analysis": trend,
        }
        return summary

    async def _detect_anomalies(self, task_data: dict) -> dict:
        values = task_data.get("values", [])
        threshold = task_data.get("threshold", 2.0)

        anomalies = self._data_tools.detect_anomalies(values, threshold)
        return {
            "total_values": len(values),
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
            "threshold_used": threshold,
        }

    async def _generate_insights(self, task_data: dict) -> dict:
        data = task_data.get("data", [])
        fields = task_data.get("numeric_fields")

        summary = self._data_tools.compute_summary(data, fields)

        insights = []
        for field, info in summary.get("fields", {}).items():
            if "trend" in info:
                trend = info["trend"]
                if trend in ("rapid_growth", "growth"):
                    insights.append(f"'{field}' is showing an upward trend")
                elif trend in ("rapid_decline", "decline"):
                    insights.append(f"'{field}' is showing a downward trend — may need attention")

        return {
            "data_summary": summary,
            "insights": insights,
            "insight_count": len(insights),
        }
