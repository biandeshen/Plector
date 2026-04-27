# v0.3 — AI 编程助手多智能体编排引擎 设计文档

**定位：** agency-orchestrator = AI 编程工具里的 docker-compose。开发者用 YAML 定义多智能体协作，直接在 Claude Code / Cursor / Kiro / Trae 等工具里运行。

**目标：** 从 31★ 的小工具成长为 AI 编程生态的标配编排层，利用 agents-zh 2182★ 的流量飞轮。

**三阶段交付：**

| 阶段 | 主题 | 核心成果 |
|------|------|---------|
| v0.3.0 | 扩入口 | 6+ AI 工具集成 + `ao init --workflow` + 12 个新 workflow 模板 |
| v0.3.1 | 提体验 | `ao explain` + `ao watch` + 文档完善 |
| v0.3.2 | 开国际 | MCP Server 模式 + 英文角色支持 |

---

## 架构决策

### 1. Skill 集成文件是一等公民

每个 AI 编程工具的集成 = 一个 `.md` 文件，教工具如何解析 YAML、加载角色、执行 workflow。现有 `integrations/cursor/workflow-runner.mdc` 是标杆实现，其他工具照搬这套模式。

### 2. CLI 新增命令遵循 Unix 哲学

- `ao init --workflow` — 交互式创建 workflow（stdin/stdout，不依赖 TUI 库）
- `ao explain` — 输出 DAG 的自然语言解释（纯文本，可 pipe）
- `ao watch` — 实时终端进度（唯一用 ANSI escape 的命令）

### 3. Workflow 模板 = 内容营销

每个模板覆盖一个高频开发场景，自带完整的 task prompt，开箱即用。模板同时是产品功能和推广素材。

### 4. MCP Server 模式（v0.3.2）

把 ao 引擎包装为 MCP Tool，暴露 `run_workflow` / `list_roles` / `explain_workflow` 三个 tool。任何 MCP 客户端都能调用。

---

## 文件结构规划

### 新增集成文件

```
integrations/
├── claude-code/README.md       ✅ 已有
├── cursor/                     ✅ 已有
│   ├── README.md
│   └── workflow-runner.mdc
├── openclaw/README.md          ✅ 已有
├── kiro/                       🔲 新增
│   ├── README.md
│   └── ao-workflow-runner.md
├── trae/                       🔲 新增
│   ├── README.md
│   └── ao-workflow-runner.md
├── gemini-cli/                 🔲 新增
│   ├── README.md
│   └── GEMINI.md
├── codex/                      🔲 新增
│   ├── README.md
│   └── instructions.md
├── deerflow/                   🔲 新增
│   ├── README.md
│   └── SKILL.md
└── antigravity/                🔲 新增
    ├── README.md
    └── AGENTS.md
```

### 新增 workflow 模板

```
workflows/
├── content-pipeline.yaml       ✅ 已有
├── product-review.yaml         ✅ 已有
├── story-creation.yaml         ✅ 已有
├── department-collab/
│   ├── code-review.yaml        ✅ 已有
│   ├── content-publish.yaml    ✅ 已有
│   ├── hiring-pipeline.yaml    ✅ 已有
│   ├── incident-response.yaml  ✅ 已有
│   └── marketing-campaign.yaml ✅ 已有
├── dev/                        🔲 新增目录
│   ├── pr-review.yaml
│   ├── tech-debt-audit.yaml
│   ├── api-doc-gen.yaml
│   ├── readme-i18n.yaml
│   ├── security-audit.yaml
│   └── release-checklist.yaml
├── data/                       🔲 新增目录
│   ├── data-pipeline-review.yaml
│   └── dashboard-design.yaml
├── design/                     🔲 新增目录
│   ├── requirement-to-plan.yaml
│   └── ux-review.yaml
└── ops/                        🔲 新增目录
    ├── incident-postmortem.yaml
    └── sre-health-check.yaml
```

### 新增 CLI 源文件

```
src/
├── cli.ts                      修改：新增 explain / watch 命令入口
├── cli/                        🔲 新增目录
│   ├── init-workflow.ts        ao init --workflow 交互逻辑
│   ├── explain.ts              ao explain 自然语言解释
│   └── watch.ts                ao watch 实时进度
├── core/
│   └── executor.ts             修改：增加进度事件回调
├── mcp/                        🔲 新增目录（v0.3.2）
│   ├── server.ts               MCP stdio server
│   └── tools.ts                run_workflow / list_roles / explain_workflow
└── ...
```
