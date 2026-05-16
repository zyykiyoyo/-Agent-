from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from core.agent import BaseAgent
from models.task import Task, TaskPriority, TaskStatus
from models.message import Message, MessageType

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Strategic planner: creates action plans, schedules tasks, optimizes workflows."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "planner", message_bus, task_manager)
        self._plans: dict[str, dict] = {}

    async def start(self):
        await super().start()
        self.bus.subscribe(MessageType.QUERY, self._handle_query)
        logger.info("PlannerAgent started")

    async def _handle_query(self, message: Message):
        query = message.content.get("query", "")
        if query == "get_plan":
            plan_id = message.content.get("plan_id")
            plan = self._plans.get(plan_id)
            await self.send_message(message.sender, {"plan": plan}, MessageType.RESPONSE)

    async def execute_task(self, task_id: str, task_data: dict):
        task_type = task_data.get("name", "plan")

        try:
            if "create" in task_type or "plan" in task_type:
                result = await self._create_plan(task_data)
            elif "optimize" in task_type:
                result = await self._optimize_schedule(task_data)
            elif "review" in task_type:
                result = await self._review_plan(task_data)
            else:
                result = {"message": f"Unknown planner task: {task_type}"}

            await self.complete_task(task_id, result)
        except Exception as e:
            await self.fail_task(task_id, str(e))

    async def _create_plan(self, task_data: dict) -> dict:
        goal = task_data.get("goal", "Unspecified goal")
        constraints = task_data.get("constraints", {})
        deadline = task_data.get("deadline", "No deadline")

        steps = []
        step_templates = [
            ("Research & Data Collection", "monitor"),
            ("Data Analysis", "analyzer"),
            ("Strategy Formulation", "planner"),
            ("Execution", "executor"),
            ("Reporting", "reporter"),
        ]

        for i, (step_name, agent_type) in enumerate(step_templates, 1):
            steps.append({
                "step": i,
                "name": step_name,
                "assigned_agent": agent_type,
                "status": "pending",
                "estimated_duration": f"{i * 30}min",
            })

        plan = {
            "id": f"plan-{asyncio.current_task().get_name()[:8] if asyncio.current_task() else 'unknown'}",
            "goal": goal,
            "created_at": datetime.now().isoformat(),
            "deadline": deadline,
            "constraints": constraints,
            "steps": steps,
            "total_steps": len(steps),
            "status": "created",
        }
        self._plans[plan["id"]] = plan

        # Create tasks for each step
        for step in steps:
            await self.create_sub_task(
                name=step["name"],
                description=f"Step {step['step']}: {step['name']} for '{goal}'",
                agent_type=step["assigned_agent"],
                priority=TaskPriority.NORMAL,
            )

        return plan

    async def _optimize_schedule(self, task_data: dict) -> dict:
        tasks_list = task_data.get("tasks", [])
        if not tasks_list:
            return {"message": "No tasks to optimize", "optimized": False}

        # Sort by priority then by creation time
        priority_order = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
        optimized = sorted(
            tasks_list,
            key=lambda t: (priority_order.get(t.get("priority", "NORMAL"), 99), t.get("created_at", "")),
        )

        return {
            "original_count": len(tasks_list),
            "optimized_schedule": [t.get("name", "Unnamed") for t in optimized],
            "estimated_completion": f"{len(optimized) * 30}min",
        }

    async def _review_plan(self, task_data: dict) -> dict:
        plan_id = task_data.get("plan_id")
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found", "plan_id": plan_id}

        completed = sum(1 for s in plan["steps"] if s["status"] == "completed")
        return {
            "plan_id": plan_id,
            "goal": plan["goal"],
            "progress": f"{completed}/{plan['total_steps']} steps completed",
            "completion_pct": round(completed / plan["total_steps"] * 100, 1) if plan["total_steps"] else 0,
            "status": plan["status"],
        }
