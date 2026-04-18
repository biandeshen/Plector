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

from core.agent_loop import AgentLoop, filter_think_tags
from core.metrics import get_metrics_collector
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

    # 初始化 conversation_titles 表
    import sqlite3

    conn = sqlite3.connect("data/plector.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_titles (
            session_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("对话标题表已初始化")


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
        metrics = get_metrics_collector()
        metrics.inc_websocket_connection()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            metrics = get_metrics_collector()
            metrics.dec_websocket_connection()

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


@app.get("/api/metrics")
async def api_metrics():
    """Prometheus 指标"""
    metrics = get_metrics_collector()
    # Update active connections gauge from connection manager
    metrics.set_active_connections(len(manager.active_connections))
    return metrics.get_all_metrics()


@app.get("/api/conversations")
async def api_conversations():
    """获取对话历史列表"""
    try:
        import sqlite3

        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()

        # 先建表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_titles (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 联合查询：优先用标题表，否则取第一条消息
        cursor.execute("""
            SELECT c.session_id,
                   COALESCE(t.title, (
                       SELECT content FROM conversations
                       WHERE session_id = c.session_id AND role = 'user'
                       ORDER BY rowid ASC LIMIT 1
                   )) as title,
                   c.last_rowid
            FROM (
                SELECT session_id, MAX(rowid) as last_rowid
                FROM conversations
                GROUP BY session_id
            ) c
            LEFT JOIN conversation_titles t ON c.session_id = t.session_id
            ORDER BY c.last_rowid DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()

        conversations = []
        for row in rows:
            title = row[1] or ""
            title = title[:30] + "..." if len(title) > 30 else title
            conversations.append(
                {
                    "session_id": row[0],
                    "title": title,
                }
            )
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        return {"conversations": [], "error": str(e)}


@app.get("/api/conversations/{session_id}")
async def api_conversation(session_id: str):
    """获取指定对话的消息"""
    try:
        import sqlite3

        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rowid, session_id, role, content FROM conversations WHERE session_id = ? ORDER BY rowid ASC",
            (session_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            messages.append(
                {
                    "id": row[0],  # rowid
                    "role": row[2],  # role
                    "content": row[3],  # content
                }
            )
        return {"session_id": session_id, "messages": messages}
    except Exception as e:
        logger.error(f"获取对话失败: {e}")
        return {"session_id": session_id, "messages": [], "error": str(e)}


@app.post("/api/conversations")
async def api_create_conversation():
    """创建新对话"""
    import sqlite3
    import uuid

    session_id = uuid.uuid4().hex
    # 立即创建会话记录
    conn = sqlite3.connect("data/plector.db")
    cursor = conn.cursor()
    # 创建一个空的用户消息作为占位，确保会话出现在列表中
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)", (session_id, "user", "[新对话]")
    )
    # 同时创建标题记录
    cursor.execute("INSERT INTO conversation_titles (session_id, title) VALUES (?, ?)", (session_id, "新对话"))
    conn.commit()
    conn.close()
    return {"session_id": session_id, "message": "新对话已创建"}


@app.patch("/api/conversations/{session_id}")
async def api_rename_conversation(session_id: str, request: dict):
    """重命名对话"""
    try:
        import sqlite3

        new_title = request.get("title", "").strip()
        if not new_title:
            return {"error": "标题不能为空"}

        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO conversation_titles (session_id, title) VALUES (?, ?)", (session_id, new_title)
        )
        conn.commit()
        conn.close()
        return {"session_id": session_id, "title": new_title}
    except Exception as e:
        logger.error(f"重命名对话失败: {e}")
        return {"error": str(e)}


@app.delete("/api/conversations/{session_id}")
async def api_delete_conversation(session_id: str):
    """删除对话"""
    try:
        import sqlite3

        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return {"deleted": deleted, "session_id": session_id}
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        return {"error": str(e)}


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


def _auto_generate_title(session_id: str, first_user_message: str):
    """为对话自动生成简短标题"""
    try:
        import sqlite3

        # 检查是否已有标题
        conn = sqlite3.connect("data/plector.db")
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM conversation_titles WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return  # 已有标题，不覆盖

        # 从用户消息提取关键词生成标题
        # 移除常见前缀、标点，提取核心内容
        text = first_user_message.strip()
        # 移除常见开头词
        for prefix in ["请", "帮我", "我想", "能不能", "可以帮我", "请问"]:
            if text.startswith(prefix):
                text = text[len(prefix) :]
        # 取前15个字符作为标题
        title = text[:15].strip()
        if len(title) < 2:
            title = text[:20].strip()
        if title:
            cursor.execute(
                "INSERT OR IGNORE INTO conversation_titles (session_id, title) VALUES (?, ?)", (session_id, title)
            )
            conn.commit()
        conn.close()
        logger.info(f"为对话 {session_id} 生成标题: {title}")
    except Exception as e:
        logger.warning(f"自动生成标题失败: {e}")


async def _handle_websocket_message(message: dict, websocket: WebSocket):
    """处理 WebSocket 消息"""
    user_input = message.get("content", "")
    session_id = message.get("session_id")  # 可选，指定对话ID

    if not user_input:
        return

    # 速率限制（按 IP）
    client_ip = websocket.client.host if websocket.client else "unknown"
    if not rate_limiter.allow(client_ip):
        await websocket.send_json(
            {
                "type": "error",
                "content": "请求过于频繁，请稍后再试",
            }
        )
        return

    log_event("ws.message", {"role": "user", "content": user_input})

    await websocket.send_json(
        {
            "type": "thinking",
            "content": "思考中...",
        }
    )

    try:
        async for event in agent.run_streaming(user_input, session_id):
            t = event.get("type", "")
            if t == "chunk":
                await websocket.send_json(
                    {
                        "type": "chunk",
                        "content": event["content"],
                    }
                )
            elif t == "toolExecuting":
                await websocket.send_json(
                    {
                        "type": "toolExecuting",
                        "tool": event.get("tool", ""),
                    }
                )
            elif t == "toolDone":
                await websocket.send_json(
                    {
                        "type": "toolDone",
                        "tool": event.get("tool", ""),
                    }
                )
            elif t == "tool_call_start":
                await websocket.send_json(
                    {
                        "type": "tool_call_start",
                        "count": event.get("count", 0),
                    }
                )
            elif t == "done":
                # 过滤 think 标签
                content = filter_think_tags(event.get("content", ""))
                await websocket.send_json(
                    {
                        "type": "response",
                        "content": content,
                    }
                )
                log_event("ws.message", {"role": "assistant", "content": content[:100]})

                # 自动生成标题（如果还没有）
                if session_id:
                    _auto_generate_title(session_id, user_input)
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
