---
tags:
  - agency-orchestrator
  - workflow
  - multi-agent
  - guide
  - v1.5
type: guide
created: 2026-04-15
related-to:
  - [[69_v1.5_agency-orchestrator合并方案操作手册]]
  - [[68_v2.x_agency-orchestrator-ClaudeCode全栈集成]]
  - [[71_mcp_call拦截机制修复]]
---

# Agency Orchestrator 使用指南

> Plector 集成的多智能体 YAML 工作流引擎，202 个 AI 角色、32 个工作流模板、DAG 并行执行，用已有 AI 会员即可运行。

关联：[[69_v1.5_agency-orchestrator合并方案操作手册]] | [[68_v2.x_agency-orchestrator-ClaudeCode全栈集成]]

---

## 一、是什么

**Agency Orchestrator** 是一个多智能体协作引擎。你写一个 YAML 文件描述工作流，它自动调度 AI 角色按 DAG 依赖执行，支持并行、变量传递、断点续跑。

Plector 中集成为**两层技能**：

| 层级 | 技能名 | 定位 | 工具数 | 适用场景 |
|------|--------|------|--------|---------|
| L1 | `agency_orchestrator` | MCP Server 直接封装 | 7 | 精细控制，手动选工作流、选角色 |
| L2 | `auto_developer` | 一键开发封装 | 6 | "帮我开发xxx"，全自动流水线 |

**大多数时候用 L2 就够了**，L1 在需要自定义工作流时使用。

---

## 二、前置条件

### 2.1 环境要求

| 依赖 | 说明 | 检查方式 |
|------|------|---------|
| Node.js ≥ 18 | MCP Server 运行环境 | `node -v` |
| Claude Code CLI | 免 API key 的 LLM 执行器 | `claude --version` |
| Plector | 已在 `develop/agency-orchestrator` 分支 | `git branch` |

### 2.2 Claude Code 安装（免 API key）

```bash
# 安装 Claude Code CLI（需要 Claude Max/Pro 会员）
npm install -g @anthropic-ai/claude-code

# 验证
claude --version

# 首次使用需要登录
claude login
```

> **没有 Claude Max？** 也可以用其他免 API key 方案：
> - Google 账号 → `provider: "gemini-cli"`（免费，1000 次/天）
> - GitHub Copilot → `provider: "copilot-cli"`
> - 本地模型 → `provider: "ollama"`

### 2.3 验证 MCP Server

```bash
cd E:\产品\Plector

# 检查编译产物
Test-Path servers\agency-orchestrator\dist\cli.js   # 应返回 True

# 如果不存在，需要构建
cd servers\agency-orchestrator
npm install
npm run build
cd ..\..\..

# 检查角色目录
Test-Path external-skills\roles                      # 应返回 True
(Get-ChildItem external-skills\roles -Recurse -Filter *.md).Count  # 应返回 ~202

# 检查工作流目录
(Get-ChildItem servers\agency-orchestrator\workflows -Recurse -Filter *.yaml).Count  # 应返回 ~32
```

### 2.4 config.yaml 配置

确认 `config/config.yaml` 中 `agency-orchestrator` MCP Server 已启用：

```yaml
mcp:
  servers:
    agency-orchestrator:
      enabled: true
      transport: "stdio"
      command: "node"
      args: ["servers/agency-orchestrator/dist/cli.js", "serve"]
      env:
        AGENTS_DIR: "external-skills/roles"
```

> **`AGENTS_DIR: "external-skills/roles"`** — 指向项目内的角色目录，不依赖 node_modules。

---

## 三、快速开始

### 3.1 一键开发（L2 — 最简单）

直接对 Plector 说：

```
帮我开发一个用户批量导出 CSV 功能，要求分页、权限校验、异步处理
```

Plector 会自动调用 `auto_developer.develop()`，走六步 DAG 流水线：

```
产品经理分析 → 架构师设计(并行) + 安全工程师审查(并行) → 高级开发者实现 → 代码审查员审查 → 产品经理汇总
```

所有步骤自动执行，无需干预。结果保存在 `ao-output/` 目录。

### 3.2 运行内置工作流（L1）

```
运行 PR 代码审查工作流，PR diff 是 xxx
```

Plector 调用 `agency_orchestrator.run_workflow()`，对应命令：

```yaml
path: "servers/agency-orchestrator/workflows/dev/pr-review.yaml"
inputs:
  pr_diff: "xxx"
provider: "claude-code"
```

### 3.3 自然语言生成工作流（L1）

```
帮我创建一个市场竞品分析的工作流，要覆盖定价、功能、用户评价
```

Plector 调用 `agency_orchestrator.compose_workflow()`，AI 自动选角色、设计 DAG、生成 YAML 文件。

---

## 四、工具详解

### 4.1 L1 — agency_orchestrator（7 个工具）

#### `run_workflow` — 执行工作流

执行 YAML 工作流，DAG 自动并行，变量 `{{output}}` 传递，支持断点续跑。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 工作流 YAML 文件路径 |
| `inputs` | object | ❌ | 输入变量，如 `{"prd_content": "..."}` |
| `provider` | string | ❌ | LLM 提供商，默认 `claude-code` |
| `model` | string | ❌ | 模型名称 |
| `resume` | string | ❌ | 断点续跑：`"last"` 或目录路径 |
| `from_step` | string | ❌ | 从指定步骤重新执行 |

**示例对话**：
```
运行 workflows/dev/pr-review.yaml，输入 pr_diff 是 "feat: add csv export"
```

#### `validate_workflow` — 校验工作流

校验 YAML 文件的语法和结构，不执行。检查必填字段、依赖关系、变量引用。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 工作流 YAML 文件路径 |

**示例对话**：
```
校验 workflows/auto_develop.yaml 的语法
```

#### `list_workflows` — 列出工作流模板

列出 32 个内置工作流模板，覆盖开发、营销、数据、设计、运维、战略、通用等场景。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| （无参数） | | | |

**示例对话**：
```
有哪些可用的工作流？
```

#### `plan_workflow` — 查看执行计划

显示 DAG 执行计划 — 哪些步骤可以并行、哪些必须串行。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 工作流 YAML 文件路径 |

**示例对话**：
```
看下 pr-review 工作流的执行计划
```

#### `compose_workflow` — 自然语言生成工作流

用自然语言描述需求，AI 自动选角色、设计 DAG、生成完整的 YAML 工作流文件。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `description` | string | ✅ | 一句话需求描述 |
| `provider` | string | ❌ | LLM 提供商，默认 `claude-code` |
| `model` | string | ❌ | 模型名称 |

**示例对话**：
```
帮我创建一个工作流：招聘面试，要覆盖简历筛选、技术面试、HR 面试
```

#### `list_roles` — 列出 AI 角色

列出 202 个 AI 角色，按 17 个分类。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | string | ❌ | 只列出指定分类 |

**示例对话**：
```
有哪些工程类角色？
列出所有 marketing 角色
```

#### `get_role` — 获取角色详情

获取角色的完整定义，包含职责、行为规范、system prompt。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `category` | string | ✅ | 角色分类 |
| `name` | string | ✅ | 角色文件名（不含 `.md` 后缀） |

**示例对话**：
```
查看 engineering 分类下的 software-architect 角色详情
```

---

### 4.2 L2 — auto_developer（6 个工具）

#### `develop` — 一键开发

输入需求描述，自动走完整开发流水线（分析→设计+安全→实现→审查→汇总）。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `requirement` | string | ✅ | 开发需求描述 |
| `project_dir` | string | ❌ | 项目目录路径，默认当前目录 |
| `provider` | string | ❌ | LLM 提供商，默认 `claude-code` |

**示例对话**：
```
帮我开发一个用户批量导出 CSV 功能，要求分页、权限校验、异步处理
一键开发：给订单模块加退款功能，要幂等、事务、异步回调
```

#### `compose` — 生成工作流

同 L1 的 `compose_workflow`，更简洁的入口。

#### `run` — 运行工作流

同 L1 的 `run_workflow`，参数名简化（`workflow` 代替 `path`）。

#### `plan` — 查看执行计划

同 L1 的 `plan_workflow`，参数名简化。

#### `list_roles` / `list_workflows`

代理到 L1 的同名工具。

---

## 五、角色分类速查

| 分类 | 数量 | 代表角色 |
|------|------|---------|
| engineering | 27 | software-architect, senior-developer, code-reviewer, security-engineer, devops-engineer |
| marketing | 33 | content-strategist, seo-specialist, brand-manager, xiaohongshu-marketer |
| specialized | 33 | ai-engineer, data-scientist, blockchain-developer, iot-specialist |
| product | 5 | product-manager, product-owner, product-analyst |
| design | 8 | ux-researcher, ui-designer, design-system-architect |
| testing | 9 | qa-engineer, test-automation-engineer, performance-tester |
| support | 8 | technical-support, customer-success, incident-manager |
| sales | 8 | account-executive, sales-engineer, revenue-analyst |
| project-management | 6 | scrum-master, program-manager, release-manager |
| finance | 3 | financial-analyst, investment-advisor |
| strategy | 3 | business-strategist, competitive-analyst |
| game-development | 5 | game-designer, gameplay-programmer |
| spatial-computing | 6 | ar-vr-developer, 3d-artist |
| paid-media | 7 | ppc-specialist, programmatic-buyer |
| hr | 2 | recruiter, interview-specialist |
| legal | 2 | contract-reviewer, compliance-officer |
| supply-chain | 3 | procurement-specialist, logistics-coordinator |

> 完整列表：对 Plector 说 **"列出所有 AI 角色"** 或 **"engineering 分类有哪些角色"**

---

## 六、工作流模板速查

| 分类 | 模板 | 用途 |
|------|------|------|
| **开发** | `dev/pr-review.yaml` | PR 代码审查 |
| | `dev/tech-design-review.yaml` | 技术方案评审 |
| | `dev/security-audit.yaml` | 安全审计 |
| | `dev/api-doc-gen.yaml` | API 文档生成 |
| | `dev/readme-i18n.yaml` | README 多语言翻译 |
| | `dev/release-checklist.yaml` | 发布检查清单 |
| | `dev/tech-debt-audit.yaml` | 技术债审计 |
| **内容** | `content-pipeline.yaml` | 内容生产流水线 |
| | `ai-opinion-article.yaml` | AI 观点文章 |
| | `product-review.yaml` | 产品测评 |
| | `story-creation.yaml` | 小说创作 |
| **营销** | `marketing/competitor-analysis.yaml` | 竞品分析 |
| | `marketing/seo-content-matrix.yaml` | SEO 内容矩阵 |
| | `marketing/xiaohongshu-content.yaml` | 小红书内容 |
| **数据** | `data/dashboard-design.yaml` | 仪表盘设计 |
| | `data/data-pipeline-review.yaml` | 数据流水线审查 |
| **设计** | `design/requirement-to-plan.yaml` | 需求→设计方案 |
| | `design/ux-review.yaml` | 用户体验评审 |
| **运维** | `ops/incident-postmortem.yaml` | 故障复盘 |
| | `ops/sre-health-check.yaml` | SRE 健康检查 |
| | `ops/weekly-report.yaml` | 周报生成 |
| **跨部门** | `department-collab/code-review.yaml` | 跨部门代码审查 |
| | `department-collab/hiring-pipeline.yaml` | 招聘流程 |
| | `department-collab/incident-response.yaml` | 应急响应 |
| | `department-collab/marketing-campaign.yaml` | 营销活动 |
| | `department-collab/content-publish.yaml` | 内容发布 |
| | `department-collab/ceo-org-delegation.yaml` | CEO 组织委派 |
| **战略** | `strategy/business-plan.yaml` | 商业计划书 |
| **HR** | `hr/interview-questions.yaml` | 面试题生成 |
| **法务** | `legal/contract-review.yaml` | 合同审查 |
| **自定义** | `auto_develop.yaml` | 一键自动开发流水线 |

---

## 七、YAML 工作流编写指南

### 7.1 基本结构

```yaml
name: "工作流名称"
description: "工作流描述"

agents_dir: "agency-agents-zh"       # 角色来源（固定值）

llm:
  provider: "claude-code"             # LLM 提供商
  model: "claude-sonnet-4-20250514"  # 模型名称
  max_tokens: 8192                    # 最大 token 数

concurrency: 2                        # 最大并行数

inputs:                               # 输入变量
  - name: requirement
    description: "需求描述"
    required: true

steps:                                # 执行步骤
  - id: analyze                       # 步骤 ID（唯一）
    role: "product/product-manager"   # 角色（分类/角色名）
    task: "分析需求：{{requirement}}" # 任务描述（支持 {{变量}}）
    output: requirements              # 输出变量名

  - id: design
    role: "engineering/engineering-software-architect"
    task: "设计方案：{{requirements}}"
    output: tech_design
    depends_on: [analyze]             # 依赖（可并行的是同一层级）
```

### 7.2 关键语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `{{变量名}}` | 引用前序步骤的 output 或 inputs | `{{requirements}}` |
| `depends_on: [a, b]` | 声明依赖，无依赖的步骤自动并行 | `depends_on: [design, security]` |
| `output: var_name` | 步骤输出保存为变量 | `output: tech_design` |
| `concurrency: N` | 最大并行步骤数 | `concurrency: 3` |
| `resume: "last"` | 断点续跑 | 从上次失败的步骤继续 |

### 7.3 角色引用格式

```
分类名/角色文件名（不含 .md 后缀和分类前缀）
```

| YAML 中的写法 | 对应文件 |
|---------------|---------|
| `product/product-manager` | `external-skills/roles/product/product-manager.md` |
| `engineering/engineering-software-architect` | `external-skills/roles/engineering/engineering-software-architect.md` |
| `marketing/marketing-content-strategist` | `external-skills/roles/marketing/marketing-content-strategist.md` |

### 7.4 DAG 并行示例

```yaml
steps:
  - id: analyze
    role: "product/product-manager"
    task: "分析需求"
    output: requirements

  # design 和 security 并行执行（都只依赖 analyze）
  - id: design
    role: "engineering/engineering-software-architect"
    task: "设计方案：{{requirements}}"
    output: tech_design
    depends_on: [analyze]

  - id: security
    role: "engineering/engineering-security-engineer"
    task: "安全审查：{{requirements}}"
    output: security_review
    depends_on: [analyze]

  # implement 等待 design 和 security 都完成
  - id: implement
    role: "engineering/engineering-senior-developer"
    task: "实现代码：{{tech_design}}\n安全意见：{{security_review}}"
    output: implementation
    depends_on: [design, security]
```

执行流程：
```
analyze ──→ design  ──→ implement
         └→ security ──┘
          (并行)
```

---

## 八、LLM 提供商配置

### 8.1 免 API key 方案（推荐）

| 提供商 | YAML 值 | 安装 CLI | 费用 |
|--------|---------|---------|------|
| Claude Max/Pro | `claude-code` | `npm i -g @anthropic-ai/claude-code` | 已有会员 |
| Google 账号 | `gemini-cli` | `npm i -g @google/gemini-cli` | 免费 |
| GitHub Copilot | `copilot-cli` | `npm i -g @github/copilot` | 已有会员 |
| ChatGPT Plus | `codex-cli` | `npm i -g @openai/codex` | 已有会员 |
| OpenClaw | `openclaw-cli` | `npm i -g openclaw` | 已有会员 |
| 本地模型 | `ollama` | [ollama.ai](https://ollama.ai) | 免费 |

### 8.2 传统 API key 方案

| 提供商 | YAML 值 | 环境变量 |
|--------|---------|---------|
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |
| Claude API | `claude` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |

### 8.3 Plector 中的默认配置

Plector 已将 `claude-code` 设为默认 provider，无需额外配置。如果你需要切换：

```
用 ollama 运行这个工作流
```

或在 YAML 中指定：

```yaml
llm:
  provider: "ollama"
  model: "qwen3:4b"
```

---

## 九、高级用法

### 9.1 断点续跑

工作流执行中断后，从上次的进度继续：

```
继续上次的工作流
```

或指定具体步骤：

```
从 implement 步骤重新执行工作流 xxx
```

### 9.2 CLI 直接使用

除了通过 Plector 对话，也可以直接用 `ao` 命令行：

```bash
cd E:\产品\Plector\servers\agency-orchestrator

# 零配置体验
npx ao demo

# 列出工作流
npx ao list

# 执行工作流
npx ao run workflows/dev/pr-review.yaml --input pr_diff="feat: add csv export"

# 自然语言生成工作流
npx ao compose "PR代码审查，覆盖安全和性能"

# 校验工作流
npx ao validate workflows/auto_develop.yaml

# 查看执行计划
npx ao plan workflows/auto_develop.yaml

# 断点续跑
npx ao run workflows/auto_develop.yaml --resume last
```

### 9.3 自定义工作流

1. 对 Plector 说：**"帮我创建一个工作流：xxx"** → 自动生成
2. 或手动创建 YAML 文件放到 `workflows/` 目录
3. 运行前先校验：**"校验 workflows/xxx.yaml"**
4. 查看执行计划：**"看下 workflows/xxx.yaml 的 DAG 计划"**

### 9.4 查看执行结果

工作流执行结果保存在 `ao-output/` 目录：

```
ao-output/
└── 2026-04-15_14-30-00_自动开发流水线/
    ├── analyze.md        # 产品经理分析结果
    ├── design.md         # 架构师设计
    ├── security.md       # 安全审查
    ├── implement.md      # 代码实现
    ├── review.md         # 代码审查
    └── summary.md        # 汇总报告
```

对 Plector 说：**"读取最新的开发结果摘要"** → 调用 `auto_developer.read_latest_summary()`

---

## 十、常见问题

### Q: MCP Server 启动不了？

**检查项**：
1. `servers/agency-orchestrator/dist/cli.js` 是否存在
2. `node -v` 是否 ≥ 18
3. 如果 `dist/` 不存在：`cd servers/agency-orchestrator && npm install && npm run build`

### Q: "需要 API key" 报错？

确保 `provider` 设为 `claude-code`（不是 `claude`），且已安装 Claude Code CLI。

### Q: 角色文件找不到？

确认 `AGENTS_DIR` 指向正确：
- config.yaml 中：`AGENTS_DIR: "external-skills/roles"`
- 角色目录：`E:\产品\Plector\external-skills\roles\` 应有 17 个分类子目录

### Q: 如何添加自定义角色？

1. 在 `external-skills/roles/` 对应分类目录下创建 `.md` 文件
2. 格式参考已有角色文件（含 YAML frontmatter）
3. 在工作流中用 `分类名/角色名` 引用

### Q: L1 和 L2 怎么选？

| 场景 | 用哪个 |
|------|--------|
| "帮我开发xxx" | L2 (`auto_developer`) |
| "运行这个工作流" | L1 或 L2 都行 |
| "帮我创建工作流" | L1 (`agency_orchestrator`) |
| "查看角色详情" | L1 |
| "校验工作流" | L1 |
| 需要 `resume` / `from_step` | L1 |

---

## 十一、架构说明

```
用户对话
  ↓
Plector Agent Loop
  ↓
┌─────────────────────────────────┐
│ L2: auto_developer              │  ← 一键开发入口
│   develop() → run_workflow()    │
│   compose() → compose_workflow()│
│   list_roles() → L1 代理        │
└──────────┬──────────────────────┘
           │ _mcp_call
           ↓
┌─────────────────────────────────┐
│ L1: agency_orchestrator         │  ← MCP Server 封装
│   本地：list_roles / get_role   │  ← 直接读文件，快
│   本地：list_workflows          │
│   MCP：run / validate / plan    │  ← 走 MCP Server
│   MCP：compose                  │
└──────────┬──────────────────────┘
           │ stdio MCP
           ↓
┌─────────────────────────────────┐
│ Agency Orchestrator MCP Server  │  ← Node.js 进程
│   9 个工具                       │
│   DAG 引擎 / CLI 执行器          │
│   claude-code provider          │
└─────────────────────────────────┘
```

**数据流**：
1. 用户说话 → Plector 匹配到 auto_developer 或 agency_orchestrator 技能
2. L2 技能内部组装 `_mcp_call` 请求
3. Plector MCP Client 通过 stdio 发送给 ao MCP Server
4. ao Server 解析 YAML → 加载角色 → 调用 claude-code CLI 执行
5. 结果写回 `ao-output/` 目录
6. 事件通过 CloudEvents 格式发布到 Plector event_bus

---

## 十二、文件位置速查

| 文件 | 路径 |
|------|------|
| L1 技能定义 | `skills/agency_orchestrator/skill.json` |
| L1 技能实现 | `skills/agency_orchestrator/implementation.py` |
| L1 技能说明 | `skills/agency_orchestrator/SKILL.md` |
| L2 技能定义 | `skills/auto_developer/skill.json` |
| L2 技能实现 | `skills/auto_developer/implementation.py` |
| L2 技能说明 | `skills/auto_developer/SKILL.md` |
| MCP Server | `servers/agency-orchestrator/` |
| MCP Server 入口 | `servers/agency-orchestrator/dist/cli.js` |
| 角色目录 | `external-skills/roles/` |
| 工作流模板 | `servers/agency-orchestrator/workflows/` |
| 自动开发工作流 | `workflows/auto_develop.yaml` |
| 执行结果输出 | `ao-output/` |
| MCP 配置 | `config/config.yaml` → `mcp.servers.agency-orchestrator` |
| 集成方案文档 | `E:\Plector开发流程\69_v1.5_agency-orchestrator合并方案操作手册.md` |

---

*最后更新：2026-04-15 · 分支 `develop/agency-orchestrator`*

