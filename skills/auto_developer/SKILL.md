---
name: auto_developer
description: 一键自动开发流水线，从需求到代码的全自动开发流程，使用 agency-orchestrator 调度 174 个专家角色协作。
---

# auto_developer — 一键自动开发流水线（L2）

## 功能

从需求到代码的全自动开发流水线。使用 agency-orchestrator 调度 174 个专家角色协作，Claude Code 执行代码开发。

## 工具

### develop（一键开发）

输入需求描述，自动调度完整开发流水线：

```
产品经理 → 架构师(并行) + 安全工程师(并行) → 高级开发者 → 代码审查员 → 产品经理汇总
```

参数：`requirement`(必需) / `project_dir` / `provider`(默认 claude-code)

示例：
```
一键开发：给用户模块增加批量导出 CSV 功能，要求分页、权限校验、异步处理
```

### compose（生成工作流）

用自然语言描述需求，AI 自动生成 YAML 工作流文件。

参数：`description`(必需) / `provider`(默认 claude-code)

### run（运行工作流）

运行指定的工作流 YAML 文件。

参数：`workflow`(必需) / `inputs` / `provider`(默认 claude-code)

### plan（查看执行计划）

查看工作流的 DAG 执行计划（哪些步骤并行、哪些串行）。

参数：`workflow`(必需)

### list_roles / list_workflows

代理到 agency_orchestrator (L1) 的同名工具。

## 依赖

- `agency_orchestrator`（L1 技能）
- agency-orchestrator MCP Server 已配置
- Claude Code CLI（claude-code provider 免 API key）
