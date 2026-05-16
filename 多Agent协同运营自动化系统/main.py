#!/usr/bin/env python3
"""
多Agent协同运营自动化系统
Multi-Agent Collaborative Operations Automation System

A framework where specialized AI agents collaborate to automate
operations: monitoring, analysis, planning, execution, and reporting.

Usage:
    python main.py                    # Start with dashboard
    python main.py --no-dashboard     # Headless mode
    python main.py --port 9090        # Custom dashboard port
"""

from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system import AgentSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


async def main():
    parser = argparse.ArgumentParser(description="多Agent协同运营自动化系统")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port (default: 8080)")
    parser.add_argument("--no-dashboard", action="store_true", help="Run without web dashboard")
    parser.add_argument("--data-dir", type=str, default="data", help="Data directory (default: data)")
    parser.add_argument("--metrics-interval", type=int, default=60, help="Metrics collection interval (s)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    config = {
        "data_dir": args.data_dir,
        "metrics_interval": args.metrics_interval,
        "report_interval": 300,
        "health_check_interval": 120,
    }

    system = AgentSystem(config)

    try:
        await system.startup()

        if not args.no_dashboard:
            from dashboard.web_dashboard import WebDashboard
            dashboard = WebDashboard(system, port=args.port)
            await dashboard.start()
            system._dashboard = dashboard

            # Broadcast initial status
            orchestrator = system._agents.get("orchestrator")
            if orchestrator:
                status = await orchestrator.get_system_status()
                await dashboard.broadcast_status({
                    **status,
                    "message": "System started",
                    "level": "info",
                })
        else:
            logger.info("Running in headless mode (no dashboard)")

        logger.info("=" * 50)
        logger.info("System is running. Press Ctrl+C to stop.")
        logger.info("=" * 50)

        # Keep running
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await system.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
