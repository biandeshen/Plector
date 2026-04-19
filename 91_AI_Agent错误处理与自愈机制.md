# AI Agent 错误处理与自愈机制

> 来源：联网调研
> 更新：2026-04-19

---

## 一、错误处理的核心挑战

### 1.1 AI Agent 错误的特殊性

| 类型 | 传统软件 | AI Agent |
|------|---------|---------|
| **确定性** | 确定性结果 | 非确定性输出 |
| **错误来源** | 代码逻辑 | LLM 语义理解 |
| **表现形式** | 异常/崩溃 | 幻觉/格式错误 |
| **可预测性** | 高 | 低 |

### 1.2 三大错误类型

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent 错误分类                      │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  1. 结构错误 (Structural Errors)                   ││
│  │  • JSON 格式破损                                   ││
│  │  • 参数类型不匹配                                   ││
│  │  • 必需参数缺失                                     ││
│  │  → 解决方案：Pydantic 严格验证                      ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  2. 运行时错误 (Runtime Errors)                   ││
│  │  • API 调用失败 (网络/认证)                         ││
│  │  • 限流 (429 Too Many Requests)                    ││
│  │  • 服务不可用 (503 Service Unavailable)            ││
│  │  → 解决方案：指数退避 + 重试                        ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  3. 逻辑错误 (Logical Errors / Hallucinations)     ││
│  │  • 语法正确但内容错误                               ││
│  │  • 引用不存在的资源                                 ││
│  │  • 自相矛盾的陈述                                   ││
│  │  → 解决方案：验证 + 反馈循环                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 二、最佳实践

### 2.1 核心原则

> **"Assume non-determinism: Design with the assumption that errors will always occur, incorporating retry and feedback loops."**

> **"Strict validation: Use Pydantic to eliminate structural errors at the input stage."**

> **"Specific feedback: Make error messages concrete and constructive instructions that the LLM can understand."**

> **"Ensure observability: Record all steps in logs to enable failure cause analysis."**

### 2.2 验证策略

```python
from pydantic import BaseModel, Field, field_validator

class ToolInput(BaseModel):
    """严格验证的工具输入"""
    query: str = Field(description="Search query string")
    max_results: int = Field(default=10, ge=1, le=100)

    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
```

### 2.3 自定义错误处理

```python
def custom_error_handler(inputs: dict, error: Exception) -> str:
    """
    根据错误类型提供具体、可操作的反馈
    """
    if isinstance(error, ValidationError):
        return (
            "Input format error. Please check:\n"
            "- Required fields are provided\n"
            "- Types match expected format\n"
            "Do not retry with same inputs."
        )

    elif isinstance(error, RateLimitError):
        return (
            f"Rate limit reached. Please wait {error.retry_after}s "
            "before retrying with same inputs."
        )

    elif "Service Unavailable" in str(error):
        return (
            "Service temporarily unavailable. "
            "Please retry with same inputs."
        )

    else:
        return (
            f"Unexpected error occurred: {type(error).__name__}. "
            "Do not retry further."
        )
```

---

## 三、重试机制

### 3.1 指数退避 + 抖动

```python
import random
import asyncio

async def exponential_backoff_with_jitter(
    func,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
):
    """
    指数退避重试策略，带随机抖动避免惊群效应
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise

            # 计算延迟：指数增长 + 随机抖动
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)  # 0-10% 抖动
            total_delay = delay + jitter

            print(f"Attempt {attempt + 1} failed: {e}. "
                  f"Retrying in {total_delay:.2f}s...")

            await asyncio.sleep(total_delay)


class RetryableError(Exception):
    """可重试的错误基类"""
    pass
```

### 3.2 重试策略矩阵

| 错误类型 | 重试策略 | 最大重试次数 | 退避策略 |
|---------|---------|------------|---------|
| 网络超时 | ✓ | 3-5 | 指数 |
| 429 限流 | ✓ | 3 | 线性到上限 |
| 401 认证 | ✗ | 0 | - |
| 500 服务错误 | ✓ | 2-3 | 指数 |
| 格式错误 | ✗ | 0 | - |
| 逻辑错误 | ✗ | 0 | - |

---

## 四、监控执行模式

### 4.1 工作流程

```
┌─────────────┐
│  用户请求   │
└──────┬──────┘
       ▼
┌─────────────┐     ┌─────────────────┐
│  Agent 规划  │────►│  工具执行请求    │
└──────┬──────┘     └────────┬────────┘
       │                      ▼
       │              ┌─────────────────┐
       │              │   输入验证       │
       │              └────────┬────────┘
       │                      │
       ▼                      ▼
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 反馈重新规划 │◄────│   验证通过       │────►│   工具执行      │
└─────────────┘     └─────────────────┘     └────────┬────────┘
       │                      ▲                      │
       │                      │                      ▼
       │              ┌─────────────────┐     ┌─────────────────┐
       └─────────────►│   结果验证      │◄────│   API 错误      │
                      └────────┬────────┘     └────────┬────────┘
                               │                      │
                               ▼                      ▼
                      ┌─────────────────┐     ┌─────────────────┐
                      │   成功响应      │     │   重试 + 退避    │
                      └─────────────────┘     └─────────────────┘
```

### 4.2 Plector 当前实现分析

```python
# core/agent_loop.py 中的错误处理
async def _execute_single_tool(self, tool_name: str, tool_id: str, arguments: dict):
    """执行单个工具，带错误处理"""

    # 当前实现：基础 try-catch
    try:
        result = await self.tool_registry.execute(tool_name, arguments)
        return {
            "type": "toolDone",
            "tool": tool_name,
            "result": result.get("text", str(result)),
            "thinking": clean_thinking,
        }

    except ValidationError as e:
        # 结构错误 - 不重试
        return {
            "type": "toolError",
            "tool": tool_name,
            "error": f"参数验证失败: {e}",
            "retryable": False,
        }

    except RateLimitError as e:
        # 限流错误 - 可重试
        return {
            "type": "toolError",
            "tool": tool_name,
            "error": f"请求频率超限",
            "retryable": True,
            "retry_after": e.retry_after,
        }

    except Exception as e:
        # 其他错误
        return {
            "type": "toolError",
            "tool": tool_name,
            "error": str(e),
            "retryable": False,
        }
```

---

## 五、自愈机制设计

### 5.1 自愈流程

```
┌─────────────────────────────────────────────────────────┐
│                   AI Agent 自愈流程                     │
│                                                         │
│  1. 错误检测                                            │
│     ├── 结构验证失败                                    │
│     ├── API 调用失败                                    │
│     └── 逻辑验证失败                                    │
│                                                         │
│  2. 错误分类                                            │
│     ├── 可重试错误 → 进入重试循环                       │
│     ├── 不可重试错误 → 生成反馈                        │
│     └── 严重错误 → 人工介入                             │
│                                                         │
│  3. 反馈生成 (Self-Correction)                         │
│     ├── 错误类型描述                                    │
│     ├── 建议的修复方向                                  │
│     └── 不要重复的动作                                  │
│                                                         │
│  4. 代理重新规划                                        │
│     └── 基于反馈调整下一步行动                          │
│                                                         │
│  5. 验证循环                                            │
│     └── 重复直到成功或达到最大迭代                      │
└─────────────────────────────────────────────────────────┘
```

### 5.2 反馈驱动的自愈

```python
class SelfHealingAgent:
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    async def execute_with_healing(
        self,
        user_request: str,
        tools: list[BaseTool],
    ) -> AgentResult:
        """
        带自愈能力的执行循环
        """

        context = {"messages": [], "errors": []}

        for iteration in range(self.max_iterations):
            try:
                # 1. Agent 规划下一步
                plan = await self.agent.plan(
                    request=user_request,
                    context=context,
                    tools=tools,
                )

                # 2. 执行计划
                result = await self.execute_plan(plan)

                # 3. 验证结果
                if self.validate_result(result):
                    return AgentResult(success=True, data=result)

                # 4. 验证失败 - 生成反馈
                feedback = self.generate_feedback(result)
                context["errors"].append(feedback)
                context["messages"].append(
                    {"role": "system", "content": feedback}
                )

            except Exception as e:
                # 错误处理
                error_feedback = self.classify_and_feedback(e)
                context["errors"].append(error_feedback)

        # 达到最大迭代
        return AgentResult(
            success=False,
            error="Max iterations reached",
            context=context,
        )

    def validate_result(self, result) -> bool:
        """验证结果是否有效"""
        # 1. 格式检查
        # 2. 逻辑一致性检查
        # 3. 外部资源验证
        pass

    def generate_feedback(self, result) -> str:
        """生成具体、可操作的反馈"""
        return f"""
        Previous attempt produced invalid result.

        Issues identified:
        - {self.identify_issues(result)}

        Please adjust your approach:
        - Do not use the same reasoning path
        - Consider alternative tools or parameters
        - Verify assumptions before proceeding
        """
```

---

## 六、Plector 增强建议

### 6.1 短期增强

1. **添加结构验证**
```python
# skill_handler.py 中增强
from pydantic import BaseModel, ValidationError

async def execute(self, skill_name: str, method: str, params: dict) -> dict:
    # 获取工具 schema
    schema = self.registry.get_tool_schema(skill_name, method)

    # 严格验证输入
    try:
        validated_params = self.validate(schema, params)
    except ValidationError as e:
        return {
            "error": f"参数验证失败: {e}",
            "retryable": False,
        }
```

2. **实现重试装饰器**
```python
# utils/retry.py
from functools import wraps
import asyncio

def retry_on_failure(
    max_retries=3,
    base_delay=1.0,
    exponential_base=2,
    retryable_exceptions=(RetryableError,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (exponential_base ** attempt)
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

### 6.2 中期增强

1. **实现自愈循环**
2. **添加结果验证器注册表**
3. **集成结构化日志**

### 6.3 长期增强

1. **参考 Temporal 的持久化重试**
2. **引入 PALADIN 的自我纠正机制**
3. **支持人工介入节点**

---

## 七、参考资源

### 官方文档
- [LangChain Agent Error Handling](https://python.langchain.com/docs/concepts/error-handling/)
- [Temporal Durable Execution](https://temporal.io/)

### 技术文章
- [Building Retries in Agents](https://rittikajindal.medium.com/building-retries-in-agents)
- [AI Agent Error Handling Best Practices](https://agenticai-flow.com/en/posts/ai-agent-error-handling-best-practices/)
- [Self-Healing LangChain Agent](https://medium.com/@bhagyarana80)

### 学术论文
- [PALADIN: Self-Correcting LLM Agents](https://arxiv.org/pdf/2509.25238)

#AI-Agent #错误处理 #自愈机制 #重试策略
