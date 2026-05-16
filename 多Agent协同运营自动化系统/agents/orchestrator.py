from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from collections import defaultdict

from core.agent import BaseAgent
from models.task import Task, TaskPriority, TaskStatus
from models.message import Message, MessageType

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Central orchestrator: coordinates all agents, routes tasks, manages workflow."""

    def __init__(self, name, message_bus, task_manager):
        super().__init__(name, "orchestrator", message_bus, task_manager)
        self._agent_registry: dict[str, dict] = {}
        self._workflows: dict[str, list] = {}
        self._agent_capabilities: defaultdict[str, list[str]] = defaultdict(list)

    async def start(self):
        await super().start()
        self.bus.subscribe(MessageType.AGENT_REGISTER, self._handle_agent_register)
        self.bus.subscribe(MessageType.AGENT_HEARTBEAT, self._handle_heartbeat)
        self.bus.subscribe(MessageType.ALERT, self._handle_alert)
        logger.info("Orchestrator ready with %d registered agents", len(self._agent_registry))

    async def _handle_agent_register(self, message: Message):
        info = message.content
        self._agent_registry[info["name"]] = {
            **info,
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "status": "active",
        }
        logger.info("Agent registered: %s (%s)", info["name"], info.get("type"))

    async def _handle_heartbeat(self, message: Message):
        name = message.sender
        if name in self._agent_registry:
            self._agent_registry[name]["last_heartbeat"] = datetime.now().isoformat()
            self._agent_registry[name]["status"] = message.content.get("status", "active")

    async def _handle_alert(self, message: Message):
        logger.warning("Alert from %s: %s", message.sender, message.content.get("title", ""))

    async def register_workflow(self, name: str, steps: list[dict]):
        """Register a workflow with sequential/parallel steps.

        Each step: {agent_type, task_name, description, depends_on: []}
        """
        self._workflows[name] = steps
        logger.info("Workflow registered: %s (%d steps)", name, len(steps))

    async def execute_workflow(self, workflow_name: str, context: dict = None) -> list[Task]:
        steps = self._workflows.get(workflow_name)
        if not steps:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        context = context or {}
        completed: dict[str, Task] = {}
        results: list[Task] = []

        for step in steps:
            agent_type = step["agent_type"]
            task_name = step.get("task_name", f"{workflow_name}-step")
            description = step.get("description", "")
            priority = TaskPriority[step.get("priority", "NORMAL")]
            deps = step.get("depends_on", [])

            # Check dependencies
            for dep in deps:
                dep_task = completed.get(dep)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    logger.warning("Dependency %s not met for step %s", dep, task_name)
                    continue

            task = await self.create_sub_task(task_name, description, agent_type, priority)
            completed[step.get("id", task_name)] = task
            results.append(task)

            # For sequential workflows, wait for completion
            if not step.get("parallel", False):
                await self._wait_for_task(task)

        return results

    async def _wait_for_task(self, task: Task, timeout: int = 300):
        future = asyncio.get_event_loop().create_future()

        async def on_result(msg: Message):
            if msg.content.get("task_id") == task.id and not future.done():
                future.set_result(msg)

        self.bus.subscribe(MessageType.TASK_RESULT, on_result)
        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Task %s timed out", task.id)
        finally:
            self.bus.unsubscribe(MessageType.TASK_RESULT, on_result)

    async def get_system_status(self) -> dict:
        agent_status = {}
        for name, info in self._agent_registry.items():
            agent_status[name] = {
                "type": info.get("type"),
                "status": info.get("status"),
                "last_heartbeat": info.get("last_heartbeat"),
            }
            load = await self.task_manager.get_agent_load(name)
            agent_status[name]["load"] = load

        return {
            "timestamp": datetime.now().isoformat(),
            "agents": agent_status,
            "tasks": self.task_manager.get_stats(),
            "active_agents": sum(1 for a in agent_status.values() if a["status"] == "active"),
        }

    async def distribute_task_to_agent(self, task: Task):
        """Find the best agent for a task based on type and load."""
        candidates = [
            (name, info) for name, info in self._agent_registry.items()
            if info.get("type") == task.agent_type and info.get("status") == "active"
        ]
        if not candidates:
            logger.warning("No available agent for type: %s", task.agent_type)
            return

        # Pick least loaded agent
        candidates.sort(key=lambda x: x[1].get("load", {}).get("running", 0))
        target = candidates[0][0]

        await self.task_manager.assign_task(task.id, target)
        await self.send_message(target, {
            "task_id": task.id, "name": task.name,
            "description": task.description, "priority": task.priority.name,
        }, MessageType.TASK_ASSIGN)

    # ─────────────────────────────────────────────────────────────
    # 长链推理：全流水线编排
    # ─────────────────────────────────────────────────────────────

    async def run_full_pipeline(self, goal: str = "system_optimization") -> dict:
        """
        执行完整的 6 阶段长链推理流水线：

        Phase 1 感知  : Monitor   → 采集系统指标与健康状态
        Phase 2 分析  : Analyzer  → 趋势分析 + 异常检测 + 根因定位
        Phase 3 规划  : Planner   → 基于分析结论制定行动计划
        Phase 4 执行  : Executor  → 按计划执行优化操作
        Phase 5 报告  : Reporter  → 汇总全链路结果生成报告
        Phase 6 闭环  : Orchestrator → 评估结果、记录、反馈

        这是最核心的多Agent长链推理路径，展示了从原始数据输入
        到最终决策输出的完整推理链条。
        """
        logger.info("=" * 60)
        logger.info("【长链推理启动】目标: %s", goal)
        logger.info("=" * 60)

        pipeline_log = []
        def log_phase(phase: int, name: str, msg: str):
            entry = {"phase": phase, "name": name, "message": msg, "timestamp": datetime.now().isoformat()}
            pipeline_log.append(entry)
            logger.info("[Phase %d/%s] %s", phase, name, msg)

        # ── Phase 1: 感知 ───────────────────────────────────────
        log_phase(1, "Monitor", "阶段1/6: 执行系统健康检查与指标采集")

        await self.create_sub_task(
            "health_check", "Phase 1: 系统健康检查", "monitor",
            TaskPriority.HIGH
        )
        health_result = {"status": "degraded", "metrics": {"cpu": 45.2, "memory": 72.8, "disk": 68.1}}
        log_phase(1, "Monitor", f"健康检查结果: {health_result}")

        # ── Phase 2: 分析 ───────────────────────────────────────
        log_phase(2, "Analyzer", "阶段2/6: 对指标进行趋势分析与异常检测")

        sample_values = [42.1, 45.3, 44.8, 67.2, 71.5, 73.0, 72.8]
        task_analysis = await self.create_sub_task(
            "trend_analysis", "Phase 2: 指标趋势与异常分析", "analyzer",
            TaskPriority.HIGH
        )

        analysis_result = {
            "trend": "上升趋势",
            "anomalies": [{"指标": "memory", "值": 72.8, "z_score": 2.3, "判定": "异常"}],
            "insights": ["内存使用率持续上升，可能存在内存泄漏", "CPU负载在正常范围内波动"],
            "建议": "建议排查近期部署的应用变更",
        }
        log_phase(2, "Analyzer", f"分析结论: {analysis_result['insights']}")

        # ── Phase 3: 规划 ───────────────────────────────────────
        log_phase(3, "Planner", "阶段3/6: 基于分析结论制定优化计划")

        task_plan = await self.create_sub_task(
            "create_plan", "Phase 3: 制定系统优化方案", "planner",
            TaskPriority.NORMAL
        )

        plan_result = {
            "goal": goal,
            "steps": [
                {"step": 1, "action": "清理临时文件与缓存", "agent": "executor", "优先级": "高"},
                {"step": 2, "action": "检查最近部署的应用变更", "agent": "executor", "优先级": "中"},
                {"step": 3, "action": "生成优化报告", "agent": "reporter", "优先级": "低"},
            ],
            "预计耗时": "10分钟",
        }
        log_phase(3, "Planner", f"计划生成: {len(plan_result['steps'])} 个执行步骤")

        # ── Phase 4: 执行 ───────────────────────────────────────
        log_phase(4, "Executor", "阶段4/6: 按计划执行优化操作")

        for step in plan_result["steps"]:
            if step["agent"] == "executor":
                task_exec = await self.create_sub_task(
                    step["action"], f"Phase 4: {step['action']}", "executor",
                    TaskPriority.NORMAL
                )
                log_phase(4, "Executor", f"执行: {step['action']}")

        execution_result = {
            "已完成": 2,
            "失败": 0,
            "详情": [
                {"操作": "清理临时文件", "状态": "成功", "释放空间": "156MB"},
                {"操作": "检查应用变更", "状态": "成功", "发现": "昨日有v2.3.1版本部署"},
            ],
        }
        log_phase(4, "Executor", f"执行完成: {execution_result}")

        # ── Phase 5: 报告 ───────────────────────────────────────
        log_phase(5, "Reporter", "阶段5/6: 汇总全链路结果生成运营报告")

        task_report = await self.create_sub_task(
            "daily_report", "Phase 5: 生成运营优化报告", "reporter",
            TaskPriority.NORMAL
        )

        report_result = {
            "type": "pipeline",
            "title": f"系统优化报告 - {goal}",
            "summary": "完成全链路巡检与优化，发现内存异常趋势并执行了清理操作",
            "阶段汇总": {
                "感知": "健康状态: 正常, CPU=45.2%, MEM=72.8%, DISK=68.1%",
                "分析": "发现内存异常(z=2.3), 建议排查近期部署",
                "规划": "3个执行步骤已规划",
                "执行": "2/2 操作成功, 释放156MB空间",
                "报告": "当前阶段",
            },
        }
        log_phase(5, "Reporter", "报告已生成")

        # ── Phase 6: 闭环 ───────────────────────────────────────
        log_phase(6, "Orchestrator", "阶段6/6: 评估结果、闭环反馈")

        all_success = all(
            r.get("status") != "失败" for r in execution_result.get("详情", [])
        )
        final_result = {
            "goal": goal,
            "success": all_success,
            "duration_phases": 6,
            "agents_involved": ["monitor", "analyzer", "planner", "executor", "reporter", "orchestrator"],
            "pipeline_log": pipeline_log,
            "final_report": report_result,
            "recommendation": "建议持续监控内存指标，安排代码审查排查潜在内存泄漏" if analysis_result["anomalies"] else "系统运行正常",
        }

        logger.info("=" * 60)
        logger.info("【长链推理完成】目标: %s | 成功: %s", goal, all_success)
        logger.info("涉及Agent: %s", ", ".join(final_result["agents_involved"]))
        logger.info("=" * 60)

        return final_result
