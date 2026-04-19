---
name: self_improver
description: Plector 自我进化技能，通过多角色协作方式完成系统升级和优化。当用户说"自我改进"、"系统升级"、"自动优化"时使用。
---

# self_improver - Plector 自我改进技能

## 简介

self_improver 是 Plector 的核心自我进化技能，通过多角色协作方式完成系统升级和优化。当用户说"自我改进"、"系统升级"、"自动优化"时使用。

## 核心能力

### 1. start_upgrade - 启动升级流程

**功能**：启动 Plector 自我改进流程 v3.0

**参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| plan_file | string | docs/reports/upgrade_plan_v2.0_integrated.md | 升级方案文档路径 |
| phase | string | phase_1 | 起始阶段 (phase_1 ~ phase_5) |
| max_iterations | int | 100 | 最大迭代轮次 |

**返回格式**：
```json
{
  "success": true,
  "data": {
    "iterations": 5,
    "completed": 10,
    "failed": 1,
    "phases": [...],
    "workflow_engaged": true
  }
}
```

**执行流程**：
1. Planner 读取升级方案，拆解任务
2. 调用 `compose_workflow` 协编多角色分析
3. Coder 执行具体代码改造（由 agency_orchestrator 并行执行）
4. Tester 验证测试通过
5. Reviewer 审查，通过后进入下一 Phase

### 2. get_status - 查询升级进度

**返回**：
```json
{
  "success": true,
  "data": {
    "running": true,
    "current_phase": "phase_2"
  }
}
```

### 3. stop_upgrade - 停止升级流程

**返回**：`{"success": true, "data": {"stopped": true}}`

## 多角色协作机制

self_improver 集成了 agency_orchestrator 的 `compose_workflow` 功能：

```
任务进来
    ↓
[compose_workflow] 协编多角色分析
    ↓
┌─────────────────────────────────────┐
│  角色1: 系统分析师 (system-architect)  │  ← 从架构角度分析
│  角色2: 技术写手 (technical-writer)   │  ← 从文档角度优化
│  角色3: 代码开发者 (code-developer)   │  ← 执行具体代码修改
│  brainstorming superpower 参与        │  ← 生成 2-3 个候选方案供选择
└─────────────────────────────────────┘
    ↓
运行生成的工作流
```

## 事件驱动

| 事件 | 触发时机 | 数据 |
|------|---------|------|
| upgrade.started | 升级开始 | plan_file, start_phase |
| task.assigned | 任务分配 | task_id, assigned_to |
| agency.compose_started | 协编开始 | task_id, description |
| agency.compose_completed | 协编完成 | task_id, workflow_path |
| phase.completed | 阶段完成 | phase, completed_tasks |
| upgrade.completed | 升级完成 | total_iterations, results |

## 使用示例

### 示例1：启动完整升级
```python
result = await skill.execute("start_upgrade", {
    "plan_file": "docs/reports/upgrade_plan_v2.0.md",
    "phase": "phase_1",
    "max_iterations": 50
})
```

### 示例2：从指定阶段继续
```python
result = await skill.execute("start_upgrade", {
    "phase": "phase_3"
})
```

### 示例3：检查状态
```python
status = await skill.execute("get_status", {})
```

## Phase 阶段定义

| Phase | 主题 | 典型任务 |
|-------|------|---------|
| phase_1 | GSD 上下文保鲜 | 实现 context_refresher skill |
| phase_2 | LangGraph 集成 | 引入 workflow_graph.py |
| phase_3 | 技能主动联动 | 改造 skill_chain |
| phase_4 | 闭环自愈完善 | 优化 closure_engine |
| phase_final | 收尾 | 文档更新、测试覆盖 |

## 依赖关系

- 依赖 `agency_orchestrator` 技能
- 需要 MCP client 支持（可选，无时 fallback 到简化执行）

## 注意事项

1. **不要**在没有升级方案时直接调用
2. 升级过程会发布大量事件，确保 event_bus 正常运行
3. 如果 compose_workflow 失败，会 fallback 到简单执行模式
4. 每次 Phase 切换都会触发 review
