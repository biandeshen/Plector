# Plector 文档索引导航

> AI 文档阅读指南 | 版本: v1.1.0 | 最后更新: 2026-04-28

---

## 零、快速索引（完整文档清单）

> 以下是 Plector 项目所有文档的完整索引，分为**公共规范**和**项目专属**两部分。

### 公共规范（跨项目通用）

| 内容 | 位置 |
|------|------|
| 开发规范模板 | `E:/笔记/Claude Code规范/CLAUDE_Template.md` |
| 元认知规则模板 | `E:/笔记/Claude Code规范/SOUL_Template.md` |
| 任务计划模板 | `E:/笔记/Claude Code规范/PLAN_Template.md` |
| Claude Code 工具 | `E:/笔记/Claude Code规范/CLAUDE_CODE_TOOLS.md` |
| 代码规范 | `E:/笔记/Claude Code规范/Coding_Convention.md` |
| 命名规范 | `E:/笔记/Claude Code规范/Naming_Convention.md` |
| 技能开发规范 | `E:/笔记/Claude Code规范/Skill_Development_Convention.md` |
| 密钥管理 | `E:/笔记/Claude Code规范/Secrets_Management.md` |
| Agent 行为规则 | `E:/笔记/Claude Code规范/Agent_Behavior_Rules.md` |
| 提交规范 | `E:/笔记/Claude Code规范/Commit_Convention.md` |
| 语言约定 | `E:/笔记/Claude Code规范/Language_Convention.md` |
| 前端修改规范 | `E:/笔记/Claude Code规范/Frontend_Modification_Rules.md` |

### 项目专属（Plector）

| 内容 | 位置 |
|------|------|
| **文档索引导航** | `docs/DOCS_INDEX.md` ⭐ 本文件 |
| Plector 技能文档 | `docs/PLECTOR_SKILLS.md` |
| Plector 代码规范 | `docs/standards/Code_Standard_Plector.md` |
| Plector 命名规范 | `docs/standards/Naming_Convention_Plector.md` |
| Plector 技能开发 | `docs/standards/Skill_Development_Plector.md` |
| MCP Server 指南 | `docs/guides/MCP_Server_Guide.md` |
| 部署指南 | `docs/guides/Deployment_Guide.md` |
| 配置参考 | `docs/guides/Configuration_Reference.md` |
| 设计文档 | `docs/specs/Design_Plector_v1.2.md` |
| SOUL.md（元认知规则） | `SOUL.md` |
| Plector 项目技能 | `CLAUDE_PLECTOR_TOOLS.md` |
| 前端设计方案 | `docs/notes/Plector_前端设计方案.md` |
| Lobe Chat 集成方案 | `docs/notes/Plector_LobeChat_集成方案.md` |
| WebSocket 适配代码 | `docs/notes/Plector_WebSocket_适配代码.md` |

### 开源必备（根目录）

| 内容 | 位置 | 说明 |
|------|------|------|
| **许可证** | `LICENSE` | MIT 开源许可 |
| **贡献指南** | `CONTRIBUTING.md` | 如何贡献代码 |
| **安全策略** | `SECURITY.md` | 漏洞报告流程 |
| **行为准则** | `CODE_OF_CONDUCT.md` | 社区行为规范 |
| **版本历史** | `CHANGELOG.md` | 版本变更记录 |

---

## 一、快速入口（按任务类型）

| 任务 | 入口文档 | 预计阅读时间 |
|------|----------|-------------|
| [新功能开发](#新功能开发路径) | CLAUDE.md → PRD | ~15 分钟 |
| [Bug 修复](#bug修复路径) | CLAUDE.md → 技术规范 | ~10 分钟 |
| [技能开发](#技能开发路径) | CLAUDE.md → Skill 开发规范 | ~20 分钟 |
| [前端修改](#前端修改路径) | CLAUDE.md → 前端设计方案 | ~15 分钟 |
| [API 开发](#api开发路径) | 技术规范 → REST_API.md | ~15 分钟 |
| [文档编写](#文档编写路径) | CLAUDE.md → 语言约定 | ~10 分钟 |
| [系统重构](#系统重构路径) | SOUL.md → 技术设计 | ~30 分钟 |

---

## 二、任务-文档映射表

### 2.1 基础层（所有任务必读）

| 优先级 | 文档 | 作用 | 何时读 |
|--------|------|------|--------|
| **Must** | [CLAUDE.md](../CLAUDE.md) | AI 行为规范 + 强制约束 | 任何任务的第一位 |
| Should | [SOUL.md](../SOUL.md) | 元认知规则 + 决策树 | 理解任务复杂度时 |
| Could | [PLAN_TEMPLATE.md](../PLAN_TEMPLATE.md) | 任务计划模板 | 需要创建 Plan.md 时 |

### 2.2 新功能开发路径

| 阶段 | 文档 | 目的 |
|------|------|------|
| 规范 | [CLAUDE.md](../CLAUDE.md) | 行为约束 |
| 规范 | [SOUL.md](../SOUL.md) | 决策树 |
| 需求 | [docs/specs/PRD/PRD_Plector_v1.8.md](specs/PRD/PRD_Plector_v1.8.md) | 功能范围 |
| 设计 | [docs/specs/Design_Plector_v1.2.md](specs/Design_Plector_v1.2.md) | 技术架构 |
| 设计 | [docs/standards/Technical_Spec_Plector.md](standards/Technical_Spec_Plector.md) | 接口规范 |
| 编码 | [docs/standards/Code_Standard_Plector.md](standards/Code_Standard_Plector.md) | 代码规范 |
| 编码 | [docs/standards/Naming_Convention_Plector.md](standards/Naming_Convention_Plector.md) | 命名规范 |
| 参考 | [docs/PLECTOR_SKILLS.md](../docs/PLECTOR_SKILLS.md) | 技能总览 |

### 2.3 Bug 修复路径

| 阶段 | 文档 | 目的 |
|------|------|------|
| 规范 | [CLAUDE.md 第1-3节](../CLAUDE.md) | 假设验证 + 熔断 |
| 上下文 | [SOUL.md](../SOUL.md) | 出错处理流程 |
| 规范 | [docs/standards/Code_Standard_Plector.md](standards/Code_Standard_Plector.md) | 代码规范 |
| 设计 | [docs/specs/Design_Plector_v1.2.md](specs/Design_Plector_v1.2.md) | 设计意图 |

### 2.4 技能开发路径

| 阶段 | 文档 | 目的 |
|------|------|------|
| 规范 | [CLAUDE.md](../CLAUDE.md) | 行为规范 |
| 体系 | [docs/PLECTOR_SKILLS.md](../docs/PLECTOR_SKILLS.md) | 技能清单 |
| 设计 | [docs/SKILL_DESIGN_PRINCIPLES.md](../docs/SKILL_DESIGN_PRINCIPLES.md) | 设计原则 |
| 规范 | [docs/standards/Skill_Development_Plector.md](standards/Skill_Development_Plector.md) | 开发规范 |
| 参考 | [skills/memory/SKILL.md](../skills/memory/SKILL.md) | 技能示例 |

### 2.5 前端修改路径

| 阶段 | 文档 | 目的 |
|------|------|------|
| 规范 | [CLAUDE.md 第3节](../CLAUDE.md) | 前端修改规范 |
| 规范 | [SOUL.md 第5节](../SOUL.md) | 三步防退化 |
| 设计 | [docs/notes/Plector_前端设计方案.md](notes/Plector_前端设计方案.md) | 前端架构 |
| 通信 | [docs/notes/Plector_WebSocket_适配代码.md](notes/Plector_WebSocket_适配代码.md) | WebSocket |

### 2.6 API 开发路径

| 阶段 | 文档 | 目的 |
|------|------|------|
| 设计 | [docs/standards/Technical_Spec_Plector.md](standards/Technical_Spec_Plector.md) | 接口规范 |
| API | [docs/api/REST_API.md](api/REST_API.md) | REST 接口 |
| API | [docs/api/WebSocket_API.md](api/WebSocket_API.md) | WebSocket 接口 |
| 开发 | [docs/guides/MCP_Server_Guide.md](guides/MCP_Server_Guide.md) | MCP 开发 |

---

## 三、文档依赖关系图

```
graph TD
    CLAUDE([CLAUDE.md<br/>AI 行为规范])
    SOUL([SOUL.md<br/>元认知规则])

    CODE_STD([docs/standards/Code_Standard_Plector.md])
    NAMING([docs/standards/Naming_Convention_Plector.md])
    SKILL_DEV([docs/standards/Skill_Development_Plector.md])
    SKILL_PRIN([docs/SKILL_DESIGN_PRINCIPLES.md])

    BRD([docs/specs/BRD/])
    PRD([docs/specs/PRD/])
    DESIGN([docs/specs/Design_Plector_v1.2.md])
    TECH_SPEC([docs/standards/Technical_Spec_Plector.md])

    SKILLS([docs/PLECTOR_SKILLS.md])
    GUIDES([docs/guides/])

    SKILL_FILES([skills/*/SKILL.md])

    CLAUDE --> SOUL
    CLAUDE --> CODE_STD
    SOUL --> CODE_STD

    CODE_STD --> NAMING
    CODE_STD --> SKILL_DEV

    SKILL_PRIN --> SKILL_DEV
    SKILL_DEV --> SKILL_FILES

    BRD --> PRD
    PRD --> DESIGN

    DESIGN --> TECH_SPEC
    TECH_SPEC --> GUIDES

    CLAUDE --> SKILLS
    SKILLS --> SKILL_FILES
```

---

## 四、执行流程示例

### 4.1 新功能开发完整流程

```
步骤 1：阅读约束规范（必读）
  [CLAUDE.md] → 理解强制行为约束（假设验证、熔断机制、变更记录）
      ↓
  [SOUL.md] → 理解决策树和技能联动机制

步骤 2：需求分析
  [docs/specs/PRD/PRD_Plector_v1.8.md] → 理解功能范围和验收标准

步骤 3：技术设计
  [docs/specs/Design_Plector_v1.2.md] → 理解架构设计和模块关系
  [docs/standards/Technical_Spec_Plector.md] → 理解接口规范

步骤 4：编码实现
  [docs/standards/Code_Standard_Plector.md] → 遵循代码规范
  [docs/standards/Naming_Convention_Plector.md] → 遵循命名规范
  [skills/*/SKILL.md] → 参考现有技能实现模式

步骤 5：测试与记录
  [docs/PLECTOR_SKILLS.md] → 运行验证命令
  创建/更新 Plan.md → 记录执行过程
```

### 4.2 Bug 修复流程

```
步骤 1：确认修复约束
  [CLAUDE.md 第 1-3 节] → 假设验证 + 熔断机制

步骤 2：理解错误上下文
  [SOUL.md 出错处理流程] → 2次熔断规则

步骤 3：定位问题
  [docs/specs/Design_Plector_v1.2.md] → 理解设计意图
  [docs/standards/Code_Standard_Plector.md] → 理解代码规范

步骤 4：验证
  [skills/test_runner/SKILL.md] → 运行测试
  ruff check core/ skills/ channels/ → 代码检查
```

---

## 五、交叉引用机制

### 5.1 引用格式约定

| 前缀 | 用途 | 示例 |
|------|------|------|
| `[规范:xxx]` | 代码/技能/技术规范 | `[规范:代码标准]` |
| `[规格:xxx]` | BRD/PRD/Design | `[规格:PRDv1.8]` |
| `[指南:xxx]` | 部署/配置/开发指南 | `[指南:部署]` |
| `[API:xxx]` | REST/WebSocket API | `[API:REST]` |
| `[技能:xxx]` | 具体技能 | `[技能:memory]` |
| `[工具:xxx]` | 具体工具 | `[工具:save_conversation]` |
| `[模板:xxx]` | Plan/TASK 等模板 | `[模板:Plan]` |

### 5.2 触发词-文档映射

| 触发词/场景 | 导航到 |
|------------|--------|
| "假设"、"验证" | CLAUDE.md 第 1 节 |
| "熔断"、"错误" | CLAUDE.md 第 2 节 |
| "前端"、"UI" | CLAUDE.md 第 3 节 |
| "复杂任务"、"多角色" | SOUL.md 决策树 |
| "技能"、"trigger" | docs/SKILL_DESIGN_PRINCIPLES.md |
| "测试"、"pytest" | skills/test_runner/SKILL.md |
| "MCP"、"协议" | docs/standards/Technical_Spec_Plector.md |
| "工作流"、"编排" | skills/agency_orchestrator/SKILL.md |

### 5.3 快速查找表

```
┌──────────────────────────────────────────────────────────┐
│  遇到问题 → 查哪里                                        │
├──────────────────────────────────────────────────────────┤
│  不确定任务复杂度      → SOUL.md 决策树                   │
│  修改现有代码         → CLAUDE.md 三步防退化流水线        │
│  创建新技能           → SKILL_DESIGN_PRINCIPLES.md        │
│  不知道用什么命名     → Naming_Convention_Plector.md     │
│  不知道接口格式       → Technical_Spec_Plector.md        │
│  需要运行测试         → skills/test_runner/SKILL.md       │
│  不知道有哪些技能     → docs/PLECTOR_SKILLS.md           │
│  想了解项目架构       → docs/specs/Design_Plector_v1.2.md │
│  想了解功能范围       → PRD_Plector_v1.8.md              │
│  想了解商业目标       → BRD_Plector_v2.2.md              │
└──────────────────────────────────────────────────────────┘
```

---

## 六、文档目录树

```
Plector/
├── CLAUDE.md                    ⭐ AI 入口规范（行为约束）
├── SOUL.md                      ⭐ AI 人格定义（元认知规则）
├── PLAN_TEMPLATE.md             任务计划模板
├── TASK.md                      任务模板
│
├── docs/
│   ├── PLECTOR_SKILLS.md       技能总览
│   ├── SKILL_DESIGN_PRINCIPLES.md  技能设计原则
│   ├── SECRETS.md               密钥管理
│   │
│   ├── specs/                   规格文档
│   │   ├── BRD/                 商业需求
│   │   ├── PRD/                 产品需求
│   │   └── Design_Plector_v1.2.md  技术设计
│   │
│   ├── standards/               开发标准
│   │   ├── Code_Standard_Plector.md
│   │   ├── Naming_Convention_Plector.md
│   │   ├── Skill_Development_Plector.md
│   │   └── Technical_Spec_Plector.md
│   │
│   ├── guides/                  用户指南
│   ├── api/                     API 文档
│   ├── notes/                   设计笔记
│   └── reports/                 状态报告
│
└── skills/                      技能定义
    └── */SKILL.md
```

---

## 七、版本历史

- v1.0.0 (2026-04-28)：初始版本，定义文档索引导航系统
