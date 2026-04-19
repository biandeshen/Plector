# LangGraph 架构深度研究

> 来源：LangChain 官方文档 + Sparkco
> 研究日期：2026-04-19

---

## 一、LangGraph 定位

LangGraph 是一个**低级编排框架和运行时**，用于构建、管理和部署长时间运行的有状态代理。其设计灵感来源于 Pregel 和 Apache Beam。

### 1.1 核心特性

| 特性 | 说明 |
|------|------|
| **持久化执行** | 支持长时间运行任务的容错恢复 |
| **流式处理** | 支持实时流式输出 |
| **人机交互** | 支持人类介入和审批节点 |
| **状态管理** | 结构化状态模式 + 归约函数 |
| **检查点** | 自动保存和恢复执行状态 |
| **调试** | 与 LangSmith 深度集成 |

---

## 二、核心架构概念

### 2.1 StateGraph

StateGraph 是 LangGraph 的核心数据结构：

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 定义状态架构
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    documents: list[str]
    counter: Annotated[int, add]
    metadata: dict

# 创建图
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("agent", agent_node)
graph.add_node("tools", tools_node)

# 添加边
graph.add_edge(START, "agent")
graph.add_edge("agent", "tools")
graph.add_edge("tools", "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END}
)

# 编译
app = graph.compile()
```

### 2.2 节点 (Nodes)

节点是图中的处理单元：

```python
# 函数式节点
def agent_node(state: AgentState) -> AgentState:
    """Agent 处理节点"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# 类式节点
class ToolsNode:
    def __call__(self, state: AgentState) -> AgentState:
        # 处理逻辑
        return state
```

### 2.3 边 (Edges)

边定义节点间的连接：

```python
# 简单边
graph.add_edge("node_a", "node_b")

# 条件边
graph.add_conditional_edges(
    "agent",
    routing_function,
    {
        "continue": "tools",
        "end": END,
        "wait": "human"
    }
)
```

### 2.4 归约函数 (Reducers)

归约函数控制状态更新方式：

```python
from typing import Annotated
from operator import add

# 列表追加归约
def add_messages(left: list, right: list) -> list:
    """追加消息列表"""
    return left + right

# 计数器归约
def add_integers(left: int, right: int) -> int:
    """累加整数"""
    return left + right

# 在状态中使用
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 追加
    counter: Annotated[int, add]             # 累加
    data: list                              # 替换（非 Annotated）
```

---

## 三、状态管理模式

### 3.1 状态架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    AgentState 架构                       │
│                                                         │
│  messages: Annotated[list, add_messages]               │
│  ├── 归约：追加而非替换                                 │
│  └── 保持消息历史完整                                   │
│                                                         │
│  documents: list[str]                                   │
│  ├── 归约：默认替换模式                                 │
│  └── 最新文档覆盖旧文档                                 │
│                                                         │
│  counter: Annotated[int, add]                          │
│  ├── 归约：数值累加                                     │
│  └── 用于跟踪执行次数                                   │
│                                                         │
│  metadata: dict                                        │
│  ├── 自定义元数据                                       │
│  └── 支持任意结构                                       │
└─────────────────────────────────────────────────────────┘
```

### 3.2 状态继承模式

```python
from typing import TypedDict

# 基础状态
class BaseState(TypedDict):
    messages: Annotated[list, add_messages]

# 扩展状态
class AgentState(BaseState):
    documents: list[str]
    user_info: dict

# 在图之间继承
child_graph = StateGraph(AgentState)
child_graph.update_state(parent_graph.get_initial_state())
```

### 3.3 检查点与持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 内存检查点
checkpointer = MemorySaver()

# SQLite 检查点
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 编译时启用检查点
app = graph.compile(checkpointer=checkpointer)

# 运行并指定线程 ID
config = {"configurable": {"thread_id": "session_123"}}
result = app.invoke(initial_state, config)

# 从检查点恢复
result = app.get_state(config)
```

---

## 四、条件路由

### 4.1 路由函数

```python
def should_continue(state: AgentState) -> str:
    """决定下一步"""

    last_message = state["messages"][-1]

    # 检查是否有工具调用
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"

    # 检查是否需要人工介入
    if state.get("requires_approval"):
        return "wait"

    return "end"

# 在图中使用
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "wait": "human_approval",
        "end": END
    }
)
```

### 4.2 复杂路由模式

```python
def complex_router(state: AgentState) -> str:
    """多层条件路由"""

    # 第一层：检查错误
    if state.get("error"):
        return "error_handler"

    # 第二层：检查工具调用
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls"):
        return "tools"

    # 第三层：检查完成条件
    if state.get("task_complete"):
        return END

    # 第四层：检查人工介入
    if state.get("awaiting_input"):
        return "human_input"

    return "continue"
```

---

## 五、人机交互

### 5.1 人类介入节点

```python
from langgraph.types import Command

def human_approval_node(state: AgentState) -> AgentState:
    """等待人类审批"""

    # 发送待审批内容
    pending_content = state["pending_approval"]

    # 等待人类输入
    # （在实际应用中，这里会暂停执行）
    human_decision = Command(
        resume={
            "approved": True,
            "feedback": "Looks good, proceed."
        }
    )

    return {"approval": human_decision}


def interrupt_node(state: AgentState) -> Command:
    """中断执行等待用户输入"""

    return Command(
        goto="human_input",
        update={"awaiting_input": True}
    )
```

### 5.2 流式处理

```python
# 流式输出节点
async def streaming_agent(state: AgentState):
    """流式生成响应"""

    async for chunk in llm.astream(state["messages"]):
        yield chunk

# 使用
app = graph.compile()

async for event in app.astream(initial_state):
    print(event)
```

---

## 六、Plector 集成方案

### 6.1 状态模式映射

```python
# Plector 当前状态
class PlectorState(TypedDict):
    session_id: str
    messages: list[dict]
    current_tool: str | None
    tool_results: list[dict]
    context: dict

# 增强为 LangGraph 风格
class PlectorState(TypedDict):
    session_id: str
    messages: Annotated[list, add_messages]
    current_tool: str | None
    tool_results: Annotated[list, add_tool_results]
    context: dict
    metadata: dict

def add_tool_results(left: list, right: list) -> list:
    """工具结果追加"""
    return left + right
```

### 6.2 DAG 转换

```python
# Plector agency_orchestrator YAML
# steps:
#   - name: security_check
#     role: security-engineer
#   - name: code_review
#     role: code-reviewer
#     depends: [security_check]

# 转换为 LangGraph
graph = StateGraph(PlectorState)

# 节点
graph.add_node("security_check", security_check_node)
graph.add_node("code_review", code_review_node)

# 条件依赖
graph.add_edge(START, "security_check")
graph.add_edge("security_check", "code_review")
graph.add_edge("code_review", END)

# 并行执行支持
from langgraph.graph import Graph

parallel_graph = Graph()

# 并行节点
parallel_graph.add_node("task_1", task_1_node)
parallel_graph.add_node("task_2", task_2_node)
parallel_graph.add_node("task_3", task_3_node)

# 并行边
parallel_graph.add_edge(START, "task_1")
parallel_graph.add_edge(START, "task_2")
parallel_graph.add_edge(START, "task_3")
parallel_graph.add_edge("task_1", END)
parallel_graph.add_edge("task_2", END)
parallel_graph.add_edge("task_3", END)

# 编译并行图
parallel_app = parallel_graph.compile()
```

### 6.3 检查点持久化

```python
# Plector 检查点方案
from langgraph.checkpoint.sqlite import SqliteSaver

class PlectorCheckpoint:
    """Plector 执行检查点"""

    def __init__(self, db_path: str):
        self.checkpointer = SqliteSaver.from_conn_string(db_path)

    async def save(self, session_id: str, state: PlectorState):
        """保存检查点"""
        config = {"configurable": {"thread_id": session_id}}
        # LangGraph 自动处理

    async def restore(self, session_id: str) -> PlectorState | None:
        """恢复检查点"""
        config = {"configurable": {"thread_id": session_id}}
        return self.checkpointer.get(config)

    async def list_sessions(self) -> list[str]:
        """列出所有会话"""
        # 实现列出逻辑
        pass
```

---

## 七、与 DeerFlow 对比

### 7.1 架构相似点

| 特性 | LangGraph | DeerFlow |
|------|-----------|----------|
| 状态管理 | TypedDict + Reducer | 自定义 State 类 |
| 图结构 | StateGraph | LangGraph (复用) |
| 节点 | 函数/类 | Python 函数 |
| 边 | add_edge / add_conditional_edges | LangGraph API |
| 检查点 | CheckpointSaver | JSON 文件 |

### 7.2 关键差异

| 方面 | LangGraph | DeerFlow |
|------|-----------|----------|
| 定位 | 底层框架 | 上层应用 |
| 中间件 | 无原生支持 | 9 中间件链 |
| 子代理 | 无原生支持 | task() 工具 |
| 部署 | 多种检查点 | Docker/K8s |

---

## 八、参考资源

- [LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [Building LangGraph 博客](https://www.langchain.com/blog/building-langgraph)
- [State Management 指南](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025)

#LangGraph #状态管理 #LangChain #工作流
