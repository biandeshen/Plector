---
tags: [Plector, 技术设计, 架构, v1.2]
type: design
created: 2026-04-08
---

# Plector 技术设计文档（DESIGN.md）v1.2

**版本**: 1.2（定稿）
**状态**: 已定稿
**关联 PRD**: v1.2
**关联 BRD**: v1.1

> 本次修订：修复 ClosureEngine 缺少 skill_handler 注入的问题，明确依赖注入关系。

---

## 1. 设计目标

- 实现 BRD/PRD 定义的功能，核心代码量控制在 5000 行以内。
- 保持模块解耦，核心引擎（`core/`）、技能（`skills/`）、工具（`tools/`）、接入渠道（`channels/`）独立。
- 事件驱动架构，支持异步消息和闭环自愈。
- 技能数量 ≤ 15 个，工具数量不限。
- 单元测试覆盖率 ≥ 80%。

---

## 2. 整体架构

```
plector/
├── core/                       # 核心引擎（不依赖 skills/ 和 tools/）
│   ├── agent_loop.py           # ReAct 循环
│   ├── event_bus.py            # 事件总线
│   ├── skill_registry.py       # 技能注册与管理
│   ├── skill_handler.py        # 技能执行器
│   ├── closure_engine.py       # 闭环引擎（条件图解析与执行）
│   ├── context_builder.py      # 上下文构建（从 .md 文件）
│   ├── function_calling.py     # 工具 Schema 生成与调用
│   ├── llm_client.py         # LLM 客户端
│   ├── mcp_client.py          # MCP Client（连接外部 MCP Server）
│   └── governance.py           # 技能治理（健康分、淘汰）
├── skills/                     # 核心技能（≤15 个）
│   └── <skill_name>/
│       ├── skill.json
│       └── implementation.py
├── tools/                      # 工具函数（无状态、无治理）
│   └── <tool_name>.py          # 使用 @tool 装饰器
├── channels/                   # 接入渠道
│   ├── cli.py
│   └── websocket.py
├── config/                     # 配置文件
│   ├── config.yaml
│   ├── closed_loops.yaml       # 闭环配置（统一路径）
│   └── profiles/
│       ├── AGENTS.md
│       ├── SOUL.md
│       └── USER.md
```

> 注：闭环配置路径统一为 `config/closed_loops.yaml`。

---

## 3. 核心模块设计

### 3.1 自主决策循环（Agent Loop）

**文件**：`core/agent_loop.py`

**职责**：实现 ReAct 模式，管理 LLM 调用、工具执行、结果回填。
**关键设计**：将技能也注册为工具，LLM 通过统一的 `tool_calls` 机制调用技能和工具。

```python
class AgentLoop:
    def __init__(self, config: dict):
        self.llm = self._init_llm(config)
        self.skill_registry = SkillRegistry()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.max_iterations = config.get("max_iterations", 10)
        self._register_skills_as_tools()
        # 创建闭环引擎（注入 skill_handler）
        self.closure_engine = ClosureEngine(self.skill_handler, "config/closed_loops.yaml")

    def _register_skills_as_tools(self):
        """将每个技能的工具注册为 LLM 可调用工具（MCP 格式）"""
        for skill_name, skill_info in self.skill_registry.skills.items():
            for tool_def in skill_info["meta"].get("tools", []):
                tool_name = f"{skill_name}_{tool_def['name']}"
                self.tool_registry.register(
                    name=tool_name,
                    description=tool_def.get("description", ""),
                    input_schema=tool_def.get("inputSchema", {}),
                    handler=self._create_skill_handler(skill_name, tool_def["name"])
                )

    def _create_skill_handler(self, skill_name, method_name):
        """创建技能调用闭包，作为工具的回调"""
        async def handler(**kwargs):
            return await self.skill_handler.execute(skill_name, method_name, kwargs)
        return handler

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环，返回最终回复"""
        messages = self._load_conversation(session_id)
        messages.append({"role": "user", "content": user_input})

        for _ in range(self.max_iterations):
            response = await self.llm.chat(
                messages=messages,
                tools=self.tool_registry.get_tool_schemas()
            )
            if not response.tool_calls:
                self._save_conversation(session_id, messages + [response.message])
                return response.content

            for tool_call in response.tool_calls:
                result = await self.tool_registry.execute(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
        return "达到最大迭代次数，任务未完成"
```

---

### 3.2 事件总线

**文件**：`core/event_bus.py`

**职责**：异步事件发布/订阅，解耦技能与闭环。

```python
class EventBus:
    def __init__(self, backend="memory"):
        self.backend = backend
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: dict):
        for handler in self._subscribers.get(event_type, []):
            asyncio.create_task(handler(payload))
        for pattern in self._subscribers:
            if pattern.endswith('*') and event_type.startswith(pattern[:-1]):
                for handler in self._subscribers[pattern]:
                    asyncio.create_task(handler(payload))
```

**特性**：支持通配符、可插拔后端（内存/Redis）。

---

### 3.3 技能注册与执行

**文件**：`core/skill_registry.py`, `core/skill_handler.py`

**SkillRegistry**：

```python
class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills = {}

    def scan(self):
        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            json_file = skill_path / "skill.json"
            if json_file.exists():
                meta = json.loads(json_file.read_text())
                self.skills[meta["name"]] = {
                    "path": skill_path,
                    "meta": meta,
                    "module": None
                }

    def get_skill(self, name: str) -> dict:
        return self.skills.get(name)
```

**SkillHandler**：

```python
class SkillHandler:
    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    async def execute(self, skill_name: str, method: str, params: dict) -> dict:
        skill = self.registry.get_skill(skill_name)
        if not skill:
            raise ValueError(f"技能 {skill_name} 不存在")
        if skill["module"] is None:
            module_path = skill["path"] / "implementation.py"
            spec = importlib.util.spec_from_file_location(skill_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            skill["module"] = module
        handler_class = getattr(skill["module"], "SkillHandler", None)
        if not handler_class:
            raise TypeError(f"技能 {skill_name} 没有 SkillHandler 类")
        instance = handler_class()
        func = getattr(instance, method, None)
        if not func:
            raise AttributeError(f"方法 {method} 不存在")
        return await func(**params) if asyncio.iscoroutinefunction(func) else func(**params)
```

**技能生命周期**：技能类应实现 `post_construct()` 和 `pre_destroy()`（可选）。

---

### 3.4 闭环引擎

**文件**：`core/closure_engine.py`

**职责**：加载 `config/closed_loops.yaml`，监听事件，执行条件图。
**修正**：构造函数注入 `skill_handler`。

```python
class ClosureEngine:
    def __init__(self, skill_handler: SkillHandler, config_path: str = "config/closed_loops.yaml"):
        self.skill_handler = skill_handler  # 注入依赖
        self.loops = self._load_yaml(config_path)
        self.event_bus = get_event_bus()
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        for loop_id, loop_def in self.loops.items():
            for event in loop_def.get("trigger_on", []):
                self.event_bus.subscribe(event, self._create_handler(loop_id))

    def _create_handler(self, loop_id):
        async def handler(payload):
            loop_def = self.loops[loop_id]
            await self._execute_loop(loop_def, payload)
        return handler

    async def _execute_loop(self, loop_def: dict, payload: dict):
        current_node = loop_def["entry"]
        context = {"payload": payload}
        for _ in range(loop_def.get("max_iterations", 10)):
            node = loop_def["nodes"][current_node]
            if node["type"] == "skill":
                result = await self.skill_handler.execute(
                    node["skill"], node["method"], context.get("last_result", {})
                )
                context["last_result"] = result
                current_node = node.get("next")
                if current_node is None:
                    break
            elif node["type"] == "condition":
                condition_key = self._evaluate_condition(node, context["last_result"])
                current_node = node["transitions"].get(condition_key)
                if not current_node:
                    break
            elif node["type"] == "end":
                break
```

---

### 3.5 工具注册与 Function Calling

**文件**：`core/function_calling.py`

**ToolRegistry**：

```python
class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name: str, description: str, parameters: dict, handler: Callable):
        self._tools[name] = {
            "handler": handler,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
        }

    def get_tool_schemas(self) -> list:
        return [info["schema"] for info in self._tools.values()]

    async def execute(self, tool_call: dict) -> dict:
        name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        handler = self._tools.get(name, {}).get("handler")
        if not handler:
            return {"error": f"工具 {name} 不存在"}
        result = handler(**arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return {"result": result}
```

**原生工具装饰器**：

```python
def tool(func):
    """装饰器：将普通函数注册为工具"""
    # 自动提取函数签名生成 schema
    # 实际使用中应由 AgentLoop 扫描 tools/ 目录并调用 ToolRegistry.register
    return func
```

---

### 3.6 上下文构建器

**文件**：`core/context_builder.py`

**职责**：从项目根目录的 `AGENTS.md`, `SOUL.md`, `USER.md` 构建系统提示词。
**修正**：复用 `AgentLoop` 中的 `SkillRegistry` 实例，避免重复扫描。

```python
class ContextBuilder:
    def __init__(self, skill_registry: SkillRegistry, profiles_dir: Path = Path("config/profiles")):
        self.skill_registry = skill_registry
        self.profiles_dir = profiles_dir

    def build_system_prompt(self) -> str:
        parts = []
        for filename in ["AGENTS.md", "SOUL.md", "USER.md"]:
            file_path = self.profiles_dir / filename
            if file_path.exists():
                parts.append(file_path.read_text(encoding="utf-8"))
        skills_desc = self._get_skills_description()
        parts.append(f"\n## 可用技能\n{skills_desc}")
        return "\n\n".join(parts)

    def _get_skills_description(self) -> str:
        lines = []
        for name, info in self.skill_registry.skills.items():
            lines.append(f"- {name}: {info['meta']['description']}")
        return "\n".join(lines)
```

---

### 3.7 技能治理

**文件**：`core/governance.py`

```python
class Governance:
    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry
        self.health_scores = {}

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float):
        old = self.health_scores.get(skill_name, 1.0)
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        new = 0.7 * success_factor + 0.3 * time_factor
        self.health_scores[skill_name] = 0.9 * old + 0.1 * new

    def check_dependencies(self):
        graph = {}
        for name, info in self.registry.skills.items():
            graph[name] = info["meta"].get("dependencies", [])
        return self._detect_cycles(graph)

    def auto_eliminate(self):
        for name, score in self.health_scores.items():
            if score < 0.6 and self._is_idle(name):
                get_event_bus().publish("skill.eliminate.proposal", {"skill": name})
```

### 3.8 MCP Client

**文件**：`core/mcp_client.py`

**职责**：通过 MCP 协议连接外部工具服务器，发现并调用远程工具。

**关键设计**：
- MCPServer：管理单个 MCP Server 连接（stdio 传输）
- MCPClient：管理多个 MCP Server 连接
- 懒加载：首次调用 AgentLoop.run() 时才初始化 MCP 连接
- 统一注册：远程工具通过 ToolRegistry 注册，LLM 统一调用

**支持的传输方式**：
- stdio（本地进程通信）✅ 已实现
- HTTP-SSE（远程服务）⚠️ 预留接口

**核心接口**：

```python
class MCPServer:
    def __init__(self, name: str, config: dict): ...
    async def connect(self) -> bool: ...
    async def list_tools(self) -> list[dict]: ...
    async def call_tool(self, name: str, args: dict) -> dict: ...
    async def disconnect(self) -> None: ...

class MCPClient:
    def __init__(self, config: dict): ...
    async def connect_all(self) -> None: ...
    async def disconnect_all(self) -> None: ...
    async def list_all_tools(self) -> dict[str, list]: ...
    def register_to_tool_registry(self, registry: ToolRegistry, tools: dict) -> None: ...
```

**配置方式**：

```yaml
# config/config.yaml
mcp:
  servers:
    filesystem:
      enabled: true
      transport: "stdio"
      command: "python"
      args: ["servers/filesystem_server.py", "."]
      description: "文件系统操作"
```

---

## 4. 数据流与交互

### 4.1 正常对话流程

```
用户 CLI 输入 → Channel CLI → AgentLoop.run()
    ↓
ContextBuilder 构建 system prompt（注入技能描述）
    ↓
AgentLoop 调用 LLM（携带所有工具 schemas，包括技能）
    ↓
LLM 返回 tool_calls → 执行工具（技能或原生工具）→ 回填结果 → 循环直到无 tool_calls
    ↓
最终回复 → Channel CLI → 用户
```

### 4.2 闭环触发流程

```
技能调用发布事件 → EventBus.publish()
    ↓
ClosureEngine 订阅事件 → 匹配闭环定义
    ↓
执行闭环节点（技能/条件）
    ↓
可能发布新事件 → 继续触发其他闭环
    ↓
最终完成
```

### 4.3 技能治理流程

```
技能调用 → Governance.update_health_score()
    ↓
定期（每小时）检查依赖、健康分
    ↓
若健康分过低 → 发布淘汰提案 → 用户确认后执行淘汰
```

---

## 5. 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 技能统一注册为工具 | 是 | LLM 通过统一机制调用，简化 Agent Loop |
| 事件总线后端 | 内存（默认），可扩展 Redis | 简化实现，性能足够；复杂场景可替换 |
| 会话存储 | 内存（默认），可扩展 Redis | 同上 |
| 技能加载 | 按需加载（首次调用时导入） | 减少启动时间，降低内存 |
| 工具调用 | 使用 LLM 原生 Function Calling | 避免不可靠的 JSON 解析 |
| 闭环配置 | YAML，路径 `config/closed_loops.yaml` | 可读性好，支持条件分支 |
| 技能数量限制 | 硬编码检查（注册时） | 防止技能膨胀 |
| 治理阈值 | 可配置 | 适应不同用户需求 |
| 工具定义格式 | MCP Tool 格式 | 业内标准，可跨项目复用 |
| 工具 Schema | OpenAI Function Calling | 事实标准，strict + additionalProperties |
| 事件格式 | CloudEvents 1.0 | CNCF 标准，事件驱动系统事实标准 |
| 错误格式 | JSON-RPC 2.0 | MCP 底层协议，标准错误码 |

---

## 6. 错误处理与可观测性

- **技能调用失败**：捕获异常，记录日志，返回错误信息，发布 `skill.failed` 事件。
- **闭环执行失败**：记录失败步骤，发布 `closure.failed` 事件，支持重试（由闭环定义中的 `max_iterations` 控制）。
- **工具调用失败**：返回 `{"error": ...}`，Agent Loop 继续运行（LLM 可看到错误并调整）。
- **结构化日志**：所有关键操作写入 `logs/plector.jsonl`，格式为 JSON Lines。

---

## 7. 测试策略

- **单元测试**：`pytest` + `asyncio`，模拟 LLM 和外部依赖。
- **集成测试**：启动完整 Agent Loop，验证真实闭环。
- **性能测试**：`locust` 模拟并发请求。
- **覆盖率目标**：≥ 80%。

---

## 8. 未来扩展点

- **分布式部署**：将事件总线、会话存储替换为 Redis，技能执行分布到多节点。
- **技能市场**：提供远程技能仓库，支持 `plector install <skill>`。
- **可视化 Dashboard**：基于 WebSocket 实时展示闭环执行和技能健康状态。

---

**文档状态**: 已定稿
**最后更新**: 2026-04-04

本文档与 BRD v1.1、PRD v1.2 共同构成 Plector 产品的完整规格。所有模块设计均满足需求，可进入 Alpha 开发阶段。

