# AI Agent 评估与可观测性研究

> 来源：Galileo / Arize AI / LangSmith 官方
> 研究日期：2026-04-19

---

## 一、评估平台对比概览

### 1.1 平台总览

| 平台 | 核心定位 | 评估方式 | 开源 | 主要用户 |
|------|---------|---------|------|---------|
| **Galileo** | Agent 原生评估 | Luna-2 SLM | 部分 | 企业 |
| **LangSmith** | LangChain 生态 | 多种评估器 | ✗ | LangChain 用户 |
| **Arize AI** | 通用可观测性 | OTEL 原生 | 部分 | 企业 |
| **Braintrust** | Eval 优先 | 自定义评分器 | ✗ | 工程团队 |
| **Langfuse** | 开源可观测性 | LLM-as-judge | ✓ | 自托管 |
| **Patronus AI** | 幻觉检测 | 专有模型 | ✗ | 企业 |
| **TruLens** | RAG 评估 | 反馈函数 | ✓ | RAG 应用 |
| **Humanloop** | 协作评估 | UI 优先 | ✗ | 产品团队 |

### 1.2 核心功能对比

| 功能 | Galileo | LangSmith | Arize | Langfuse | Braintrust |
|------|---------|-----------|--------|-----------|------------|
| Tracing | ✓ | ✓ | ✓ | ✓ | ✓ |
| LLM-as-judge | ✓ | ✓ | ✓ | ✓ | ✓ |
| RAG 评估 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Agent 指标 | ✓ (9个) | 基础 | ✗ | ✗ | ✗ |
| 离线评估 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 运行时保护 | ✓ | ✗ | ✗ | ✗ | ✗ |
| 自动护栏 | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 二、评估指标体系

### 2.1 Agent 专用指标 (Galileo)

| 指标 | 说明 | 测量方式 |
|------|------|---------|
| **Goal Completion Rate** | 任务完成率 | 最终状态评估 |
| **Step Efficiency** | 步骤效率 | 实际 vs 预期步骤 |
| **Tool Call Accuracy** | 工具调用准确率 | 工具选择正确性 |
| **Error Recovery Rate** | 错误恢复率 | 失败后恢复能力 |
| **Context Utilization** | 上下文利用率 | 上下文使用效率 |
| **Response Coherence** | 响应连贯性 | 跨轮次一致性 |
| **Hallucination Rate** | 幻觉率 | 事实性错误检测 |
| **Latency** | 延迟 | 执行时间 |
| **Cost Efficiency** | 成本效率 | 成本 vs 质量 |

### 2.2 RAG 评估指标

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| **Context Precision** | 上下文精确度 | 相关块排名 |
| **Answer Relevance** | 答案相关性 | 答案 vs 问题 |
| **Faithfulness** | 忠诚度 | 答案 vs 上下文 |
| **Hallucination** | 幻觉 | 上下文外内容 |
| **Context Recall** | 上下文召回 | 答案 vs 真实答案 |

### 2.3 评估器类型

```python
# LangSmith 4 种评估器

# 1. LLM-as-Judge
from langsmith.evaluation import evaluate

def correctiveness_evaluator(run, example):
    """LLM 判断正确性"""
    return {
        "score": llm.judge(
            f"Rate correctness: {run.outputs['answer']}",
            reference=example.outputs["answer"]
        )
    }

# 2. Regex Match
from langsmith.evaluation import StringEvaluator

evaluator = StringEvaluator(
    key="exact_match",
    scoring_method=lambda pred, ref: pred.strip() == ref.strip()
)

# 3. Semantic Similarity
evaluator = StringEvaluator(
    key="semantic_similarity",
    scoring_method=sentence_similarity
)

# 4. Custom Function
def custom_metric(run, example) -> dict:
    """自定义评估函数"""
    prediction = run.outputs["output"]
    expected = example.outputs["target"]
    return {
        "score": calculate_custom_score(prediction, expected),
        "reasoning": "评分理由"
    }
```

---

## 三、评估工作流

### 3.1 离线评估流程

```
┌─────────────────────────────────────────────────────────┐
│                  离线评估工作流                           │
│                                                         │
│  1. 数据准备                                            │
│     ├── 收集测试数据集                                   │
│     ├── 定义期望输出                                    │
│     └── 标注关键信息                                    │
│                                                         │
│  2. 评估执行                                            │
│     ├── 选择评估器                                     │
│     ├── 运行评估                                        │
│     └── 收集结果                                        │
│                                                         │
│  3. 分析与改进                                          │
│     ├── 识别失败模式                                    │
│     ├── 生成改进建议                                    │
│     └── 验证修复效果                                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 在线评估流程

```
┌─────────────────────────────────────────────────────────┐
│                  在线评估工作流                           │
│                                                         │
│  1. 生产监控                                            │
│     ├── 实时追踪执行                                    │
│     ├── 采样关键请求                                    │
│     └── 收集用户反馈                                    │
│                                                         │
│  2. 自动评估                                            │
│     ├── LLM-as-judge                                   │
│     ├── 规则检查                                        │
│     └── 异常检测                                        │
│                                                         │
│  3. 反馈循环                                            │
│     ├── 数据集更新                                      │
│     ├── Prompt 优化                                    │
│     └── 模型微调                                        │
└─────────────────────────────────────────────────────────┘
```

### 3.3 护栏转换流程

```
┌─────────────────────────────────────────────────────────┐
│              评估 → 护栏转换 (Galileo)                  │
│                                                         │
│  离线评估 ──► 识别问题 ──► 生成规则 ──► 运行时保护      │
│     │             │               │                    │
│     ▼             ▼               ▼                    │
│  数据集      失败模式        检查逻辑                    │
│                                                         │
│  效果：评估中发现的问题自动转化为生产护栏                │
└─────────────────────────────────────────────────────────┘
```

---

## 四、OpenTelemetry 集成

### 4.1 追踪数据模型

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 设置追踪
provider = TracerProvider()
processor = BatchSpanExporter(endpoint="langfuse-host:4317")
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Agent 追踪
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("agent_execution")
async def execute_agent(prompt: str):
    with trace.get_current_span() as span:
        span.set_attribute("user.prompt", prompt)

        # LLM 调用
        llm_span = tracer.start_span("llm.call")
        response = await llm.invoke(prompt)
        llm_span.end()

        # 工具调用
        for tool_call in response.tool_calls:
            tool_span = tracer.start_span(f"tool.{tool_call.name}")
            result = await execute_tool(tool_call)
            tool_span.set_attribute("tool.name", tool_call.name)
            tool_span.end()

        return response
```

### 4.2 Langfuse 集成

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-xxx",
    secret_key="sk-xxx",
    host="https://cloud.langfuse.com"
)

# 自动追踪 LangChain
from langchain.callbacks import LangfuseCallbackHandler

handler = LangfuseCallbackHandler(
    user_id="user_123",
    session_id="session_abc",
    metadata={"tier": "premium"}
)

# 带追踪运行
chain.invoke(
    {"query": "your query"},
    config={"callbacks": [handler]}
)
```

---

## 五、Plector 评估方案

### 5.1 评估指标定义

```python
from dataclasses import dataclass
from enum import Enum

class MetricType(Enum):
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    USER_SATISFACTION = "user_satisfaction"

@dataclass
class Metric:
    name: str
    type: MetricType
    description: str
    calculation: str  # 计算公式或方法
    threshold: float   # 合格阈值

# Plector 核心指标
PLECTOR_METRICS = [
    Metric(
        name="task_completion_rate",
        type=MetricType.FUNCTIONAL,
        description="任务完成率",
        calculation="completed_tasks / total_tasks",
        threshold=0.85
    ),
    Metric(
        name="tool_call_accuracy",
        type=MetricType.FUNCTIONAL,
        description="工具调用准确率",
        calculation="correct_tool_calls / total_tool_calls",
        threshold=0.90
    ),
    Metric(
        name="response_latency_p95",
        type=MetricType.PERFORMANCE,
        description="P95 响应延迟（秒）",
        calculation="percentile(latencies, 95)",
        threshold=5.0
    ),
    Metric(
        name="context_efficiency",
        type=MetricType.PERFORMANCE,
        description="上下文利用率",
        calculation="effective_tokens / total_tokens",
        threshold=0.70
    ),
    Metric(
        name="safety_violation_rate",
        type=MetricType.SAFETY,
        description="安全违规率",
        calculation="violations / total_requests",
        threshold=0.01
    ),
]
```

### 5.2 评估执行框架

```python
from abc import ABC, abstractmethod
from typing import Any

class Evaluator(ABC):
    """评估器基类"""

    @abstractmethod
    async def evaluate(
        self,
        prediction: Any,
        reference: Any = None,
        metadata: dict = None
    ) -> EvaluationResult:
        """执行评估"""
        pass

class LLMJudgeEvaluator(Evaluator):
    """LLM-as-Judge 评估器"""

    def __init__(self, llm, judge_prompt: str):
        self.llm = llm
        self.judge_prompt = judge_prompt

    async def evaluate(
        self,
        prediction: Any,
        reference: Any = None,
        metadata: dict = None
    ) -> EvaluationResult:
        judgment = await self.llm.complete(
            self.judge_prompt.format(
                prediction=prediction,
                reference=reference
            )
        )
        return EvaluationResult(
            score=self.parse_score(judgment),
            reasoning=judgment
        )

class ToolAccuracyEvaluator(Evaluator):
    """工具调用准确率评估器"""

    async def evaluate(
        self,
        prediction: Any,
        reference: Any = None,
        metadata: dict = None
    ) -> EvaluationResult:
        if not reference:
            return EvaluationResult(score=None, reason="No reference")

        pred_tools = set(metadata.get("tool_calls", []))
        ref_tools = set(reference.get("expected_tools", []))

        correct = len(pred_tools & ref_tools)
        total = len(ref_tools)

        return EvaluationResult(
            score=correct / total if total > 0 else 0,
            reasoning=f"{correct}/{total} correct"
        )
```

### 5.3 评估报告生成

```python
from datetime import datetime

class EvaluationReport:
    """评估报告"""

    def __init__(self, name: str):
        self.name = name
        self.timestamp = datetime.now()
        self.results: list[EvaluationResult] = []
        self.metrics: dict[str, float] = {}

    def add_result(self, result: EvaluationResult):
        self.results.append(result)

    def calculate_metrics(self):
        """计算汇总指标"""
        for metric in PLECTOR_METRICS:
            scores = [r.score for r in self.results if r.score is not None]
            if scores:
                self.metrics[metric.name] = sum(scores) / len(scores)

    def check_thresholds(self) -> dict[str, bool]:
        """检查阈值"""
        checks = {}
        for metric in PLECTOR_METRICS:
            value = self.metrics.get(metric.name)
            if value is not None:
                checks[metric.name] = value >= metric.threshold
        return checks

    def generate_report(self) -> str:
        """生成报告"""
        self.calculate_metrics()
        checks = self.check_thresholds()

        return f"""
# Plector 评估报告

**评估时间**: {self.timestamp}
**评估名称**: {self.name}

## 指标汇总

| 指标 | 值 | 阈值 | 状态 |
|------|-----|------|------|
{chr(10).join([
    f"| {m.name} | {self.metrics.get(m.name, 'N/A'):.2%} | {m.threshold:.2%} | {'✓' if checks.get(m.name) else '✗'} |"
    for m in PLECTOR_METRICS
])}

## 结论

整体通过率: {sum(checks.values()) / len(checks):.2%}
"""
```

---

## 六、实施路线图

### Phase 1：基础追踪 (1-2周)

| 任务 | 说明 | 优先级 |
|------|------|--------|
| OpenTelemetry 集成 | Agent 执行追踪 | P0 |
| Langfuse 集成 | 可视化追踪界面 | P0 |
| 基础指标收集 | 延迟、吞吐量 | P1 |

### Phase 2：评估能力 (2-3周)

| 任务 | 说明 | 优先级 |
|------|------|--------|
| LLM-as-Judge | 自动质量评估 | P1 |
| 工具准确率评估 | 工具调用评估 | P1 |
| 测试数据集 | 构建评估数据集 | P1 |

### Phase 3：生产护栏 (3-4周)

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 实时监控 | 生产环境监控 | P2 |
| 异常检测 | 异常行为检测 | P2 |
| 自动护栏 | 评估→护栏转换 | P2 |

---

## 七、参考资源

- [Galileo AI Agent Evaluation](https://galileo.ai/blog/best-ai-agent-evaluation-platforms)
- [LangSmith 文档](https://docs.smith.langchain.com/)
- [Arize AI](https://arize.com/)
- [Langfuse](https://langfuse.com/)
- [OpenTelemetry](https://opentelemetry.io/)

#评估 #可观测性 #LangSmith #Galileo #Langfuse
