from __future__ import annotations
import csv
import json
import logging
from io import StringIO
from typing import Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)


class DataTools:
    """Data processing tools for agents."""

    @staticmethod
    def parse_json(text: str) -> Optional[dict]:
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("JSON parse error: %s", e)
            return None

    @staticmethod
    def parse_csv(text: str) -> Optional[list[dict]]:
        try:
            reader = csv.DictReader(StringIO(text))
            return list(reader)
        except Exception as e:
            logger.error("CSV parse error: %s", e)
            return None

    @staticmethod
    def compute_summary(data: list[dict], numeric_fields: list[str] = None) -> dict:
        summary = {"count": len(data), "fields": {}}
        if not data:
            return summary

        for key in data[0].keys():
            values = [row.get(key) for row in data if row.get(key) is not None]
            if not values:
                continue

            numeric = all(isinstance(v, (int, float)) for v in values)
            entry = {"non_null_count": len(values), "null_count": len(data) - len(values)}

            if numeric and numeric_fields and key in numeric_fields:
                nums = [float(v) for v in values]
                entry.update({
                    "min": min(nums), "max": max(nums),
                    "avg": sum(nums) / len(nums),
                    "sum": sum(nums),
                })
            elif not numeric:
                counter = Counter(values)
                entry.update({
                    "unique_values": len(counter),
                    "most_common": counter.most_common(5),
                })

            summary["fields"][key] = entry

        return summary

    @staticmethod
    def detect_anomalies(values: list[float], threshold: float = 2.0) -> list[dict]:
        import statistics
        if len(values) < 3:
            return []

        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        if stdev == 0:
            return []

        anomalies = []
        for i, v in enumerate(values):
            z_score = (v - mean) / stdev
            if abs(z_score) > threshold:
                anomalies.append({"index": i, "value": v, "z_score": round(z_score, 3)})
        return anomalies

    @staticmethod
    def trend_analysis(values: list[float], labels: list[str] = None) -> dict:
        if len(values) < 2:
            return {"trend": "insufficient_data"}

        changes = [values[i] - values[i - 1] for i in range(1, len(values))]
        avg_change = sum(changes) / len(changes)
        pct_changes = [
            ((values[i] - values[i - 1]) / values[i - 1] * 100) if values[i - 1] != 0 else 0
            for i in range(1, len(values))
        ]
        avg_pct_change = sum(pct_changes) / len(pct_changes) if pct_changes else 0

        if avg_pct_change > 5:
            trend = "rapid_growth"
        elif avg_pct_change > 1:
            trend = "growth"
        elif avg_pct_change < -5:
            trend = "rapid_decline"
        elif avg_pct_change < -1:
            trend = "decline"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "avg_change": round(avg_change, 3),
            "avg_pct_change": round(avg_pct_change, 3),
            "max_increase": max(changes) if changes else 0,
            "max_decrease": min(changes) if changes else 0,
        }
