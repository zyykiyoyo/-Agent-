from __future__ import annotations
import json
import logging
from datetime import datetime

from aiohttp import web

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>多Agent协同运营自动化系统</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: linear-gradient(135deg, #1e293b, #334155); padding: 20px 32px; border-bottom: 1px solid #475569; }}
  .header h1 {{ font-size: 24px; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .header p {{ color: #94a3b8; font-size: 14px; margin-top: 4px; }}
  .status-bar {{ display: flex; gap: 16px; padding: 16px 32px; background: #1e293b; border-bottom: 1px solid #334155; }}
  .stat-card {{ flex: 1; padding: 16px; background: #1e293b; border: 1px solid #334155; border-radius: 12px; text-align: center; }}
  .stat-card .value {{ font-size: 32px; font-weight: 700; }}
  .stat-card .label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; text-transform: uppercase; }}
  .stat-card.green .value {{ color: #34d399; }}
  .stat-card.blue .value {{ color: #60a5fa; }}
  .stat-card.yellow .value {{ color: #fbbf24; }}
  .stat-card.purple .value {{ color: #a78bfa; }}
  .stat-card.red .value {{ color: #f87171; }}
  .main {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; padding: 24px 32px; }}
  @media (max-width: 1024px) {{ .main {{ grid-template-columns: 1fr; }} }}
  .panel {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
  .panel h2 {{ padding: 16px 20px; font-size: 16px; border-bottom: 1px solid #334155; }}
  .panel-body {{ padding: 16px 20px; }}
  .agent-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .agent-item {{ display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: #0f172a; border-radius: 8px; }}
  .agent-name {{ display: flex; align-items: center; gap: 8px; }}
  .agent-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
  .agent-dot.active {{ background: #34d399; }}
  .agent-dot.inactive {{ background: #f87171; }}
  .task-item {{ padding: 8px 12px; background: #0f172a; border-radius: 8px; margin-bottom: 8px; }}
  .task-header {{ display: flex; justify-content: space-between; align-items: center; }}
  .task-name {{ font-weight: 500; }}
  .task-status {{ font-size: 12px; padding: 2px 8px; border-radius: 4px; }}
  .status-completed {{ background: rgba(52,211,153,0.2); color: #34d399; }}
  .status-running {{ background: rgba(96,165,250,0.2); color: #60a5fa; }}
  .status-pending {{ background: rgba(148,163,184,0.2); color: #94a3b8; }}
  .status-failed {{ background: rgba(248,113,113,0.2); color: #f87171; }}
  .btn {{ padding: 8px 16px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }}
  .btn-primary {{ background: #3b82f6; color: white; }}
  .btn-primary:hover {{ background: #2563eb; }}
  .btn-danger {{ background: #ef4444; color: white; }}
  .btn-success {{ background: #10b981; color: white; }}
  .controls {{ display: flex; gap: 8px; margin-top: 12px; }}
  .log {{ font-family: 'Courier New', monospace; font-size: 12px; max-height: 300px; overflow-y: auto; }}
  .log-entry {{ padding: 4px 0; border-bottom: 1px solid #1e293b; }}
  .log-time {{ color: #64748b; margin-right: 8px; }}
  .log-info {{ color: #60a5fa; }}
  .log-warning {{ color: #fbbf24; }}
  .log-error {{ color: #f87171; }}
  .action-panel {{ display: flex; gap: 8px; flex-wrap: wrap; }}
</style>
</head>
<body>
<div class="header">
  <h1>多Agent协同运营自动化系统</h1>
  <p>Multi-Agent Collaborative Operations Automation System</p>
</div>

<div class="status-bar" id="stats">
  <div class="stat-card blue"><div class="value" id="agent-count">0</div><div class="label">Agents</div></div>
  <div class="stat-card yellow"><div class="value" id="active-tasks">0</div><div class="label">Active Tasks</div></div>
  <div class="stat-card green"><div class="value" id="completed-tasks">0</div><div class="label">Completed</div></div>
  <div class="stat-card red"><div class="value" id="failed-tasks">0</div><div class="label">Failed</div></div>
  <div class="stat-card purple"><div class="value" id="uptime">0s</div><div class="label">Uptime</div></div>
</div>

<div class="main">
  <div class="panel">
    <h2> Agents</h2>
    <div class="panel-body agent-list" id="agent-list">
      <div style="color:#64748b;text-align:center;padding:24px;">Loading...</div>
    </div>
  </div>

  <div class="panel">
    <h2> Recent Tasks</h2>
    <div class="panel-body" id="task-list">
      <div style="color:#64748b;text-align:center;padding:24px;">Loading...</div>
    </div>
  </div>

  <div class="panel">
    <h2> Controls</h2>
    <div class="panel-body">
      <div class="action-panel">
        <button class="btn btn-primary" onclick="action('status')">System Status</button>
        <button class="btn btn-success" onclick="action('health_check')">Health Check</button>
        <button class="btn btn-primary" onclick="action('collect_metrics')">Collect Metrics</button>
        <button class="btn btn-success" onclick="action('daily_report')">Generate Report</button>
        <button class="btn btn-primary" onclick="action('create_plan')">Create Plan</button>
        <button class="btn btn-success" onclick="action('run_analysis')">Run Analysis</button>
        <button class="btn btn-primary" onclick="action('cleanup')">Run Cleanup</button>
      </div>
      <div id="action-result" style="margin-top:12px;padding:12px;background:#0f172a;border-radius:8px;display:none;"></div>
    </div>
  </div>

  <div class="panel">
    <h2> System Log</h2>
    <div class="panel-body log" id="log">
      <div style="color:#64748b;text-align:center;padding:24px;">Waiting for events...</div>
    </div>
  </div>
</div>

<script>
const API = '/api';
const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
const logEl = document.getElementById('log');
const logs = [];

function addLog(msg, level='info') {{
  const time = new Date().toLocaleTimeString();
  logs.push(`<div class="log-entry"><span class="log-time">[${{time}}]</span><span class="log-${{level}}">${{msg}}</span></div>`);
  logEl.innerHTML = logs.slice(-50).join('');
  logEl.scrollTop = logEl.scrollHeight;
}}

ws.onmessage = (e) => {{
  try {{
    const data = JSON.parse(e.data);
    if (data.type === 'status') updateDashboard(data);
    addLog(data.message || JSON.stringify(data).slice(0, 100), data.level || 'info');
  }} catch {{ addLog(e.data); }}
}};

function updateDashboard(data) {{
  document.getElementById('agent-count').textContent = data.agent_count || 0;
  document.getElementById('active-tasks').textContent = data.active_tasks || 0;
  document.getElementById('completed-tasks').textContent = data.completed_tasks || 0;
  document.getElementById('failed-tasks').textContent = data.failed_tasks || 0;
  document.getElementById('uptime').textContent = (data.uptime || 0) + 's';

  const agentList = document.getElementById('agent-list');
  if (data.agents) {{
    agentList.innerHTML = Object.entries(data.agents).map(([name, info]) => `
      <div class="agent-item">
        <div class="agent-name">
          <span class="agent-dot ${{info.status === 'active' ? 'active' : 'inactive'}}"></span>
          <strong>${{name}}</strong>
          <span style="color:#64748b;font-size:12px;">(${{info.type || 'unknown'}})</span>
        </div>
        <span style="font-size:12px;color:#94a3b8;">running: ${{info.load?.running || 0}} | pending: ${{info.load?.pending || 0}}</span>
      </div>
    `).join('');
  }}

  const taskList = document.getElementById('task-list');
  if (data.recent_tasks) {{
    taskList.innerHTML = data.recent_tasks.map(t => `
      <div class="task-item">
        <div class="task-header">
          <span class="task-name">${{t.name || 'Unnamed'}}</span>
          <span class="task-status status-${{(t.status || 'pending').toLowerCase()}}">${{t.status}}</span>
        </div>
        <div style="font-size:12px;color:#94a3b8;margin-top:4px;">
          ${{t.agent_type ? t.agent_type + ' | ' : ''}}${{t.created_at ? new Date(t.created_at).toLocaleString() : ''}}
        </div>
      </div>
    `).join('');
  }}
}}

async function action(name) {{
  const resultEl = document.getElementById('action-result');
  resultEl.style.display = 'block';
  resultEl.innerHTML = 'Executing...';
  try {{
    const resp = await fetch(`/api/action/${{name}}`, {{method: 'POST'}});
    const data = await resp.json();
    resultEl.innerHTML = `<pre style="font-size:12px;white-space:pre-wrap;">${{JSON.stringify(data, null, 2)}}</pre>`;
    addLog(`Action '${{name}}' completed`, 'info');
  }} catch (e) {{
    resultEl.innerHTML = `Error: ${{e.message}}`;
    addLog(`Action '${{name}}' failed: ${{e.message}}`, 'error');
  }}
}}

// Poll for status
setInterval(async () => {{
  try {{
    const resp = await fetch('/api/status');
    const data = await resp.json();
    updateDashboard(data);
  }} catch {{ }}
}}, 3000);
</script>
</body>
</html>"""


class WebDashboard:
    """Web-based dashboard for monitoring and controlling the agent system."""

    def __init__(self, agent_system, host: str = "0.0.0.0", port: int = 8080):
        self._system = agent_system
        self._host = host
        self._port = port
        self._app = web.Application()
        self._start_time = datetime.now()
        self._ws_clients: set = set()
        self._setup_routes()

    def _setup_routes(self):
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/status", self._handle_status)
        self._app.router.add_post("/api/action/{name}", self._handle_action)
        self._app.router.add_get("/ws", self._handle_websocket)

    async def _handle_index(self, request):
        return web.Response(text=HTML_TEMPLATE.format(), content_type="text/html")

    async def _handle_status(self, request):
        system = self._system
        orchestrator = system._agents.get("orchestrator")
        status = await orchestrator.get_system_status() if orchestrator else {}
        tasks = await system._task_manager.get_tasks(limit=20)

        uptime = (datetime.now() - self._start_time).total_seconds()
        data = {
            "agent_count": len(status.get("agents", {})),
            "active_tasks": status.get("tasks", {}).get("by_status", {}).get("RUNNING", 0),
            "completed_tasks": status.get("tasks", {}).get("by_status", {}).get("COMPLETED", 0),
            "failed_tasks": status.get("tasks", {}).get("by_status", {}).get("FAILED", 0),
            "uptime": round(uptime),
            "agents": status.get("agents", {}),
            "recent_tasks": [t.to_dict() for t in tasks[:10]],
        }
        return web.json_response(data)

    async def _handle_action(self, request):
        name = request.match_info["name"]
        try:
            result = await self._system.execute_action(name)
            # Broadcast to websocket clients
            await self._broadcast({
                "type": "action",
                "action": name,
                "result": result.get("result", result),
                "level": "info",
                "message": f"Action '{name}' triggered",
            })
            return web.json_response({"success": True, "result": result})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def _handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)
        try:
            async for _ in ws:
                pass
        finally:
            self._ws_clients.discard(ws)
        return ws

    async def _broadcast(self, data: dict):
        if not self._ws_clients:
            return
        msg = json.dumps(data, ensure_ascii=False)
        for ws in self._ws_clients.copy():
            try:
                await ws.send_str(msg)
            except Exception:
                self._ws_clients.discard(ws)

    async def start(self):
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        logger.info("Dashboard running at http://%s:%d", self._host, self._port)
        return runner

    async def broadcast_status(self, status_data: dict):
        await self._broadcast({
            "type": "status",
            **status_data,
        })
