---
tags: [Plector, 规范, 设计]
type: spec
created: 2026-04-08
---

# Harness Engineering 完整实施指南

Harness Engineering 的核心思想是：**把 AI 当一匹烈马，你要做的不是天天训马，而是给它套上缰绳、设计好跑道、修好护栏、装好仪表盘，让它自己跑稳、跑久、不跑偏**[reference:0]。

以下是基于 OpenAI、LangChain、Anthropic 等一线实践的完整实施流程。

---

## 一、核心原则：记住这三句话

1. **模型能力决定上限，Harness 决定下限**——LangChain 在固定模型的情况下，仅通过优化 Harness 将排名从 Top 30 提升到 Top 5[reference:1]。
2. **每当 AI 犯错，就工程化一个方案，让它永远不再犯同样的错**——这不是改 prompt，而是构建测试、lint 规则或验证脚本[reference:2]。
3. **Harness Engineering = 信息层 + 约束层 + 自动化层 + 可观测性层**[reference:3]。

---

## 二、完整实施路线图（四阶段，约 2-3 周）

| 阶段 | 核心任务 | 产出 | 时长 |
|------|----------|------|------|
| **Phase 1：信息层** | 建立结构化知识库，解决“Agent 该看什么” | `AGENTS.md`（索引地图）+ `docs/` 目录 | 1-2 天 |
| **Phase 2：约束层** | 定义架构规则、CI 门禁，解决“Agent 不能做什么” | 分层架构定义 + 自定义 Linter + 测试覆盖率门禁 | 3-5 天 |
| **Phase 3：自动化层** | 构建反馈回路和自迭代机制，解决“Agent 如何自我修正” | Ralph 循环 + 闭环配置 + 错误自动修复 | 1-2 周 |
| **Phase 4：可观测性层** | 接入追踪和度量系统，解决“如何知道 Agent 在做什么” | Trace Analyzer + 结构化日志 + Dashboard | 2-3 天 |

---

## 三、Phase 1：信息层——让 Agent 知道去哪里看（1-2 天）

### 3.1 核心教训：不要把 AGENTS.md 写成百科全书

OpenAI 早期踩过这个坑：他们让 Codex 生成了一个成百上千页的巨型 `AGENTS.md`，结果 Agent 反而更笨了——巨量指令挤占了上下文窗口，注意力被稀释，无法区分优先级[reference:4]。

**正确做法**：把 `AGENTS.md` 从“百科全书”变成“索引地图”，控制在 **100 行左右**，只放目录和关键约束，真实内容放到 `docs/` 目录下[reference:5]。

### 3.2 标准 `AGENTS.md` 模板

```markdown
# AGENTS.md - 项目索引地图

## 快速导航
| 你想做什么 | 去哪里看 |
|-----------|----------|
| 了解系统架构 | docs/architecture/overview.md |
| 了解编码规范 | docs/conventions/README.md |
| 了解 API 设计 | docs/api/design.md |
| 查看当前任务 | docs/plans/current-sprint.md |

## 硬性规则（CI 会验证）
1. 依赖方向：types/ → config/ → repo/ → service/ → runtime/ → ui/
2. 新增代码必须有对应测试
3. 所有公共 API 必须有文档注释

## 项目快速概览
[项目名称] 是一个 [一句话定位]
```

### 3.3 结构化知识库

在 `docs/` 下按主题组织，每个文件控制在 **300-500 行**以内，避免单个文件过大。推荐结构：

```
docs/
├── architecture/       # 架构设计
├── conventions/        # 编码规范
├── api/               # API 文档
├── plans/             # 任务计划（供 Agent 读取）
└── guides/            # 操作指南
```

**渐进式披露**：Agent 从 `AGENTS.md` 这个“索引地图”开始，需要时才去对应目录读取详细信息[reference:6]。

---

## 四、Phase 2：约束层——让 Agent 知道不能做什么（3-5 天）

### 4.1 分层架构定义

```yaml
# config/architecture.yaml
layers:
  - name: types
    allowed_deps: []
  - name: config
    allowed_deps: [types]
  - name: repo
    allowed_deps: [types, config]
  - name: service
    allowed_deps: [types, config, repo]
  - name: runtime
    allowed_deps: [types, config, repo, service]
  - name: ui
    allowed_deps: [types, config, repo, service, runtime]
```

**实现检查**：写一个自定义 Linter，在 CI 中运行，违反依赖方向的代码直接拒绝合并。

### 4.2 结构化测试门禁

| 检查项 | 工具 | 通过标准 |
|--------|------|----------|
| 单元测试覆盖率 | pytest-cov | ≥ 80% |
| 导入循环检测 | pylint / 自定义脚本 | 0 组 |
| 代码格式 | black / ruff | 自动格式化 |
| 类型检查 | mypy | 无错误 |
| 依赖方向 | 自定义 Linter | 无违规 |

将这些检查集成到 CI 中（GitHub Actions / GitLab CI），合并 PR 前必须全部通过。

### 4.3 自定义 Linter 示例

```python
# scripts/lint_architecture.py
import ast
import sys
from pathlib import Path

LAYER_RULES = {
    "types": {"max": 0, "allowed": []},
    "config": {"max": 1, "allowed": ["types"]},
    "repo": {"max": 2, "allowed": ["types", "config"]},
    "service": {"max": 3, "allowed": ["types", "config", "repo"]},
}

def check_import(filepath, layer, allowed):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] not in allowed:
                    print(f"违规: {layer} 层导入了 {alias.name}")
                    return False
    return True
```

---

## 五、Phase 3：自动化层——让 Agent 自我修正（1-2 周）

### 5.1 Ralph 循环：不完成不许下班

Ralph 循环是 2025 年底兴起的一种 AI 编程方法论——用一个简单的循环让 AI **持续迭代直到任务真正完成**[reference:7]。

**核心机制**：当 AI 试图退出时，Hook 拦截并检查输出中是否包含预定义的“完成承诺”（如 `DONE` 或 `COMPLETE`），未检测到则继续循环[reference:8]。

**原始实现**（Bash 5 行代码）[reference:9]：

```bash
while :; do cat PROMPT.md | claude-code; done
```

**集成到 Plector**：在 `core/agent_loop.py` 中实现：

```python
class RalphLoop:
    def __init__(self, agent_loop, max_iterations=10):
        self.agent_loop = agent_loop
        self.max_iterations = max_iterations
        self.completion_keywords = ["DONE", "COMPLETE", "任务完成"]

    async def run(self, task: str, session_id: str = None):
        context = {"task": task, "history": []}
        for i in range(self.max_iterations):
            result = await self.agent_loop.run(
                f"任务: {task}\n历史: {context['history']}\n请继续，完成后输出 DONE",
                session_id
            )
            if any(kw in result for kw in self.completion_keywords):
                return result
            context["history"].append(f"第 {i+1} 轮输出: {result[:200]}...")
        return "达到最大迭代次数"
```

### 5.2 闭环配置（基于现有 `closed_loops.yaml`）

你已经有了 `closed_loops.yaml`，这正是 Harness 的“反馈回路”组件[reference:10]。扩展它：

```yaml
# config/closed_loops.yaml
test_failure_recovery:
  trigger_on: ["test.failed"]
  entry: "record_error"
  max_iterations: 3
  nodes:
    record_error:
      type: "skill"
      skill: "error_knowledge"
      method: "store_error"
      next: "analyze_error"
    analyze_error:
      type: "condition"
      skill: "error_knowledge"
      method: "classify_error"
      transitions:
        syntax_error: "fix_code"
        timeout: "retry_test"
        unknown: "alert_human"
    fix_code:
      type: "skill"
      skill: "code_writer"
      method: "fix_code"
      next: "re_test"
    re_test:
      type: "skill"
      skill: "test_runner"
      method: "run_test"
      transitions:
        passed: "end"
        failed: "record_error"
    end:
      type: "end"
```

### 5.3 双重智能体架构（用于长周期任务）

Anthropic 的方案：一个 **初始化代理**（首次运行搭建环境），一个 **编码代理**（后续增量改动，并为下次会话留下清晰痕迹）[reference:11]。

**集成到 Plector**：

```python
class DualAgent:
    async def run(self, project_root: str):
        # 1. 初始化代理：搭建环境、脚手架、初始代码
        init_result = await self.initializer.run(f"初始化项目 {project_root}")
        # 2. 编码代理：循环迭代，每次会话后留下 progress.md
        progress_file = Path(project_root) / "progress.md"
        while True:
            task = f"基于 progress.md 继续开发，完成后输出 CHECKPOINT"
            result = await self.coding_agent.run(task)
            if "CHECKPOINT" in result:
                break
            # 更新进度文件
            progress_file.write_text(result)
```

---

## 六、Phase 4：可观测性层——知道 Agent 在做什么（2-3 天）

### 6.1 Trace Analyzer Skill（LangChain 的核心武器）

LangChain 的做法：**将 trace 分析做成一个 Agent Skill**，让它自动分析失败模式，然后回写到 harness[reference:12]。

**流程**：
1. 从追踪系统拉取实验 traces
2. 并行启动多个错误分析 Agent
3. 主 Agent 汇总发现和建议
4. 将反馈应用到 harness 中

这个做法与 **boosting**（机器学习中的集成方法）类似——每次都聚焦于上一轮的错误，逐步改进[reference:13]。

### 6.2 结构化日志（你已有基础）

Plector 已经在 `logs/plector.jsonl` 中记录日志，需确保包含：

```json
{
  "timestamp": "2026-04-04T10:00:00Z",
  "session_id": "abc123",
  "event_type": "skill_call",
  "skill": "code_writer",
  "method": "write",
  "success": true,
  "duration_ms": 1234,
  "input_tokens": 500,
  "output_tokens": 200
}
```

### 6.3 可观测性仪表盘

基于这些日志，构建 Dashboard 展示：

- 技能调用成功率（目标 > 95%）
- 闭环执行成功率（目标 > 70%）
- Token 消耗趋势（用于成本优化）
- 错误分类分布（语法错误 vs 超时 vs 未知）

---

## 七、工具链推荐

| 类别 | 推荐工具 | 用途 |
|------|----------|------|
| **Agent 框架** | LangChain + Deep Agents CLI | 可观测性、trace 分析[reference:14] |
| **沙箱执行** | Daytona | 安全隔离的代码执行环境[reference:15] |
| **可观测性** | LangSmith / Harbor | trace 收集、指标度量[reference:16] |
| **CI/CD** | GitHub Actions / Harness | 自动化门禁 |
| **代码质量** | ruff, mypy, pytest-cov | 静态检查、测试覆盖率 |
| **知识库** | docs/ + AGENTS.md | 结构化项目知识[reference:17] |

---

## 八、常见陷阱与应对

| 陷阱 | 症状 | 应对 |
|------|------|------|
| **AGENTS.md 膨胀** | Agent 忽略关键指令 | 控制在 100 行以内，只做索引[reference:18] |
| **过度约束** | Agent 被规则卡死，无法完成任务 | 区分“必须检查”和“建议遵守”，给 Agent 留自主空间 |
| **反馈回路缺失** | 同样的错误反复出现 | 建立闭环配置，让错误自动触发修复 |
| **可观测性不足** | 不知道 Agent 为什么失败 | 接入 trace 分析，用 AI 分析失败模式[reference:19] |
| **一次做太多** | Agent 耗尽上下文，半途而废 | 使用 Ralph 循环 + 渐进式任务拆解[reference:20] |

---

## 九、与 Plector 的整合清单

你的系统已经有很多 Harness 的组件了。以下是完整整合清单：

- [x] **信息层**：`config/profiles/AGENTS.md` 可作为索引地图（需精简）
- [x] **信息层**：`docs/` 目录（需要结构化）
- [x] **约束层**：分层架构（`tier_0/1/2/3` + 依赖检查）
- [ ] **约束层**：CI 门禁 + 自定义 Linter（待实现）
- [x] **自动化层**：`closed_loops.yaml` 闭环配置
- [ ] **自动化层**：Ralph 循环（待集成到 `agent_loop.py`）
- [ ] **自动化层**：双重智能体架构（待实现）
- [x] **可观测性层**：`logs/plector.jsonl` 结构化日志
- [ ] **可观测性层**：Trace Analyzer（待实现）
- [ ] **可观测性层**：Dashboard（待实现）

---

## 十、一句话总结

**Harness Engineering 就是为 AI 套上缰绳、修好跑道、装好仪表盘，然后放手让它自己跑。** 你不需要天天训马，只需要建好这套基础设施。

按四阶段推进：**信息层（1-2 天）→ 约束层（3-5 天）→ 自动化层（1-2 周）→ 可观测性层（2-3 天）**。每完成一层，Agent 的稳定性就会上一个台阶。

你的 Plector 已经走在正确的路上——核心引擎、技能体系、闭环配置都已就绪。接下来的重点是 **Ralph 循环**（让 Agent 能持续迭代）和 **Trace Analyzer**（让系统能自动从错误中学习）。