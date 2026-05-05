# 6 断点修复方案

> 源文档：Obsidian 106_Plector最终实施计划方案.md
> 日期：2026-04-19
> 状态：待实施

---

## 断点全景

```
用户输入
  → _analyze_task_complexity()  🔴 B1: recommended_actions 被丢弃
  → _build_messages()           🔴 B2: context_refresher 未集成
  → LLM 推理 → tool_calls
  → _execute_tool_calls()       🟠 B3: ClosureEngine 事件缺失
  → 输出结果                    🟠 B4: Governance 未调用
                                🟡 B5: 工具结果未保存到记忆
                                🟡 B6: 中间件架构缺失
```

---

## B1: recommended_actions 未执行

**位置**: `core/agent_loop.py` — `_analyze_task_complexity()` 返回了推荐动作，但 `run_streaming()` 只检查 `is_complex` 并打日志，从未执行 `recommended_actions` 列表。

**修复**: 在 `run_streaming()` 中添加 `_execute_recommended_actions()` 方法，解析 `skill.method` 格式的动作名并调用 `skill_handler.execute()`。

**关键代码路径**: `agent_loop.py:500-536`

---

## B2: context_refresher 未集成

**位置**: `core/agent_loop.py` — `skills/context_refresher/` skill 已创建（4 个工具），但 AgentLoop 从未调用 `preserve`/`inject_context`。

**修复**:
1. 添加 `self.turn_count` 计数器
2. 每 10 轮调用 `_trigger_context_refresh()`
3. `_build_messages()` 中调用 `_inject_context_if_needed()` 注入保鲜上下文

---

## B3: ClosureEngine 事件缺失

**位置**: `core/closure_engine.py` — `_execute_loop()` 执行完成/失败后不发布事件。

**修复**: 在 `_execute_loop()` 末尾发布 `closure_loop.completed` 或 `closure_loop.failed` 事件。

**闭环配置扩展** (`config/closed_loops.yaml`):
- `skill_failure_loop` — 订阅 `skill.failed`，分类错误 → 重试/致命 → 触发自改进
- `context_refresh_loop` — 订阅 `turn.count_reached`，获取历史 → 保鲜上下文
- `complex_task_loop` — 订阅 `complexity.detected`，提取目标 → 编排工作流 → 执行

---

## B4: Governance 未与 AgentLoop 集成

**位置**: `core/governance.py` + `core/agent_loop.py` — Governance 已实现 3-color DFS 循环检测 + EMA 健康分，但 AgentLoop 从不调用 `update_health_score()`。

**修复**: 在工具执行成功/失败后调用 `governance.update_health_score()`，健康分 <0.5 时发布 `health.degraded` 事件。

---

## B5: 工具结果未保存到记忆

**位置**: `core/agent_loop.py:429-453` — 工具执行后有 `_save_tool_call()` 但结果不自动存入 memory/error_knowledge。

**修复**: 成功结果 → `memory.save_knowledge()`，失败结果 → `error_knowledge.store_error()` + 发布 `skill.failed` 事件。

---

## B6: 中间件架构缺失

**位置**: `core/agent_loop.py` — AgentLoop 是单链执行，无可插拔中间件。

**修复**: 引入 MiddlewareChain，5 个中间件按序执行：
1. LoggingMiddleware — 请求日志
2. SecurityMiddleware — 输入/输出安全检查
3. GovernanceMiddleware — 技能健康分监控
4. MemoryMiddleware — 工具结果自动记忆
5. SkillChainMiddleware — 技能联动触发

> **注意**: MiddlewareChain 已在 `develop/agency-orchestrator` 分支实现 (`core/middleware_chain.py`)。
