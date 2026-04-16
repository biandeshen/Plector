#!/usr/bin/env python3
"""
Plector WebSocket 渠道 + Dashboard

功能：
    1. WebSocket 实时对话
    2. REST API 查询技能/工具/健康/事件
    3. Dashboard 静态页面

启动方式：
    python channels/websocket.py
    python channels/websocket.py --host 0.0.0.0 --port 8080

访问：
    http://localhost:8080

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import logging
from datetime import datetime

import psutil
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from core.agent_loop import AgentLoop
from core.rate_limiter import rate_limiter

# 加载 .env 环境变量（在所有导入之后）
load_dotenv()

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="Plector", version="1.1.0")


@app.on_event("startup")
async def startup():
    """应用启动时初始化 Agent"""
    global agent
    if agent is None:
        agent = AgentLoop()
        logger.info("Agent 已初始化")


# 全局 Agent 实例
agent: AgentLoop = None


# 连接管理
class ConnectionManager:
    """WebSocket 连接管理"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """向所有连接广播消息"""
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)


manager = ConnectionManager()

# 事件日志（内存中保留最近 100 条）
event_log: list[dict] = []
MAX_EVENT_LOG = 100


def log_event(event_type: str, data: dict):
    """记录事件到日志"""
    event_log.append(
        {
            "time": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
    )
    if len(event_log) > MAX_EVENT_LOG:
        event_log.pop(0)


# ==================== REST API ====================


@app.get("/")
async def index():
    """返回 Dashboard 页面"""
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def api_health():
    """系统健康状态"""
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu": cpu,
        "memory": memory.percent,
        "memory_total": round(memory.total / (1024**3), 1),
        "memory_used": round(memory.used / (1024**3), 1),
        "disk": disk.percent,
        "disk_total": round(disk.total / (1024**3), 1),
        "disk_used": round(disk.used / (1024**3), 1),
        "status": "healthy" if cpu < 90 and memory.percent < 90 else "degraded",
    }


@app.get("/api/skills")
async def api_skills():
    """技能列表"""
    skills = []
    for name, info in agent.skill_registry.skills.items():
        tools = info["meta"].get("tools", [])
        skills.append(
            {
                "name": name,
                "description": info["meta"].get("description", ""),
                "version": info["meta"].get("version", ""),
                "tier": info["meta"].get("tier", ""),
                "tools": [{"name": t["name"], "description": t.get("description", "")} for t in tools],
            }
        )
    return {"skills": skills, "total": len(skills)}


@app.get("/api/tools")
async def api_tools():
    """工具列表"""
    schemas = agent.tool_registry.get_tool_schemas()
    local = []
    mcp = []
    for s in schemas:
        name = s["function"]["name"]
        tool = {"name": name, "description": s["function"].get("description", "")}
        if name.startswith("mcp_"):
            mcp.append(tool)
        else:
            local.append(tool)
    return {
        "local": local,
        "mcp": mcp,
        "total": len(schemas),
    }


@app.get("/api/events")
async def api_events():
    """事件日志"""
    return {"events": event_log, "total": len(event_log)}


@app.get("/api/config")
async def api_config():
    """当前配置"""
    config = agent.config or {}
    llm_config = config.get("llm", {})
    return {
        "llm_provider": llm_config.get("provider", "ollama"),
        "max_iterations": config.get("max_iterations", 10),
        "skills_count": len(agent.skill_registry.skills),
        "tools_count": len(agent.tool_registry.get_tool_schemas()),
    }


# ==================== WebSocket ====================


async def _handle_websocket_message(message: dict, websocket: WebSocket):
    """处理 WebSocket 消息"""
    user_input = message.get("content", "")
    if not user_input:
        return

    # 速率限制（按 IP）
    client_ip = websocket.client.host if websocket.client else "unknown"
    if not rate_limiter.allow(client_ip):
        await websocket.send_json({
            "type": "error",
            "content": "请求过于频繁，请稍后再试",
        })
        return

    log_event("ws.message", {"role": "user", "content": user_input})

    await websocket.send_json(
        {
            "type": "thinking",
            "content": "思考中...",
        }
    )

    try:
        async for event in agent.run_streaming(user_input):
            t = event.get("type", "")
            if t == "chunk":
                await websocket.send_json({
                    "type": "chunk",
                    "content": event["content"],
                })
            elif t == "toolExecuting":
                await websocket.send_json({
                    "type": "toolExecuting",
                    "tool": event.get("tool", ""),
                })
            elif t == "toolDone":
                await websocket.send_json({
                    "type": "toolDone",
                    "tool": event.get("tool", ""),
                })
            elif t == "tool_call_start":
                await websocket.send_json({
                    "type": "tool_call_start",
                    "count": event.get("count", 0),
                })
            elif t == "done":
                await websocket.send_json({
                    "type": "response",
                    "content": event["content"],
                })
                log_event("ws.message", {"role": "assistant", "content": event.get("content", "")[:100]})
                break

    except Exception as e:
        logger.error(f"Agent 执行失败: {e}", exc_info=True)
        await websocket.send_json(
            {
                "type": "error",
                "content": f"执行失败: {e}",
            }
        )
        log_event("ws.error", {"error": str(e)})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 对话端点"""
    await manager.connect(websocket)
    log_event("ws.connect", {"client": str(websocket.client)})

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await _handle_websocket_message(message, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        log_event("ws.disconnect", {"client": str(websocket.client)})


# ==================== 启动 ====================


def create_app(config: dict = None):
    """创建应用（供外部调用）"""
    global agent
    agent = AgentLoop(config or {})
    return app


def main():
    """启动服务器"""
    parser = argparse.ArgumentParser(description="Plector WebSocket 渠道")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8080, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="自动重载（开发模式）")
    args = parser.parse_args()

    logger.info(f"Plector WebSocket 启动: http://{args.host}:{args.port}")
    logger.info(f"Dashboard: http://{args.host}:{args.port}/")
    logger.info(f"WebSocket: ws://{args.host}:{args.port}/ws")

    uvicorn.run(
        "channels.websocket:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
