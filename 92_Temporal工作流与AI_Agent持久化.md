# Temporal 工作流引擎与 AI Agent 持久化

> 来源：联网调研 + Temporal 官方文档
> 更新：2026-04-19

---

## 一、Temporal 核心概念

### 1.1 什么是 Temporal

Temporal 是一个**持久化执行引擎**，让长时间运行的工作流能够容错、持久化、可观测。它不是消息队列，不是编排框架，而是** durable execution platform**。

### 1.2 核心概念映射

| 传统概念 | Temporal 概念 | 说明 |
|---------|--------------|------|
| 函数调用 | **Workflow** | 长时间运行的逻辑 |
| 微服务 | **Activity** | 具体执行的任务单元 |
| 数据库事务 | **Workflow Execution** | 完整业务流程 |
| 消息队列 | **Event History** | 工作流历史记录 |
| 幂等处理 | **Determinism** | 确定性执行保证 |

### 1.3 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Temporal 架构                         │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Temporal Server (Cluster)                         ││
│  │  ├── Control Plane (API, 操作协调)                  ││
│  │  ├── Data Plane (事件历史, 持久化)                  ││
│  │  └── Matching Service (任务分发)                   ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Worker 1    │  │  Worker 2    │  │  Worker N    │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │  │
│  │  │Workflow│  │  │  │Workflow│  │  │  │Workflow│  │  │
│  │  │ Code   │  │  │  │ Code   │  │  │  │ Code   │  │  │
│  │  └────────┘  │  │  └────────┘  │  │  └────────┘  │  │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │  │
│  │  │Activity│  │  │  │Activity│  │  │  │Activity│  │  │
│  │  │ Code   │  │  │  │ Code   │  │  │  │ Code   │  │  │
│  │  └────────┘  │  │  └────────┘  │  │  └────────┘  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 二、Durable Execution 原理

### 2.1 事件溯源

Temporal 使用**事件溯源 (Event Sourcing)** 模式：

```
┌─────────────────────────────────────────────────────────┐
│                    事件历史 (Event History)              │
│                                                         │
│  Event 1: WorkflowStarted                               │
│  Event 2: ActivityScheduled {"activity": "search"}     │
│  Event 3: ActivityCompleted {"result": "..."}          │
│  Event 4: ActivityScheduled {"activity": "analyze"}   │
│  Event 5: WorkflowCompleted                             │
│                                                         │
│  → 如果 Activity 失败，Worker 重启后读取历史             │
│  → 只需重新执行未完成的 Activity                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 确定性重放

**关键特性**：Workflow 代码必须是**确定性的**

```python
# ✓ 正确：在 Workflow 外获取当前时间
current_time = asyncio.get_event_loop().time()

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, name: str):
        # 确定性操作
        result = await execute_activity(
            my_activity,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return result
```

### 2.3 自动重试

```python
@activity.defn
async def unreliable_activity() -> str:
    """自动重试的活动"""
    result = await call_unreliable_api()
    return result

# 配置重试策略
@activity.defn
@activity.retry(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(minutes=1),
    backoff_coefficient=2.0,
    non_retryable_error_types=["ValidationError"],
)
async def reliable_activity() -> str:
    ...
```

---

## 三、AI Agent 持久化方案

### 3.1 为什么 AI Agent 需要 Temporal

| 问题 | 传统方案 | Temporal 方案 |
|------|---------|--------------|
| LLM API 超时 | 手动重试 | 自动重试 |
| Worker 重启 | 丢失状态 | 完整恢复 |
| 长任务中断 | 无法续跑 | 断点续跑 |
| 人工审批 | 阻塞等待 | 异步信号 |

### 3.2 集成模式

```
┌─────────────────────────────────────────────────────────┐
│              Temporal + AI Agent 架构                   │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Workflow (协调逻辑 - 确定性)                      ││
│  │  • 定义执行流程                                     ││
│  │  • 协调多个 Activity                                ││
│  │  • 处理信号和查询                                   ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Activity (非确定性工作 - LLM 调用)                  ││
│  │  • LLM API 调用                                     ││
│  │  • 工具执行                                         ││
│  │  • 外部服务交互                                     ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Event History (持久化)                             ││
│  │  • 保存完整执行历史                                 ││
│  │  • 支持任意时间点恢复                               ││
│  │  • 审计和调试                                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 3.3 Pydantic AI + Temporal 集成

**安装**：
```bash
pip install pydantic-ai[temporal]
```

**代码示例**：
```python
from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent

# 1. 定义普通 Pydantic AI Agent
agent = Agent(
    model='anthropic:claude-sonnet-4-5',
    system_prompt='You are a helpful research assistant.',
)

# 2. 包装为 Temporal Agent
research_agent = TemporalAgent(agent)


# 3. 定义 Workflow
@workflow.defn
class ResearchCrewWorkflow:
    @workflow.run
    async def run(self, topic: str) -> ResearchReport:
        # 并行执行多个研究任务
        parallel_results = await asyncio.gather(
            research_agent.run(f"Research {topic} from academic sources"),
            research_agent.run(f"Research {topic} from industry news"),
            research_agent.run(f"Research {topic} from technical blogs"),
        )

        # 综合分析
        synthesis = await research_agent.run(
            f"Summarize and synthesize these findings about {topic}:\n"
            f"{parallel_results}"
        )

        return ResearchReport(content=synthesis.output)
```

### 3.4 多 Agent 编排示例

```python
@workflow.defn
class DinnerBotWorkflow:
    @workflow.run
    async def run(self, user_message: str) -> DinnerRecommendations:
        # 1. 调度员分析用户请求
        dispatch_result = await dispatcher_agent.run(user_message)

        # 2. 根据分析决定下一步
        if dispatch_result.output.needs_more_info:
            # 请求更多信息（异步等待）
            clarification = await workflow.execute_query(
                name="request_clarification",
                query_type="preference_clarification",
            )
            user_response = await asyncio.wrap_in_activity(
                send_question, clarification
            )
            # 重新调度
            dispatch_result = await dispatcher_agent.run(
                f"{user_message}\n\nAdditional info: {user_response}"
            )

        # 3. 研究员收集信息
        if dispatch_result.output.intent == "dinner_recommendation":
            research = await researcher_agent.run(
                dispatch_result.output.search_query
            )

        # 4. 返回推荐
        return DinnerRecommendations(
            recommendations=research.output.suggestions
        )
```

---

## 四、Plector 集成方案

### 4.1 当前状态

Plector 的 `agent_loop.py` 当前：
- 内存中的循环执行
- 无持久化支持
- 中断后无法恢复

### 4.2 渐进式集成方案

**Phase 1：Activity 提取**
```python
# 将 LLM 调用提取为 Activity
@activity.defn
async def call_llm(messages: list[dict], tools: list[dict]) -> LLMResponse:
    """LLM 调用 - 非确定性活动"""
    return await llm_client.chat(messages, tools)


@activity.defn
async def execute_tool(tool_call: dict) -> ToolResult:
    """工具执行 - 非确定性活动"""
    return await tool_registry.execute(tool_call)


# Workflow 编排
@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, user_message: str) -> AgentResponse:
        messages = [{"role": "user", "content": user_message}]

        for _ in range(max_iterations):
            # LLM 决策
            decision = await workflow.execute_activity(
                call_llm,
                messages,
                start_to_close_timeout=timedelta(seconds=60),
            )

            if decision.is_complete:
                return AgentResponse(final=decision.message)

            # 工具执行
            for tool_call in decision.tool_calls:
                result = await workflow.execute_activity(
                    execute_tool,
                    tool_call,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                messages.append({"role": "tool", "content": result})

        raise MaxIterationsExceededError()
```

**Phase 2：状态持久化**
```python
@workflow.defn
class PersistentAgentWorkflow:
    @workflow.run
    async def run(self, session_id: str, user_message: str) -> AgentResponse:
        # 从持久化存储恢复上下文
        context = await load_session_context(session_id)

        # 继续执行
        messages = context.get("messages", [])
        messages.append({"role": "user", "content": user_message})

        # ... 执行逻辑 ...

        # 保存上下文
        await save_session_context(session_id, {"messages": messages})

        return final_response
```

**Phase 3：人类介入**
```python
@workflow.defn
class HumanInLoopWorkflow:
    @workflow.run
    async def run(self, task: str) -> Result:
        # 执行前置步骤
        analysis = await agent.run(task)

        # 请求人工审批
        approval = await workflow.execute_query(
            name="human_approval",
            payload={"analysis": analysis, "task": task},
        )

        # 等待信号
        await workflow.wait_until("approval_received")

        if not approval.approved:
            return Result(status="rejected", reason=approval.feedback)

        # 继续执行
        return await agent.complete(task)
```

---

## 五、与 Plector 现有组件的集成

### 5.1 Skill Handler 改造

```python
# 方案1：Activity 包装
@activity.defn
async def skill_activity(skill_name: str, method: str, params: dict):
    """技能执行作为 Activity"""
    return await skill_handler.execute(skill_name, method, params)


# 方案2：Workflow 内直接调用
@workflow.defn
class SkillWorkflow:
    @workflow.run
    async def run(self, task: SkillTask):
        # Skill 执行在 Workflow 中
        result = await execute_skill_activity(
            task.skill_name,
            task.method,
            task.params,
        )
        return result
```

### 5.2 MCP 集成

```python
@activity.defn
async def mcp_call(server: str, tool: str, args: dict):
    """MCP 工具调用作为 Activity"""
    result = await mcp_client.call_tool(server, tool, args)
    return result
```

---

## 六、部署选项

### 6.1 自托管

```yaml
# docker-compose.yml
services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=postgres
      - POSTGRES_PWD=postgres
      - POSTGRES_SEEDS=postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```

### 6.2 Temporal Cloud (SaaS)

```python
from temporalio import client

# 连接 Temporal Cloud
client = await client.connect(
    target_host="your-namespace.tmprl.cloud:7233",
    tls=True,
    namespace="your-namespace",
)
```

---

## 七、决策矩阵

| 需求 | 推荐方案 |
|------|---------|
| 快速原型 | 直接用 Plector 当前实现 |
| 中等复杂度 | 添加重试和检查点 |
| 生产环境长任务 | Temporal 集成 |
| 强一致性 | Temporal + 持久化存储 |
| 简单任务 | asyncio + 手动检查点 |

---

## 八、参考资源

- [Temporal 官网](https://temporal.io/)
- [Temporal Python SDK](https://python.temporal.io/)
- [Durable AI Agent 教程](https://learn.temporal.io/tutorials/ai/durable-ai-agent/)
- [Pydantic AI + Temporal 集成](https://temporal.io/blog/build-durable-ai-agents-pydantic-ai-and-temporal)
- [Temporal GitHub](https://github.com/temporalio)

#Temporal #工作流 #持久化 #AI-Agent
