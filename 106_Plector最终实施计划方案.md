# Plector 最终实施计划方案

> 版本：3.0（最终版）
> 日期：2026-04-19
> 状态：基于系统断点深度分析的完整修复与升级方案

---

## 摘要

本方案基于对 Plector 当前系统断点的深度分析，结合竞品对比研究和功能联动设计，提出了一套完整的系统修复与升级计划。方案涵盖 **6 个 Critical 断点修复**、**4 个核心闭环打通**、**3 个架构升级**和 **6 个联动链实现**，确保 Plector 智能体系统从"能跑"到"好用"的质变。

---

## 第一部分：系统断点深度分析

### 1.1 断点全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Plector 系统断点全景                                 │
│                                                                             │
│  用户输入                                                                   │
│      │                                                                     │
│      ▼                                                                     │
│  ┌───────────────────┐                                                   │
│  │ _analyze_task_    │ ◄── 🔴 Critical #1                              │
│  │ complexity()       │     recommended_actions 未执行                      │
│  └─────────┬─────────┘                                                   │
│            │ 返回 complexity dict                                         │
│            │ 但结果被丢弃！                                                │
│            ▼                                                             │
│  ┌───────────────────┐                                                   │
│  │ run_streaming()  │                                                   │
│  │                   │     🔴 Critical #2                                  │
│  │ messages = await │     context_refresher 未集成                        │
│  │ _build_messages() │     每 N 轮自动保鲜未实现                          │
│  └─────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                   │
│  │ LLM 推理          │                                                   │
│  │ tool_calls        │                                                   │
│  └─────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                   │
│  │ _execute_tool_    │                                                   │
│  │ calls()           │     🟠 High #3                                   │
│  │                   │     ClosureEngine 事件缺失                        │
│  │ ClosureEngine     │     skill.failed 未发布                           │
│  │ (未集成)         │                                                   │
│  └─────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                   │
│  │ 输出结果          │                                                   │
│  └───────────────────┘                                                   │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  事件总线 (EventBus V2)                                                  │
│      │                                                                     │
│      │ 只有 2 个闭环订阅                                                  │
│      ▼                                                                     │
│  closed_loops.yaml                                                        │
│      ├── error_record_loop    (test.failed)                              │
│      └── health_check_loop    (health.degraded)                          │
│                                                                             │
│      ✗ 缺少: context_refresh_loop                                       │
│      ✗ 缺少: complex_task_loop                                           │
│      ✗ 缺少: skill_failure_loop                                         │
│      ✗ 缺少: self_improve_loop                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 断点详情分析

#### 🔴 Critical #1: recommended_actions 未执行

**位置**: `core/agent_loop.py:500-536`

```python
# 当前代码 (问题代码)
async def _analyze_task_complexity(self, user_input: str) -> dict:
    # ...
    if complex_score > simple_score:
        return {
            "is_complex": True,
            "complexity_level": "high",
            "recommended_actions": [
                "context_refresher.preserve",           # ← 声明了
                "agency_orchestrator.compose_workflow"  # ← 声明了
            ],
        }
    return {"is_complex": False, "complexity_level": "simple", "recommended_actions": []}

# 调用处 (问题代码)
async def run_streaming(self, user_input: str, session_id: str = None):
    complexity = await self._analyze_task_complexity(user_input)
    if complexity["is_complex"]:
        logger.info(f"检测到复杂任务: {complexity}")  # ← 只打日志！
        # recommended_actions 被丢弃！从未执行！
```

**根因分析**:
1. `_analyze_task_complexity` 返回了 `recommended_actions` 列表
2. `run_streaming` 只检查了 `is_complex` 字段并打日志
3. **从未实际调用** `recommended_actions` 中的动作
4. 这是设计意图与实现脱节的典型案例

**影响**:
- 复杂任务无法自动触发 `context_refresher.preserve`
- 复杂任务无法自动路由到 `agency_orchestrator`
- SOUL.md 中定义的决策树完全失效

---

#### 🔴 Critical #2: context_refresher 未集成

**位置**: `core/agent_loop.py` + `skills/context_refresher/`

**当前状态**:
- ✅ `context_refresher` skill 已创建（4 个工具）
- ✅ `ContextRefresher` 类已实现
- ✅ `GSDContext` 保鲜机制已实现
- ❌ **AgentLoop 中从未调用**
- ❌ **每 N 轮自动保鲜未实现**

**设计意图** (来自 `SOUL.md`):
```
任务进来
    ↓
["这个任务够复杂吗？"]
    ↓
如果复杂（多角色/多阶段/跨领域）
    → 调用 context_refresher 分析复杂度  ◄── 未实现
    → 调用 agency_orchestrator.compose_workflow 编排多角色  ◄── 未实现
    → 从 external-skills/ 匹配合适角色  ◄── 未实现
    → 多角色协作完成  ◄── 未实现
```

**根因分析**:
1. skill 已创建但未与 AgentLoop 集成
2. 没有实现"每 N 轮自动保鲜"触发器
3. `inject_context` 方法从未被调用
4. 没有实现对话轮次计数器

---

#### 🟠 High #3: ClosureEngine 事件缺失

**位置**: `core/closure_engine.py` + `config/closed_loops.yaml`

**当前状态**:
- ✅ `ClosureEngine` 类已实现
- ✅ `closed_loops.yaml` 配置已创建
- ✅ `error_record_loop` 已订阅 `test.failed`
- ❌ **没有发布执行完成事件**
- ❌ **没有发布执行失败事件**
- ❌ **skill.failed 事件无闭环**

**当前事件拓扑**:
```
事件总线
    │
    ├── test.failed ──► error_record_loop ──► error_knowledge.store_error
    │
    └── health.degraded ──► health_check_loop ──► health_monitor.check_health
```

**根因分析**:
1. `ClosureEngine._execute_loop` 执行后没有发布结果事件
2. `skill.failed` 事件没有被任何闭环订阅
3. 没有实现失败重试机制

---

#### 🟠 High #4: Governance 未与 AgentLoop 集成

**位置**: `core/governance.py`

**当前状态**:
- ✅ `Governance` 类已实现
- ✅ 技能健康分计算已实现
- ✅ 依赖循环检测已实现
- ❌ **AgentLoop 中从未调用**
- ❌ **技能失败时未更新健康分**
- ❌ **健康分低时无降级策略**

---

#### 🟡 Medium #5: 工具调用结果未保存到记忆

**位置**: `core/agent_loop.py:429-453`

**当前状态**:
- ✅ `_execute_single_tool` 已实现
- ✅ `_save_tool_call` 已实现
- ❌ **工具结果未自动存入 memory**
- ❌ **错误结果未存入 error_knowledge**

---

#### 🟡 Medium #6: 中间件架构缺失

**位置**: `core/agent_loop.py`

**当前状态**:
- AgentLoop 是单链执行，没有中间件概念
- 无法在执行流程中插入钩子
- 无法实现横切关注点分离

---

### 1.3 闭环状态矩阵

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          闭环状态矩阵                                      │
│                                                                             │
│  ┌────────────────┬────────────┬────────────┬────────────┬──────────────┐ │
│  │ 闭环             │ 触发器     │ 订阅      │ 执行       │ 结果反馈     │ │
│  ├────────────────┼────────────┼────────────┼────────────┼──────────────┤ │
│  │ error_record   │ test.failed│ ✅        │ ✅        │ ❌          │ │
│  │ health_check   │ health.deg │ ✅        │ ✅        │ ❌          │ │
│  ├────────────────┼────────────┼────────────┼────────────┼──────────────┤ │
│  │ context_refres│ turn % N   │ ❌        │ ❌        │ ❌          │ │
│  │ complex_task   │ complexity │ ❌        │ ❌        │ ❌          │ │
│  │ skill_failure │ skill.fail │ ❌        │ ❌        │ ❌          │ │
│  │ self_improve  │ error_accum│ ❌        │ ❌        │ ❌          │ │
│  └────────────────┴────────────┴────────────┴────────────┴──────────────┘ │
│                                                                             │
│  图例: ✅ 已实现  ❌ 未实现  🟡 部分实现                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第二部分：断点修复详细方案

### 2.1 Critical #1 修复: recommended_actions 执行引擎

#### 2.1.1 修复策略

在 `AgentLoop.run_streaming()` 中添加 `recommended_actions` 执行逻辑：

```python
# core/agent_loop.py 修复

class AgentLoop:
    def __init__(self, config: dict = None):
        # ... 现有初始化代码 ...
        self.turn_count = 0  # 新增：对话轮次计数器

    async def _execute_recommended_actions(
        self,
        complexity: dict,
        session_id: str,
        messages: list
    ) -> list:
        """
        执行复杂度分析返回的推荐动作

        Args:
            complexity: _analyze_task_complexity 返回的结果
            session_id: 会话 ID
            messages: 消息列表

        Returns:
            执行结果列表
        """
        results = []
        actions = complexity.get("recommended_actions", [])

        for action in actions:
            if "." not in action:
                continue

            skill_name, method_name = action.split(".", 1)

            try:
                if skill_name == "context_refresher":
                    # 调用上下文保鲜
                    conversation_history = await self._get_conversation_history(session_id)
                    result = await self.skill_handler.execute(
                        skill_name,
                        "preserve",
                        {
                            "session_id": session_id,
                            "conversation_history": conversation_history
                        }
                    )
                    results.append({
                        "action": action,
                        "success": result.get("success", False),
                        "result": result
                    })

                elif skill_name == "agency_orchestrator":
                    # 调用工作流编排
                    user_input = messages[-1]["content"] if messages else ""
                    result = await self.skill_handler.execute(
                        skill_name,
                        "compose_workflow",
                        {
                            "description": f"用户需求: {user_input}",
                            "provider": "claude-code"
                        }
                    )
                    results.append({
                        "action": action,
                        "success": result.get("success", False),
                        "result": result
                    })

            except Exception as e:
                logger.error(f"执行推荐动作 {action} 失败: {e}")
                results.append({
                    "action": action,
                    "success": False,
                    "error": str(e)
                })

        return results

    async def _get_conversation_history(self, session_id: str, limit: int = 20) -> list:
        """获取对话历史"""
        try:
            result = await self.skill_handler.execute(
                "memory",
                "get_conversation_history",
                {"session_id": session_id, "limit": limit}
            )
            return result.get("data", {}).get("messages", [])
        except Exception:
            return []
```

#### 2.1.2 集成到 run_streaming

```python
# core/agent_loop.py - run_streaming 修复

async def run_streaming(self, user_input: str, session_id: str = None):
    """流式执行 Agent 循环，yield 事件"""
    metrics = get_metrics_collector()
    start_time = time.perf_counter()

    if session_id is None:
        session_id = "default"

    # ══════════════════════════════════════════════════════════════
    # 修复 #1: 执行复杂度分析并执行推荐动作
    # ══════════════════════════════════════════════════════════════
    complexity = await self._analyze_task_complexity(user_input)
    if complexity["is_complex"]:
        logger.info(f"检测到复杂任务: {complexity}")

        # 执行推荐动作
        recommended_results = await self._execute_recommended_actions(
            complexity, session_id, []
        )

        # 发布推荐动作执行结果
        await self.event_bus.publish(
            "complexity.recommended_actions_executed",
            {
                "complexity": complexity,
                "results": recommended_results,
                "session_id": session_id
            },
            source="agent_loop"
        )

    # ══════════════════════════════════════════════════════════════
    # 处理图片命令
    # ══════════════════════════════════════════════════════════════
    result = await self._handle_image_command(user_input)
    if result:
        yield {"type": "done", "content": result[1]}
        return

    # 初始化和消息构建
    await self._ensure_mcp_initialized()
    await self._save_conversation(session_id, "user", user_input)
    self.turn_count += 1  # 轮次计数

    # ══════════════════════════════════════════════════════════════
    # 修复 #2: 每 N 轮触发上下文保鲜
    # ══════════════════════════════════════════════════════════════
    if self.turn_count % 10 == 0:  # 每 10 轮
        await self._trigger_context_refresh(session_id)

    messages = await self._build_messages(user_input, session_id)

    # 主执行循环 (保持不变)
    for _ in range(self.max_iterations):
        # ... 现有代码 ...
```

---

### 2.2 Critical #2 修复: context_refresher 集成

#### 2.2.1 实现自动保鲜触发器

```python
# core/agent_loop.py 新增方法

async def _trigger_context_refresh(self, session_id: str):
    """
    触发上下文保鲜

    流程:
    1. 获取对话历史
    2. 调用 context_refresher.preserve
    3. 发布保鲜事件
    """
    try:
        # 获取对话历史
        conversation_history = await self._get_conversation_history(session_id, limit=20)

        if not conversation_history:
            return

        # 调用上下文保鲜
        result = await self.skill_handler.execute(
            "context_refresher",
            "preserve",
            {
                "session_id": session_id,
                "conversation_history": conversation_history
            }
        )

        if result.get("success"):
            logger.info(f"上下文保鲜完成: session={session_id}")

            # 发布保鲜事件
            await self.event_bus.publish(
                "context.refreshed",
                {
                    "session_id": session_id,
                    "turn_count": self.turn_count,
                    "result": result.get("data", {})
                },
                source="agent_loop"
            )

    except Exception as e:
        logger.error(f"上下文保鲜失败: {e}")

async def _inject_context_if_needed(self, session_id: str, messages: list) -> list:
    """
    如果存在保鲜上下文，注入到消息中

    流程:
    1. 检查是否有保鲜上下文
    2. 获取上下文
    3. 注入到 system prompt 或首条消息
    """
    try:
        # 检查是否需要注入
        context_result = await self.skill_handler.execute(
            "context_refresher",
            "get_context",
            {"session_id": session_id}
        )

        if not context_result.get("success"):
            return messages

        context_data = context_result.get("data", {})
        if not context_data:
            return messages

        # 获取对话历史
        recent_turns = await self._get_conversation_history(session_id, limit=5)

        # 调用注入方法
        inject_result = await self.skill_handler.execute(
            "context_refresher",
            "inject_context",
            {
                "session_id": session_id,
                "recent_turns": recent_turns
            }
        )

        if inject_result.get("success"):
            injected_context = inject_result.get("data", {}).get("injected_context", "")

            # 注入到 system prompt
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += f"\n\n{injected_context}"

        return messages

    except Exception as e:
        logger.error(f"上下文注入失败: {e}")
        return messages
```

#### 2.2.2 更新 _build_messages

```python
# core/agent_loop.py - _build_messages 修复

async def _build_messages(self, user_input: str, session_id: str) -> list:
    """构建初始消息列表"""
    memory_context = await self._load_memory(session_id)
    system_prompt = self.context_builder.build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    if memory_context:
        messages[0]["content"] += "\n\n" + memory_context

    # ══════════════════════════════════════════════════════════════
    # 修复 #2: 注入保鲜上下文
    # ══════════════════════════════════════════════════════════════
    messages = await self._inject_context_if_needed(session_id, messages)

    messages.append({"role": "user", "content": user_input})
    return messages
```

---

### 2.3 High #3 修复: ClosureEngine 事件完善

#### 2.3.1 增强 ClosureEngine

```python
# core/closure_engine.py 修复

class ClosureEngine:
    def __init__(self, skill_handler, config_path: str = "config/closed_loops.yaml"):
        self.skill_handler = skill_handler
        with open(config_path, encoding="utf-8") as f:
            self.loops = yaml.safe_load(f)
        self.event_bus = get_event_bus()
        self._subscribe_to_events()

    async def _execute_loop(self, loop_def, payload):
        """执行闭环，返回执行结果"""
        current_node = loop_def["entry"]
        context = {
            "payload": payload.get("data", {}) if isinstance(payload, dict) and "data" in payload else payload,
            "last_result": None,
            "steps": [],
            "errors": []
        }

        try:
            for iteration in range(loop_def.get("max_iterations", 10)):
                node = loop_def["nodes"].get(current_node)
                if not node:
                    break

                if node["type"] == "skill":
                    params_from = node.get("params_from", "last_result")
                    if params_from == "payload" or context["last_result"] is None:
                        params = context.get("payload", {})
                    else:
                        params = context.get("last_result", {})

                    try:
                        result = await self.skill_handler.execute(
                            node["skill"],
                            node["method"],
                            params
                        )
                        context["last_result"] = result
                        context["steps"].append({
                            "skill": node["skill"],
                            "method": node["method"],
                            "success": result.get("success", False)
                        })

                        if not result.get("success"):
                            context["errors"].append({
                                "step": current_node,
                                "error": result.get("error", "unknown")
                            })

                    except Exception as e:
                        context["errors"].append({
                            "step": current_node,
                            "error": str(e)
                        })
                        context["last_result"] = {"success": False, "error": str(e)}

                    current_node = node.get("next")
                    if not current_node:
                        break

                elif node["type"] == "condition":
                    for key in node["transitions"]:
                        if key in context.get("last_result", {}):
                            current_node = node["transitions"][key]
                            break
                    else:
                        current_node = next(iter(node["transitions"].values()))
                    if not current_node:
                        break

                elif node["type"] == "end":
                    break

        except Exception as e:
            context["errors"].append({"step": current_node, "error": str(e)})

        # ══════════════════════════════════════════════════════════════
        # 发布执行完成事件
        # ══════════════════════════════════════════════════════════════
        loop_id = self._get_loop_id(loop_def)
        success = len(context["errors"]) == 0

        await self.event_bus.publish(
            "closure_loop.completed",
            {
                "loop_id": loop_id,
                "success": success,
                "steps": context["steps"],
                "errors": context["errors"],
                "result": context.get("last_result")
            },
            source="closure_engine"
        )

        if not success:
            await self.event_bus.publish(
                "closure_loop.failed",
                {
                    "loop_id": loop_id,
                    "errors": context["errors"]
                },
                source="closure_engine"
            )

        return context
```

#### 2.3.2 添加 skill_failure 闭环

```yaml
# config/closed_loops.yaml 新增

# ═══════════════════════════════════════════════════════════════════════════════
# 技能失败闭环
# ═══════════════════════════════════════════════════════════════════════════════
skill_failure_loop:
  trigger_on: ["skill.failed"]
  entry: "classify_failure"
  max_iterations: 3
  nodes:
    classify_failure:
      type: "skill"
      skill: "error_knowledge"
      method: "classify_error"
      params_from: "payload"
      next: "decide_recovery"

    decide_recovery:
      type: "condition"
      transitions:
        retryable: "retry_skill"
        fatal: "record_fatal"

    retry_skill:
      type: "skill"
      skill: "error_knowledge"
      method: "store_error"
      params_from: "payload"
      next: "end"

    record_fatal:
      type: "skill"
      skill: "error_knowledge"
      method: "store_error"
      params_from: "payload"
      next: "trigger_self_improve"

    trigger_self_improve:
      type: "condition"
      transitions:
        true: "call_self_improver"

    call_self_improver:
      type: "skill"
      skill: "self_improver"
      method: "start_upgrade"
      params_from: "payload"
      next: "end"

    end:
      type: "end"

# ═══════════════════════════════════════════════════════════════════════════════
# 上下文保鲜闭环
# ═══════════════════════════════════════════════════════════════════════════════
context_refresh_loop:
  trigger_on: ["turn.count_reached"]
  entry: "get_history"
  max_iterations: 2
  nodes:
    get_history:
      type: "skill"
      skill: "memory"
      method: "get_conversation_history"
      params_from: "payload"
      next: "preserve_context"

    preserve_context:
      type: "skill"
      skill: "context_refresher"
      method: "preserve"
      params_from: "last_result"
      next: "end"

    end:
      type: "end"

# ═══════════════════════════════════════════════════════════════════════════════
# 复杂任务闭环
# ═══════════════════════════════════════════════════════════════════════════════
complex_task_loop:
  trigger_on: ["complexity.detected"]
  entry: "extract_goal"
  max_iterations: 5
  nodes:
    extract_goal:
      type: "skill"
      skill: "context_refresher"
      method: "get_context"
      params_from: "payload"
      next: "compose_workflow"

    compose_workflow:
      type: "skill"
      skill: "agency_orchestrator"
      method: "compose_workflow"
      params_from: "last_result"
      next: "execute_workflow"

    execute_workflow:
      type: "skill"
      skill: "agency_orchestrator"
      method: "run_workflow"
      params_from: "last_result"
      next: "end"

    end:
      type: "end"
```

---

### 2.4 High #4 修复: Governance 集成

#### 2.4.1 创建 GovernanceMiddleware

```python
# core/middleware/governance_middleware.py

from core.governance import Governance
from core.skill_registry import SkillRegistry

class GovernanceMiddleware(AgentMiddleware):
    """
    治理中间件

    功能:
    1. 工具执行前后更新技能健康分
    2. 技能失败时发布 health.degraded 事件
    3. 技能健康分低时降级处理
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.governance = Governance(SkillRegistry(), event_bus)

        # 订阅事件
        self.event_bus.subscribe("tool.executed", self._on_tool_executed)
        self.event_bus.subscribe("tool.failed", self._on_tool_failed)

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 在执行前检查技能健康分
        for tool in ctx.tools:
            skill_name = self._extract_skill_name(tool)
            score = self.governance.get_health_score(skill_name)

            if score < 0.3:
                logger.warning(f"技能 {skill_name} 健康分过低: {score}")
                ctx.metadata["degraded_skills"] = ctx.metadata.get("degraded_skills", [])
                ctx.metadata["degraded_skills"].append(skill_name)

        # 执行
        result = await next_handler()

        return result

    def _extract_skill_name(self, tool: dict) -> str:
        """从工具定义提取技能名"""
        name = tool.get("name", "")
        # skill_method → skill
        if "_" in name:
            return name.rsplit("_", 1)[0]
        return name

    async def _on_tool_executed(self, event: dict):
        """工具执行完成"""
        data = event.get("data", {})
        skill_name = data.get("skill", "")
        duration = data.get("duration_ms", 0)

        if skill_name:
            self.governance.update_health_score(skill_name, success=True, duration_ms=duration)

    async def _on_tool_failed(self, event: dict):
        """工具执行失败"""
        data = event.get("data", {})
        skill_name = data.get("skill", "")
        duration = data.get("duration_ms", 0)

        if skill_name:
            self.governance.update_health_score(skill_name, success=False, duration_ms=duration)

            # 检查是否需要发布健康分下降事件
            score = self.governance.get_health_score(skill_name)
            if score < 0.5:
                await self.event_bus.publish(
                    "health.degraded",
                    {"skill": skill_name, "score": score, "reason": "skill_failure"},
                    source="governance"
                )
```

#### 2.4.2 集成到 AgentLoop

```python
# core/agent_loop.py - __init__ 修改

class AgentLoop:
    def __init__(self, config: dict = None):
        # ... 现有初始化代码 ...
        self.governance_middleware = GovernanceMiddleware(self.event_bus)
```

---

### 2.5 Medium #5 修复: 工具结果自动保存

#### 2.5.1 创建工具结果保存中间件

```python
# core/middleware/memory_middleware.py

class MemoryMiddleware(AgentMiddleware):
    """
    记忆中间件

    功能:
    1. 工具执行后自动保存结果到 memory
    2. 错误结果自动保存到 error_knowledge
    3. 发布工具完成事件
    """

    def __init__(self, skill_handler, event_bus):
        self.skill_handler = skill_handler
        self.event_bus = event_bus

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        result = await next_handler()

        # 发布工具执行事件
        for tool_result in ctx.metadata.get("tool_results", []):
            await self._save_tool_result(tool_result)

        return result

    async def _save_tool_result(self, result: dict):
        """保存工具结果"""
        tool_name = result.get("tool", "")
        success = result.get("success", False)
        error = result.get("error", "")
        data = result.get("data", {})

        # 发布事件
        event_type = "tool.executed" if success else "tool.failed"
        await self.event_bus.publish(
            event_type,
            {
                "tool": tool_name,
                "success": success,
                "error": error,
                "data": data
            },
            source="memory_middleware"
        )

        # 成功结果存入 memory
        if success and data:
            try:
                await self.skill_handler.execute(
                    "memory",
                    "save_knowledge",
                    {
                        "topic": f"tool_result:{tool_name}",
                        "content": str(data)[:500],
                        "source": "tool_execution"
                    }
                )
            except Exception:
                pass

        # 失败结果存入 error_knowledge
        if not success and error:
            try:
                await self.skill_handler.execute(
                    "error_knowledge",
                    "store_error",
                    {"error": f"{tool_name}: {error}"}
                )

                # 发布 skill.failed 事件触发闭环
                await self.event_bus.publish(
                    "skill.failed",
                    {
                        "skill": tool_name,
                        "error": error,
                        "data": data
                    },
                    source="memory_middleware"
                )
            except Exception:
                pass
```

---

## 第三部分：闭环架构设计

### 3.1 完整事件拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Plector 完整事件拓扑                               │
│                                                                             │
│  ═══════════════════════════ 事件总线 (EventBus V2) ════════════════════════ │
│                                                                             │
│  核心事件                                                                   │
│  ─────────                                                                   │
│  ├── user.input                    用户输入                                  │
│  ├── complexity.analyzed           复杂度分析完成                          │
│  ├── complexity.recommended_actions_executed  推荐动作执行                  │
│  ├── turn.count_reached             轮次达到阈值                             │
│  ├── context.refreshed               上下文保鲜完成                            │
│  │                                                                             │
│  工具执行事件                                                               │
│  ├── tool.executing                工具开始执行                              │
│  ├── tool.executed                 工具执行完成                              │
│  ├── tool.failed                   工具执行失败                              │
│  │                                                                             │
│  闭环事件                                                                   │
│  ├── test.failed                   测试失败 ──────────────────────────┐     │
│  ├── skill.failed                  技能失败 ──────────────────────────┼─►   │
│  ├── health.degraded              健康分下降 ────────────────────────┼─►   │
│  │                                       │                           │     │
│  │                                       ▼                           ▼     │
│  │                              ┌─────────────────┐        ┌─────────────────┐│
│  │                              │ ClosureEngine   │        │ ClosureEngine   ││
│  │                              │                 │        │                 ││
│  │                              │ error_record_   │        │ health_check_   ││
│  │                              │ loop           │        │ loop           ││
│  │                              └────────┬────────┘        └────────┬────────┘│
│  │                                       │                          │         │
│  │                                       ▼                          ▼         │
│  │                              ┌─────────────────┐        ┌─────────────────┐│
│  │                              │ error_knowledge │        │ health_monitor  ││
│  │                              │ .store_error   │        │ .check_health   ││
│  │                              └─────────────────┘        └─────────────────┘│
│  │                                                                             │
│  闭环完成事件                                                               │
│  ├── closure_loop.completed    闭环执行完成                                │
│  ├── closure_loop.failed       闭环执行失败                                │
│  │                                                                             │
│  自我改进事件                                                               │
│  ├── self_improve.started      自改进开始                                   │
│  ├── self_improve.task_assigned  任务分配                                  │
│  ├── self_improve.task_completed 任务完成                                   │
│  └── self_improve.upgrade_completed 升级完成                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 闭环依赖图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          闭环依赖图                                          │
│                                                                             │
│  ┌─────────────┐                                                          │
│  │ test.failed │                                                          │
│  └──────┬──────┘                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────┐                                  │
│  │         error_record_loop           │                                  │
│  │                                     │                                  │
│  │  test.failed ──► store_error ──► classify_error                       │
│  │                                     │                                  │
│  │                                     ▼                                   │
│  │                              closure_loop.completed                     │
│  └─────────────────────────────────────┘                                  │
│                                                                             │
│  ┌─────────────┐                                                          │
│  │skill.failed │                                                          │
│  └──────┬──────┘                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────┐                                  │
│  │         skill_failure_loop          │                                  │
│  │                                     │                                  │
│  │  skill.failed ──► classify ──► decide ──► [retry/fatal]               │
│  │                                              │                        │
│  │                                              ▼                        │
│  │                                     call_self_improver                │
│  │                                              │                        │
│  │                                              ▼                        │
│  │                                     self_improve_loop                 │
│  └─────────────────────────────────────┘                                  │
│                                                                             │
│  ┌─────────────┐                                                          │
│  │turn % N==0 │                                                          │
│  └──────┬──────┘                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────┐                                  │
│  │         context_refresh_loop        │                                  │
│  │                                     │                                  │
│  │  turn.count ──► get_history ──► preserve_context                     │
│  │                                     │                                  │
│  │                                     ▼                                   │
│  │                              closure_loop.completed                     │
│  └─────────────────────────────────────┘                                  │
│                                                                             │
│  ┌─────────────┐                                                          │
│  │complex.detec│                                                          │
│  └──────┬──────┘                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────────────────────────────┐                                  │
│  │         complex_task_loop          │                                  │
│  │                                     │                                  │
│  │  complexity ──► extract ──► compose ──► execute                       │
│  │                                     │                                  │
│  │                                     ▼                                   │
│  │                              closure_loop.completed                     │
│  └─────────────────────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第四部分：中间件链架构

### 4.1 完整中间件链

```python
# core/middleware_chain.py

class MiddlewareChain:
    """
    Plector 中间件链

    执行顺序（从左到右）：
    1. LoggingMiddleware - 请求日志
    2. SecurityMiddleware - 安全检查
    3. GovernanceMiddleware - 技能健康分
    4. MemoryMiddleware - 结果记忆
    5. SkillChainMiddleware - 技能联动
    6. AgentExecution - Agent 执行
    """

    def __init__(self, config: dict):
        self.middlewares: list[AgentMiddleware] = []
        self._init_middlewares(config)

    def _init_middlewares(self, config: dict):
        """初始化所有中间件"""
        # 1. 日志中间件
        self.middlewares.append(LoggingMiddleware())

        # 2. 安全中间件
        self.middlewares.append(SecurityMiddleware(
            sanitizer=InputSanitizer()
        ))

        # 3. 治理中间件
        event_bus = get_event_bus()
        self.middlewares.append(GovernanceMiddleware(event_bus))

        # 4. 记忆中间件
        self.middlewares.append(MemoryMiddleware(
            skill_handler=self._skill_handler,
            event_bus=event_bus
        ))

        # 5. 技能联动中间件
        self.middlewares.append(SkillChainMiddleware(
            chains=self._init_skill_chains()
        ))

    async def execute(self, ctx: AgentContext) -> dict:
        """执行中间件链"""

        async def chain(index: int) -> dict:
            if index >= len(self.middlewares):
                return await self._execute_agent(ctx)

            middleware = self.middlewares[index]
            return await middleware.process(ctx, lambda: chain(index + 1))

        return await chain(0)
```

### 4.2 AgentContext 扩展

```python
# core/agent_context.py

from pydantic import BaseModel
from typing import Optional, Any

class AgentContext(BaseModel):
    """Agent 执行上下文"""

    # 基础信息
    session_id: str
    user_id: Optional[str] = None
    workspace_id: str = "default"

    # 消息和工具
    messages: list[dict] = []
    tools: list[dict] = []

    # 复杂度分析
    complexity: Optional[dict] = None
    recommended_actions_executed: list[dict] = []

    # 上下文保鲜
    context_refreshed: bool = False
    injected_context: Optional[str] = None

    # 记忆
    memory_results: list[dict] = []

    # 工具执行
    tool_results: list[dict] = []
    degraded_skills: list[str] = []

    # 状态
    turn_count: int = 0
    metadata: dict = {}

    class Config:
        arbitrary_types_allowed = True
```

---

## 第五部分：完整实施计划

### 5.1 实施路线图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Plector v2.x 完整实施路线图                          │
│                                                                             │
│  Sprint 1 (1-2周): Critical 断点修复                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Task 1.1: recommended_actions 执行引擎 (3天)                        │   │
│  │ Task 1.2: context_refresher 集成 (3天)                           │   │
│  │ Task 1.3: ClosureEngine 事件完善 (2天)                            │   │
│  │ Task 1.4: 单元测试 + 集成测试 (2天)                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  Sprint 2 (3-4周): Governance 与记忆集成                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Task 2.1: GovernanceMiddleware 实现 (3天)                        │   │
│  │ Task 2.2: MemoryMiddleware 实现 (2天)                            │   │
│  │ Task 2.3: 技能联动链初版 (3天)                                    │   │
│  │ Task 2.4: 新增闭环配置 (2天)                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  Sprint 3 (5-6周): 中间件链架构                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Task 3.1: MiddlewareChain 基类 (2天)                             │   │
│  │ Task 3.2: 中间件集成到 AgentLoop (2天)                            │   │
│  │ Task 3.3: SkillChainMiddleware (3天)                             │   │
│  │ Task 3.4: 端到端测试 (2天)                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  Sprint 4 (7-8周): 高级闭环                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Task 4.1: complex_task_loop 实现 (3天)                          │   │
│  │ Task 4.2: skill_failure_loop 实现 (3天)                         │   │
│  │ Task 4.3: self_improve_loop 实现 (3天)                           │   │
│  │ Task 4.4: 自改进效果验证 (2天)                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Sprint 5+ (9周+): 持续优化                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Task 5.1: 性能优化                                                │   │
│  │ Task 5.2: 监控面板                                                │   │
│  │ Task 5.3: 文档完善                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Sprint 1 详细任务

#### Task 1.1: recommended_actions 执行引擎

**目标**: 实现复杂度分析后自动执行推荐动作

**代码变更**:
```python
# core/agent_loop.py
# 新增方法: _execute_recommended_actions()
# 修改方法: run_streaming()
```

**验收标准**:
- [ ] 复杂任务自动触发 context_refresher.preserve
- [ ] 复杂任务自动触发 agency_orchestrator.compose_workflow
- [ ] 推荐动作执行结果发布到事件总线

**测试用例**:
```python
# tests/test_complexity_action_execution.py

async def test_complex_task_triggers_context_refresh():
    """复杂任务应自动触发上下文保鲜"""
    agent = AgentLoop()

    # 模拟复杂任务输入
    result = agent._analyze_task_complexity("帮我规划一个多角色协作的项目")

    assert result["is_complex"] == True
    assert "context_refresher.preserve" in result["recommended_actions"]
    assert "agency_orchestrator.compose_workflow" in result["recommended_actions"]

async def test_recommended_actions_executed():
    """推荐动作应被实际执行"""
    agent = AgentLoop()
    session_id = "test_session"

    complexity = {"is_complex": True, "recommended_actions": ["context_refresher.preserve"]}

    results = await agent._execute_recommended_actions(complexity, session_id, [])

    assert len(results) == 1
    assert results[0]["action"] == "context_refresher.preserve"
```

---

#### Task 1.2: context_refresher 集成

**目标**: 每 N 轮自动触发上下文保鲜

**代码变更**:
```python
# core/agent_loop.py
# 新增方法: _trigger_context_refresh(), _inject_context_if_needed()
# 修改方法: _build_messages(), run_streaming()
# 新增字段: self.turn_count
```

**验收标准**:
- [ ] turn_count 正确计数
- [ ] 每 10 轮自动触发保鲜
- [ ] 保鲜上下文正确注入到消息

**测试用例**:
```python
# tests/test_context_refresh.py

async def test_turn_count_increments():
    """轮次计数应正确递增"""
    agent = AgentLoop()
    assert agent.turn_count == 0

    # 模拟执行
    agent.turn_count += 1
    assert agent.turn_count == 1

async def test_context_refresh_at_10_turns():
    """第 10 轮应触发上下文保鲜"""
    agent = AgentLoop()
    agent.turn_count = 9  # 即将达到第 10 轮

    # 模拟用户输入
    await agent._trigger_context_refresh("test_session")

    # 验证 context_refresher 被调用
    # ... 具体断言 ...
```

---

#### Task 1.3: ClosureEngine 事件完善

**目标**: 闭环执行后发布完成/失败事件

**代码变更**:
```python
# core/closure_engine.py
# 修改方法: _execute_loop()
# 新增发布事件: closure_loop.completed, closure_loop.failed
```

**验收标准**:
- [ ] 闭环执行完成发布 closure_loop.completed
- [ ] 闭环执行失败发布 closure_loop.failed
- [ ] 事件包含 steps 和 errors 信息

---

### 5.3 Sprint 2 详细任务

#### Task 2.1: GovernanceMiddleware 实现

**目标**: 技能健康分全程监控

**代码变更**:
```python
# core/middleware/governance_middleware.py (新建)
# core/agent_loop.py (集成)
```

**验收标准**:
- [ ] 工具执行前后更新健康分
- [ ] 健康分低于 0.3 标记为降级
- [ ] 健康分低于 0.5 发布 health.degraded

---

#### Task 2.2: MemoryMiddleware 实现

**目标**: 工具结果自动记忆

**代码变更**:
```python
# core/middleware/memory_middleware.py (新建)
```

**验收标准**:
- [ ] 成功结果存入 memory
- [ ] 失败结果存入 error_knowledge
- [ ] 发布 tool.executed / tool.failed 事件

---

### 5.4 里程碑验收

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          里程碑验收检查点                                    │
│                                                                             │
│  Milestone 1: 断点修复完成 (Sprint 1 结束)                                   │
│  ────────────────────────────────────────────────────────                    │
│  ✅ recommended_actions 已执行                                                │
│  ✅ context_refresher 每 10 轮自动保鲜                                       │
│  ✅ ClosureEngine 发布完成事件                                               │
│  ✅ 所有 Critical 断点已修复                                                 │
│                                                                             │
│  Milestone 2: 闭环打通 (Sprint 2 结束)                                       │
│  ────────────────────────────────────────────────────────                    │
│  ✅ GovernanceMiddleware 集成                                               │
│  ✅ MemoryMiddleware 集成                                                   │
│  ✅ 新闭环: context_refresh_loop                                            │
│  ✅ 新闭环: skill_failure_loop                                              │
│                                                                             │
│  Milestone 3: 中间件链完成 (Sprint 3 结束)                                  │
│  ────────────────────────────────────────────────────────                    │
│  ✅ MiddlewareChain 基类实现                                                │
│  ✅ 5 个中间件串联执行                                                      │
│  ✅ AgentContext 正确传递                                                   │
│                                                                             │
│  Milestone 4: 高级闭环 (Sprint 4 结束)                                       │
│  ────────────────────────────────────────────────────────                    │
│  ✅ complex_task_loop 实现                                                  │
│  ✅ skill_failure_loop 实现                                                │
│  ✅ self_improve_loop 集成                                                 │
│  ✅ 自改进闭环验证                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第六部分：测试方案

### 6.1 测试金字塔

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          测试金字塔                                          │
│                                                                             │
│                                    ▲                                        │
│                                   /│\                                       │
│                                  / │ \                                      │
│                                 /  │  \                                     │
│                                /   │   \                                    │
│                               /███████\                                    │
│                              /  E2E     \                                   │
│                             /  测试       \                                  │
│                            /───────────────\                                 │
│                           /   集成测试      \                                │
│                          /─────────────────\                                │
│                         /     单元测试        \                               │
│                        /─────────────────────────\                             │
│                                                                             │
│  比例: 70% 单元测试 / 20% 集成测试 / 10% E2E 测试                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 单元测试用例

```python
# tests/test_agent_loop/
# ├── test_complexity_analysis.py
# ├── test_context_refresh.py
# ├── test_tool_execution.py
# └── test_event_publishing.py

# tests/test_closure_engine/
# ├── test_error_record_loop.py
# ├── test_skill_failure_loop.py
# ├── test_context_refresh_loop.py
# └── test_event_publishing.py

# tests/test_middleware/
# ├── test_governance_middleware.py
# ├── test_memory_middleware.py
# ├── test_security_middleware.py
# └── test_middleware_chain.py
```

### 6.3 E2E 测试场景

```python
# tests/e2e/
# ├── test_complex_task_flow.py
# ├── test_error_recovery_flow.py
# └── test_self_improve_flow.py

"""
E2E 测试场景 1: 复杂任务流程

步骤:
1. 用户输入复杂任务
2. 系统分析复杂度
3. 触发 context_refresher.preserve
4. 触发 agency_orchestrator.compose_workflow
5. 执行工作流
6. 返回结果

预期:
- context_refreshed 事件被发布
- agency 工作流被创建和执行
- 任务成功完成
"""

"""
E2E 测试场景 2: 错误自愈流程

步骤:
1. 执行技能失败
2. skill.failed 事件发布
3. skill_failure_loop 触发
4. error_knowledge 存储错误
5. 分类错误类型
6. 触发 self_improver (如果致命)

预期:
- 错误被正确分类
- 致命错误触发自改进
"""
```

---

## 第七部分：监控与可观测性

### 7.1 关键指标

```python
# core/metrics.py 扩展

CLOSED_LOOP_METRICS = {
    # 闭环执行
    "closure_loop.executed.total": "闭环执行总数",
    "closure_loop.executed.success": "闭环成功数",
    "closure_loop.executed.failed": "闭环失败数",
    "closure_loop.duration.seconds": "闭环执行时长",

    # 上下文保鲜
    "context.refresh.total": "上下文保鲜触发次数",
    "context.refresh.success": "保鲜成功次数",
    "context.goal_version": "目标版本分布",

    # 技能健康
    "skill.health.<name>.score": "技能健康分",
    "skill.health.degraded.total": "技能降级次数",

    # 复杂度分析
    "complexity.detected.total": "复杂任务检测数",
    "complexity.actions.executed": "推荐动作执行数",
}
```

### 7.2 监控面板

```yaml
# dashboard/闭环监控.json

{
  "panels": [
    {
      "title": "闭环执行状态",
      "type": "stat",
      "targets": [
        "closure_loop.executed.success / closure_loop.executed.total"
      ],
      "thresholds": {
        "warning": 0.8,
        "critical": 0.5
      }
    },
    {
      "title": "上下文保鲜率",
      "type": "gauge",
      "targets": [
        "context.refresh.success / context.refresh.total"
      ]
    },
    {
      "title": "技能健康分分布",
      "type": "histogram",
      "targets": [
        "skill_health_scores"
      ]
    },
    {
      "title": "闭环执行时长",
      "type": "heatmap",
      "targets": [
        "closure_loop.duration.seconds"
      ]
    }
  ]
}
```

---

## 第八部分：风险与缓解

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 中间件链性能影响 | 中 | 低 | 异步执行，延迟监控 |
| 闭环死循环 | 高 | 中 | max_iterations 限制 |
| 事件风暴 | 中 | 低 | 事件过滤，合并发送 |
| 记忆存储爆炸 | 中 | 中 | 遗忘曲线自动清理 |

### 8.2 项目风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 范围蔓延 | 高 | 中 | 严格变更控制 |
| 测试覆盖不足 | 高 | 中 | 70% 覆盖率要求 |
| 集成回归 | 中 | 低 | 自动化 CI/CD |

---

## 第九部分：总结

### 9.1 修复后的系统闭环

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Plector 完整闭环 (修复后)                           │
│                                                                             │
│  用户输入                                                                   │
│      │                                                                     │
│      ▼                                                                     │
│  ┌───────────────────────────────────────────┐                             │
│  │ _analyze_task_complexity()              │                             │
│  │  ↓                                        │                             │
│  │ recommended_actions 执行 ──────────────────┼──► context_refresher       │
│  │                                         │     preserve (每 10 轮)     │
│  │                                         │                             │
│  │                                         └──► agency_orchestrator      │
│  │                                               compose_workflow         │
│  └───────────────────────────┬───────────────────────┘                       │
│                              │                                               │
│  ┌───────────────────────────▼───────────────────────┐                       │
│  │ _inject_context_if_needed()                    │                       │
│  │  注入保鲜上下文                                │                       │
│  └───────────────────────────┬───────────────────┘                       │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────┐                             │
│  │ AgentLoop._execute_tool_calls()          │                             │
│  │  ↓                                        │                             │
│  │ GovernanceMiddleware - 更新健康分          │                             │
│  │  ↓                                        │                             │
│  │ MemoryMiddleware - 保存结果                │                             │
│  │  ↓                                        │                             │
│  │ SkillChainMiddleware - 触发联动            │                             │
│  └───────────────────────────┬───────────────┘                             │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────┐                             │
│  │ 事件总线 (EventBus V2)                  │                             │
│  │  ↓                                      │                             │
│  │ ClosureEngine                           │                             │
│  │  ├── skill_failure_loop ──► self_improve│                             │
│  │  ├── context_refresh_loop ──► 上下文保鲜│                             │
│  │  └── complex_task_loop ──► agency       │                             │
│  └───────────────────────────────────────────┘                             │
│                                                                             │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  ✅ 所有 Critical 断点已修复                                               │
│  ✅ 4 个新闭环已打通                                                       │
│  ✅ 5 个中间件已串联                                                      │
│  ✅ 事件驱动闭环自愈                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 关键改进点

1. **recommended_actions 执行引擎**: 复杂度分析结果不再被丢弃
2. **context_refresher 集成**: 每 10 轮自动保鲜，上下文不遗忘
3. **ClosureEngine 事件完善**: 闭环执行结果可追踪
4. **GovernanceMiddleware**: 技能健康分全程监控
5. **MemoryMiddleware**: 工具结果自动记忆
6. **完整中间件链**: 横切关注点分离，可扩展

### 9.3 预期效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 复杂任务处理率 | 0% | 95% |
| 上下文保鲜率 | 0% | 100% |
| 错误自愈率 | 0% | 60% |
| 技能健康监控 | 无 | 完整 |
| 闭环可观测性 | 低 | 高 |

---

## 附录

### A. 参考文档

- [87_Plector_技能与MCP系统深度分析.md](../87_Plector_技能与MCP系统深度分析.md)
- [93_Plector与同类开源Agent项目对比.md](../93_Plector与同类开源Agent项目对比.md)
- [97_Plector技能与架构增强方案.md](../97_Plector技能与架构增强方案.md)
- [102_Plector未来升级改造演进方案.md](../102_Plector未来升级改造演进方案.md)
- [103_Plector深度技术分析报告.md](../103_Plector深度技术分析报告.md)
- [104_Plector_v2.x_详细实施计划.md](../104_Plector_v2.x_详细实施计划.md)
- [105_Plector功能联动融合方案.md](../105_Plector功能联动融合方案.md)

### B. 代码位置索引

| 文件 | 说明 |
|------|------|
| `core/agent_loop.py` | AgentLoop 主循环（修复点）|
| `core/closure_engine.py` | 闭环引擎（修复点）|
| `core/governance.py` | 治理模块 |
| `core/middleware/governance_middleware.py` | 治理中间件（新建）|
| `core/middleware/memory_middleware.py` | 记忆中间件（新建）|
| `core/middleware_chain.py` | 中间件链（新建）|
| `config/closed_loops.yaml` | 闭环配置（扩展）|
| `skills/context_refresher/` | 上下文保鲜技能 |

---

#Plector #最终实施计划 #断点修复 #闭环 #中间件
