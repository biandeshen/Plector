# Plector 项目技能文档

> 版本：v1.0.0 | 更新：2026-04-21
> 本文档描述 Plector 项目开发的技能，不是 Claude Code 的 Skill。

---

## 一、文档定位

```
CLAUDE.md              ← 项目规范入口（仅 Plector 项目约束）
CLAUDE_CODE_TOOLS.md   ← Claude Code 工作流规范（通用）
CLAUDE_PLECTOR_TOOLS.md ← Plector 项目技能（本文档）
```

---

## 二、Plector 技能概述

| 技能 | 目录位置 | 说明 |
|------|----------|------|
| `memory` | `skills/memory/` | 记忆系统（艾宾浩斯遗忘曲线） |
| `context_refresher` | `skills/context_refresher/` | 上下文保鲜，防止目标遗忘 |
| `error_knowledge` | `skills/error_knowledge/` | 错误知识库，事件驱动 |
| `self_improver` | `skills/self_improver/` | 自我改进系统，连续失败时自动修复 |
| `agency_orchestrator` | `skills/agency_orchestrator/` | 工作流引擎，174 角色 DAG |
| `test_runner` | `skills/test_runner/` | 测试执行 |

---

## 三、核心技能详解

### 3.1 memory - 记忆系统

**功能**：基于艾宾浩斯遗忘曲线实现的记忆系统

**典型用法**：
```python
# 保存经验
memory.save(topic="代码审查", content="发现 agent_loop.py 的 recommended_actions 未执行")

# 检索
memory.recall(topic="代码审查")  # 检索相关记忆
```

**目录结构**：
```
skills/memory/
├── implementation.py    # 主实现
├── storage.py           # 存储层
└── retrieval.py         # 检索算法
```

### 3.2 context_refresher - 上下文保鲜

**功能**：GSD（Getting Things Done）风格的长对话目标保鲜

**典型用法**：
```python
context_refresher.check()  # 检查是否需要刷新上下文
context_refresher.refresh(original_goal)  # 刷新到原始目标
```

**触发条件**：
- 对话超过 30 分钟无进展
- 上下文明显偏离原始目标
- 用户提出新的子问题

### 3.3 error_knowledge - 错误知识库

**功能**：事件驱动的错误记录与分类系统

**典型用法**：
```python
error_knowledge.record(error_type="import_error", context="...")
error_knowledge.classify("import_error")  # 分类错误
error_knowledge.suggest("import_error")  # 获取修复建议
```

### 3.4 self_improver - 自我改进

**功能**：连续失败时自动修复问题的系统

**触发条件**：
- 同一操作失败 2 次
- 假设被否定 2 次

**执行流程**：
1. 分析失败原因
2. 生成替代方案
3. 执行并验证
4. 记录到 error_knowledge

### 3.5 agency_orchestrator - 工作流引擎

**功能**：多角色 DAG 工作流编排

**典型用法**：
```python
orchestrator.create_workflow([role1, role2, role3])  # 创建工作流
orchestrator.execute(workflow_id)  # 执行工作流
```

**角色支持**：
- code-reviewer
- plan-agent
- explore-agent
- design-agent
- 等等

### 3.6 test_runner - 测试执行

**功能**：执行测试套件并报告结果

**典型用法**：
```bash
python scripts/validate_skills.py  # 验证所有技能
pytest tests/ -v                    # 运行单元测试
```

---

## 四、项目命令

| 命令 | 说明 |
|------|------|
| `python channels/cli.py --query "你好"` | CLI 测试 |
| `python channels/websocket.py --port 8080` | Web 服务 |
| `python scripts/validate_skills.py` | 技能校验 |
| `ruff check core/ skills/ channels/` | 代码格式检查 |

---

## 五、快速索引

| 内容 | 位置 |
|------|------|
| Plector 项目规范 | `CLAUDE.md` |
| Claude Code 工作流 | `CLAUDE_CODE_TOOLS.md` |
| 技能完整文档 | `docs/PLECTOR_SKILLS.md` |

---

*版本：v1.0.0 | 更新：2026-04-21*
