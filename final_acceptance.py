import asyncio
import io
import sys

from core.agent_loop import AgentLoop
from core.event_bus import EventBus
from core.function_calling import ToolRegistry
from core.skill_handler import SkillHandler
from core.skill_registry import SkillRegistry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

results = []

# 1. 模块导入
try:
    agent = AgentLoop()
    results.append(
        (
            "模块导入",
            "✅",
            f"{len(agent.skill_registry.skills)} skills, {len(agent.tool_registry.get_tool_schemas())} tools",
        )
    )
except Exception as e:
    results.append(("模块导入", "❌", str(e)))


# 2. 技能调用
async def test_skills():
    r = SkillRegistry()
    r.scan()
    h = SkillHandler(r)
    result = await h.execute("health_monitor", "check_health", {})
    if result.get("result", {}).get("success"):
        return "✅", f"CPU: {result['result']['data']['cpu']}%, Memory: {result['result']['data']['memory']}%"
    else:
        return "❌", str(result)


try:
    status, detail = asyncio.run(test_skills())
    results.append(("技能调用", status, detail))
except Exception as e:
    results.append(("技能调用", "❌", str(e)))


# 3. CloudEvents 格式
async def test_cloudevents():
    bus = EventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe("test.final", handler)
    await bus.publish("test.final", {"msg": "hello"}, source="final_test")
    await asyncio.sleep(0.5)
    e = received[0]
    assert e["specversion"] == "1.0"
    assert e["type"] == "test.final"
    return "✅", "CloudEvents 1.0 格式正确"


try:
    status, detail = asyncio.run(test_cloudevents())
    results.append(("CloudEvents", status, detail))
except Exception as e:
    results.append(("CloudEvents", "❌", str(e)))


# 4. JSON-RPC 2.0
async def test_jsonrpc():
    t = ToolRegistry()
    result = await t.execute({"function": {"name": "nonexistent", "arguments": "{}"}})
    assert result.get("jsonrpc") == "2.0"
    assert result.get("error", {}).get("code") == -32601
    return "✅", "JSON-RPC 2.0 错误码正确"


try:
    status, detail = asyncio.run(test_jsonrpc())
    results.append(("JSON-RPC 2.0", status, detail))
except Exception as e:
    results.append(("JSON-RPC 2.0", "❌", str(e)))

# 输出结果
print("=" * 60)
print("Plector v1.0 最终验收")
print("=" * 60)
for name, status, detail in results:
    print(f"{status} {name}: {detail}")
print("=" * 60)
passed = sum(1 for _, s, _ in results if s == "✅")
print(f"通过: {passed}/{len(results)}")
