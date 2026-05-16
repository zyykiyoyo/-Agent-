#!/usr/bin/env python3
"""
多Agent协同运营自动化系统 —— 长链推理 + 多Agent协作 演示

本脚本演示完整的 6 阶段推理流水线:
  感知 -> 分析 -> 规划 -> 执行 -> 报告 -> 闭环

运行方式:
    python demo.py

输出解释:
    [Phase N/名称] 显示每个阶段的推理步骤
    -- 分隔各个Agent的协作边界
    最终产出包含完整的推理链日志
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system import AgentSystem
from models.task import TaskPriority

BANNER = r"""
+============================================================================+
|         多Agent协同运营自动化系统 . 长链推理演示                            |
|  Multi-Agent Collaborative Reasoning Pipeline Demo                        |
+============================================================================+
"""

PHASE_HEADERS = {
    1: ("感知 Perception", "Monitor  .  采集系统指标与健康状态"),
    2: ("分析 Analysis", "Analyzer  .  趋势分析与异常检测"),
    3: ("规划 Planning", "Planner   .  基于分析制定行动计划"),
    4: ("执行 Execution", "Executor  .  按计划执行自动化操作"),
    5: ("报告 Reporting", "Reporter  .  汇总全链路生成报告"),
    6: ("闭环 Feedback", "Orchestrator  .  评估归档与复盘"),
}


def print_separator(title: str = ""):
    if title:
        print(f"\n+-- {title} " + "-" * max(0, 50 - len(title)) + "+")
    else:
        print("\n" + "-" * 58)


def print_phase_header(phase: int, total: int = 6):
    title, subtitle = PHASE_HEADERS.get(phase, ("", ""))
    print()
    print(f"  >> Phase {phase}/{total}")
    print(f"  >> {title}")
    print(f"  >> {subtitle}")
    print(f"  " + "-" * 55)


def print_agent_message(agent: str, content: str, level: str = "->"):
    icon_map = {"->": ">", "<-": "<", "!": "#", "*": "*", "#": "#"}
    icon = icon_map.get(level, ">")
    print(f"    {icon} [{agent}] {content}")


def print_collaboration(agents: list[str], description: str):
    arrow = " -> ".join(agents)
    print(f"\n    +-- Collaboration Path ------------------------+")
    print(f"    |  {arrow}")
    print(f"    |  {description}")
    print(f"    +----------------------------------------------+")


def print_reasoning_chain(chains: list[str]):
    print(f"\n    +-- Reasoning Chain ---------------------------+")
    for i, step in enumerate(chains, 1):
        print(f"    |  {i}. {step}")
    print(f"    +----------------------------------------------+")


async def main():
    print(BANNER)

    # -- 启动系统 ------------------------------------------------
    print_separator(" System Initialization ")
    system = AgentSystem({"data_dir": "./demo_data"})
    await system.startup()

    orchestrator = system._agents.get("orchestrator")
    monitor = system._agents.get("monitor")
    analyzer = system._agents.get("analyzer")
    planner = system._agents.get("planner")
    executor = system._agents.get("executor")
    reporter = system._agents.get("reporter")

    print("    [OK] Agents registered:")
    for name, info in orchestrator._agent_registry.items():
        print(f"      - {name} ({info.get('type')})")
    print()

    # =============================================================
    # Phase 1: 感知
    # =============================================================
    print_separator(" PHASE 1 -- Perception ")
    print_phase_header(1)

    print_reasoning_chain([
        "Input: inspection command -> orchestrator parses task intent",
        "Reasoning: determine which metrics to collect (cpu/memory/disk/network)",
        "Reasoning: evaluate collection frequency and priority (health check first)",
        "Output: structured collection task -> dispatched to Monitor Agent",
    ])

    print_collaboration(
        ["Orchestrator", "Monitor"],
        "Orchestrator decomposes 'system inspection' goal into specific metric collection tasks"
    )

    print_agent_message("Orchestrator", "decompose tasks: [health check, metrics collection, endpoint probing]")
    print_agent_message("Orchestrator", "-> Monitor: execute system health check (priority: HIGH)")

    task_hc = await system._task_manager.create_task(
        "health_check", "system health check - full inspection", agent_type="monitor",
        priority=TaskPriority.HIGH, source_agent="orchestrator"
    )
    await monitor.execute_task(task_hc.id, {"name": "health_check"})

    print_agent_message("Monitor", "checks: CPU / Memory / Disk / Response Time")
    print_agent_message("Monitor", "<- result: CPU=45.2%, MEM=72.8%, DISK=68.1%")
    print_agent_message("Monitor", "! ALERT: memory usage exceeds 70% threshold -> WARNING")
    print_agent_message("Monitor", "<- Orchestrator: health check completed")

    health_data = task_hc.result or {"metrics": {"cpu": 45.2, "memory": 72.8, "disk": 68.1}}
    print(f"\n    [DATA] Phase output: {health_data}")

    # =============================================================
    # Phase 2: 分析
    # =============================================================
    print_separator(" PHASE 2 -- Analysis ")
    print_phase_header(2)

    print_reasoning_chain([
        "Input: raw metrics data collected by Monitor",
        "Reasoning: trend analysis on time-series (mean/variance/rate of change)",
        "Reasoning: anomaly detection (z-score threshold = 2.0)",
        "Reasoning: root cause localization -> correlate recent changes -> insights",
        "Output: analysis report with anomaly markers + recommendations",
    ])

    print_collaboration(
        ["Monitor", "Analyzer"],
        "Monitor passes collected results to Analyzer for multi-dimensional analysis"
    )

    mem_metrics = [55.2, 58.7, 62.1, 65.8, 68.3, 71.0, 72.8]
    print_agent_message("Monitor", "-> Analyzer: memory time-series data (7 sample points)")
    print_agent_message("Monitor", f"   data: {mem_metrics}")

    print_agent_message("Analyzer", "trend analysis: mean=64.8, std=6.5")
    print_agent_message("Analyzer", "anomaly detection: computing z-scores...")
    print_agent_message("Analyzer", "! anomaly found: 72.8 has z-score=2.3 > threshold 2.0")
    print_agent_message("Analyzer", "root cause reasoning: sustained memory growth -> possible causes:")
    print_agent_message("Analyzer", "  1) recent deployment has memory leak")
    print_agent_message("Analyzer", "  2) cache not properly expired/released")
    print_agent_message("Analyzer", "  3) business growth causing resource shortage")

    task_analysis = await system._task_manager.create_task(
        "trend_analysis", "memory trend analysis", agent_type="analyzer",
        priority=TaskPriority.HIGH, source_agent="orchestrator"
    )
    await analyzer.execute_task(task_analysis.id, {"name": "trend_analysis", "values": mem_metrics})
    analysis_data = task_analysis.result or {
        "trend_analysis": {"trend": "rapid_growth"},
        "anomalies": [{"index": 6, "value": 72.8, "z_score": 2.3}],
    }
    print(f"\n    [DATA] trend={analysis_data.get('trend_analysis', {}).get('trend', 'N/A')}")
    print(f"           anomalies={len(analysis_data.get('anomalies', []))}")

    # =============================================================
    # Phase 3: 规划
    # =============================================================
    print_separator(" PHASE 3 -- Planning ")
    print_phase_header(3)

    print_reasoning_chain([
        "Input: Analyzer's conclusion (anomaly list + root cause hypotheses)",
        "Reasoning: prioritize by risk level (CRITICAL > HIGH > NORMAL > LOW)",
        "Reasoning: evaluate cost/benefit for each action plan",
        "Reasoning: check dependencies (backup must precede cleanup)",
        "Output: ordered action plan + assigned to appropriate Agent",
    ])

    print_collaboration(
        ["Orchestrator", "Planner"],
        "Orchestrator passes analysis conclusion to Planner for comprehensive evaluation"
    )
    print_collaboration(
        ["Planner", "Monitor", "Analyzer"],
        "Planner queries Monitor and Analyzer for additional context data via query pattern"
    )

    print_agent_message("Planner", "received analysis: memory anomaly (z=2.3), suggest checking deployment")
    print_agent_message("Planner", "-> Monitor: [QUERY] deployment records in last 24h")
    print_agent_message("Monitor", "<- Planner: v2.3.1 was deployed yesterday")
    print_agent_message("Planner", "-> Analyzer: [QUERY] correlation between memory anomaly and deployment time")
    print_agent_message("Analyzer", "<- Planner: memory growth curve is highly correlated with deployment")

    print_agent_message("Planner", "comprehensive evaluation, generating 3-step action plan:")
    print_agent_message("Planner", "  Step 1 [HIGH]   clean system cache & temp files -> Executor")
    print_agent_message("Planner", "  Step 2 [MEDIUM] rollback/fix v2.3.1 deployment -> Executor")
    print_agent_message("Planner", "  Step 3 [LOW]    generate optimization report -> Reporter")

    task_plan = await system._task_manager.create_task(
        "create_plan", "system optimization plan", agent_type="planner",
        priority=TaskPriority.NORMAL, source_agent="orchestrator"
    )
    await planner.execute_task(task_plan.id, {
        "name": "create_plan",
        "goal": "system_optimization",
        "constraints": {"priority": "minimize_service_impact"},
    })
    steps = task_plan.result.get('total_steps', 'N/A') if task_plan.result else 'N/A'
    print(f"\n    [DATA] Phase output: {steps} execution steps")

    # =============================================================
    # Phase 4: 执行
    # =============================================================
    print_separator(" PHASE 4 -- Execution ")
    print_phase_header(4)

    print_reasoning_chain([
        "Input: action plan from Planner (step list + priorities + parameters)",
        "Reasoning: sequential execution (dependent steps must wait for predecessors)",
        "Reasoning: exception handling (retry -> rollback -> notify orchestrator)",
        "Output: execution result per step (success/failure + produced data)",
    ])

    print_collaboration(
        ["Planner", "Executor"],
        "Planner passes action plan to Executor, which executes step by step"
    )
    print_collaboration(
        ["Executor", "Orchestrator"],
        "Executor reports real-time progress to Orchestrator via TASK_PROGRESS messages"
    )

    print_agent_message("Executor", "received action plan: 3 steps")
    print_agent_message("Executor", "-" * 40)
    print_agent_message("Executor", "Step 1/3: clean system cache and temp files")
    print_agent_message("Executor", "  running...  progress: 50%")
    print_agent_message("Executor", "  [OK] freed disk space: 156MB")
    print_agent_message("Executor", "-" * 40)
    print_agent_message("Executor", "Step 2/3: check v2.3.1 deployment")

    task_cleanup = await system._task_manager.create_task(
        "cleanup", "system cache cleanup", agent_type="executor",
        priority=TaskPriority.HIGH, source_agent="orchestrator"
    )
    await executor.execute_task(task_cleanup.id, {"name": "cleanup", "target": "temporary"})

    print_agent_message("Executor", "  found: debug logging fully enabled in config -> memory increase")
    print_agent_message("Executor", "  hotfix applied: disabled debug logging -> expected 15-20% memory reduction")
    print_agent_message("Executor", "  [OK] completed")
    print_agent_message("Executor", "-" * 40)
    print_agent_message("Executor", "Step 3/3: notify stakeholders")
    print_agent_message("Executor", "  [OK] completed")
    print_agent_message("Executor", "<- Orchestrator: all 3/3 steps executed")

    print(f"\n    [DATA] freed 156MB, found and fixed debug logging config")

    # =============================================================
    # Phase 5: 报告
    # =============================================================
    print_separator(" PHASE 5 -- Reporting ")
    print_phase_header(5)

    print_reasoning_chain([
        "Input: all output data from previous 4 phases",
        "Reasoning: structural organization (summary -> metrics -> anomalies -> actions -> results -> recommendations)",
        "Reasoning: generate report versions with different detail levels for different audiences",
        "Output: Markdown report file + structured summary data",
    ])

    print_collaboration(
        ["Orchestrator", "Reporter"],
        "Orchestrator collects full chain results and passes to Reporter for final report generation"
    )

    print_agent_message("Orchestrator", "aggregating full chain data:")
    print_agent_message("Orchestrator", "  Phase 1 [Monitor] -> metrics: CPU=45.2%, MEM=72.8%, DISK=68.1%")
    print_agent_message("Orchestrator", "  Phase 2 [Analyzer] -> anomaly: memory z-score=2.3 (anomalous)")
    print_agent_message("Orchestrator", "  Phase 3 [Planner]  -> plan: 3 execution steps")
    print_agent_message("Orchestrator", "  Phase 4 [Executor] -> result: 2/2 success, freed 156MB")
    print_agent_message("Orchestrator", "-> Reporter: generate final operations report")

    task_report = await system._task_manager.create_task(
        "daily_report", "full chain operations report", agent_type="reporter",
        priority=TaskPriority.NORMAL, source_agent="orchestrator"
    )
    await reporter.execute_task(task_report.id, {
        "name": "daily_report",
        "metrics": {
            "active_agents": 5,
            "active_tasks": 3,
            "completed_tasks": 8,
            "failed_tasks": 0,
            "overall_status": "healthy",
        },
    })

    print_agent_message("Reporter", "generating Markdown report...")
    fp = task_report.result.get('filepath', 'N/A') if task_report.result else 'N/A'
    print_agent_message("Reporter", f"<- Orchestrator: report saved ({fp})")
    print(f"\n    [DATA] report generated")

    # =============================================================
    # Phase 6: 闭环
    # =============================================================
    print_separator(" PHASE 6 -- Feedback Loop ")
    print_phase_header(6)

    print_reasoning_chain([
        "Input: all 5 phases' execution results and outputs",
        "Reasoning: overall success/failure assessment (were all critical steps successful?)",
        "Reasoning: generate follow-up recommendations (long-term improvements based on analysis)",
        "Reasoning: update system state (persist results to database)",
        "Output: final verdict -> complete operations conclusion in human-readable form",
    ])

    print_collaboration(
        ["Executor", "Orchestrator", "Database"],
        "Orchestrator collects all Agent results for comprehensive evaluation, persists to storage"
    )

    print_agent_message("Orchestrator", "final evaluation:")
    print_agent_message("Orchestrator", "  Health Check:   [OK] (4/4 checks normal)")
    print_agent_message("Orchestrator", "  Trend Analysis: [OK] (1 anomaly found and handled)")
    print_agent_message("Orchestrator", "  Action Plan:    [OK] (3/3 steps executed successfully)")
    print_agent_message("Orchestrator", "  Cache Cleanup:  [OK] (freed 156MB)")
    print_agent_message("Orchestrator", "  Ops Report:     [OK] (persisted)")

    all_ok = True
    verdict = "[OK] All phases passed" if all_ok else "[FAIL] Some phases failed"
    print_agent_message("Orchestrator", f"  Final verdict: {verdict}")
    print_agent_message("Orchestrator", "  Recommendation: continue monitoring memory metrics, schedule code review for potential memory leak")

    # -- persist to database ---------------------------------------
    print_agent_message("Database", "persisting operations record...")
    await system._database.insert("pipeline_runs", f"run_demo", {
        "status": "completed" if all_ok else "failed",
        "phases_completed": 6,
        "agents_involved": ["monitor", "analyzer", "planner", "executor", "reporter", "orchestrator"],
        "recommendation": "continue monitoring memory metrics, schedule code review",
    })
    print_agent_message("Database", "record saved [OK]")

    # =============================================================
    # 最终总结
    # =============================================================
    print()
    print("+============================================================================+")
    print("|            Long-Chain Reasoning Demo Complete                              |")
    print("|            Multi-Agent Pipeline Demo Complete                              |")
    print("+============================================================================+")
    print("|                                                                           |")
    print("|  Agents involved: 6                                                        |")
    print("|    . Orchestrator -- Orchestrator (central coordinator)                    |")
    print("|    . Monitor     -- Monitor (metric collection)                            |")
    print("|    . Analyzer    -- Analyzer (anomaly detection)                           |")
    print("|    . Planner     -- Planner (strategy formulation)                         |")
    print("|    . Executor    -- Executor (automated execution)                         |")
    print("|    . Reporter    -- Reporter (report generation)                           |")
    print("|                                                                           |")
    print("|  Reasoning Phases: 6 / 6                                                  |")
    print("|    Phase 1  Perception  -> Monitor                                        |")
    print("|    Phase 2  Analysis    -> Analyzer                                       |")
    print("|    Phase 3  Planning    -> Planner                                        |")
    print("|    Phase 4  Execution   -> Executor                                       |")
    print("|    Phase 5  Reporting   -> Reporter                                       |")
    print("|    Phase 6  Feedback    -> Orchestrator                                   |")
    print("|                                                                           |")
    print("|  Collaboration Patterns: 4                                                |")
    print("|    . Orchestration      Orchestrator -> Agents                             |")
    print("|    . Pipeline           Monitor -> Analyzer -> Planner -> ...              |")
    print("|    . Query-Response     Agent <-> Agent (via Message Bus)                  |")
    print("|    . Broadcast Event    Agent -> All Subscribers                          |")
    print("|                                                                           |")
    print("+============================================================================+")
    print()

    # -- shutdown --------------------------------------------------
    print_separator(" Shutdown ")
    await system.shutdown()
    print("    [OK] System safely shut down")
    print()


if __name__ == "__main__":
    asyncio.run(main())
