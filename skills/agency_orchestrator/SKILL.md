---
name: agency_orchestrator
description: 多智能体 YAML 工作流引擎，174 个 AI 角色、32 个工作流模板、DAG 并行执行、变量传递、断点续跑。
---

# agency_orchestrator — 多智能体 YAML 工作流引擎（L1）

## 功能

Agency Orchestrator 的 Plector 技能封装。174 个 AI 角色、32 个工作流模板、DAG 并行执行、变量传递、断点续跑。

## 工具

### run_workflow
执行 YAML 工作流。DAG 自动并行，变量 `{{output}}` 传递，支持断点续跑。

参数：`path`(必需) / `inputs` / `provider`(默认 claude-code) / `model` / `resume` / `from_step`

### validate_workflow
校验工作流语法和结构，不执行。

参数：`path`(必需)

### list_workflows
列出 32 个内置工作流模板。

### plan_workflow
显示 DAG 执行计划（并行/串行）。

参数：`path`(必需)

### compose_workflow
用自然语言生成 YAML 工作流。AI 自动选角色、设计 DAG。

参数：`description`(必需) / `provider`(默认 claude-code) / `model`

### list_roles
列出 174 个 AI 角色（18 个分类）。

参数：`category`(可选过滤)

### get_role
获取角色完整定义。

参数：`category`(必需) / `name`(必需)

## 实现方式

- **本地只读**：list_roles / get_role / list_workflows → 直接读文件，快
- **MCP 代理**：run / validate / plan / compose → 走 MCP Server，服务端有完整逻辑

## 配置要求

- agency-orchestrator MCP Server 已配置（config.yaml）
- Claude Code CLI（claude-code provider 免 API key）
