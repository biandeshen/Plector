#!/usr/bin/env python3
"""
Plector v2.0 升级驱动
- 启动 Plector WebSocket 服务器（子进程）
- 通过 WebSocket 持续发送升级任务
- 循环直到完成
"""
import asyncio
import subprocess
import sys
import time
import os
import json

from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PLAN_PATH = PROJECT_ROOT / "docs" / "reports" / "upgrade_plan_v2.0_integrated.md"
WS_URL = "ws://127.0.0.1:8082/ws"
SERVER_PORT = 8082
MAX_TURNS = 200
TURN_DELAY = 2

proc = None


def start_server():
    global proc
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [sys.executable, "channels/websocket.py", "--port", str(SERVER_PORT)],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(f"Plector PID={proc.pid}")
    return proc


def wait_for_server(timeout=30):
    import httpx
    url = f"http://127.0.0.1:{SERVER_PORT}/api/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code == 200:
                print(f"Server ready ({time.time()-start:.1f}s)")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def log(msg):
    print(msg, flush=True)


async def send_ws(ws, msg):
    """发送消息并等待响应"""
    safe = msg[:60].replace("\n", " ")
    log(f"\n[SEND] {safe}...")
    await ws.send(json.dumps({"content": msg}))

    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=180)
            data = json.loads(raw)
            t, c = data.get("type", ""), data.get("content", "")

            if t == "thinking":
                print(f"  ... {c[:80]}")
            elif t == "response":
                print(f"  [RESP] {c[:200]}")
                return c
            elif t == "error":
                print(f"  [ERROR] {c[:200]}")
                return f"ERROR: {c}"
        except asyncio.TimeoutError:
            print("  [TIMEOUT waiting]")
            return "TIMEOUT"


async def run_loop():
    import websockets
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        log("WebSocket connected!\n")

        task = (
            f"你是 Plector。请读取升级方案文件：{PLAN_PATH}，"
            f"然后开始执行 Phase 1：创建 skills/context_refresher/ 技能（GSD 上下文保鲜）。"
            f"创建 implementation.py 和 skill.json，写完后报告'已完成: [文件名]'。开始。"
        )
        await send_ws(ws, task)

        for turn in range(1, MAX_TURNS + 1):
            print(f"\n=== Turn {turn}/{MAX_TURNS} ===")
            resp = await send_ws(ws, "继续。有任何进展就报告。")
            await asyncio.sleep(TURN_DELAY)

            if "error" in resp.lower() or resp == "TIMEOUT":
                continue

            if "完成" in resp and "phase" in resp.lower():
                print("\n[PLECTOR] 进展良好，继续下一项任务...")

        print(f"\nMax turns ({MAX_TURNS}) reached.")


async def main():
    global proc
    try:
        start_server()
        time.sleep(3)
        if not wait_for_server():
            print("Server failed to start!")
            return
        await run_loop()
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            print(f"\nServer PID={proc.pid} stopped.")


if __name__ == "__main__":
    import websockets
    asyncio.run(main())
