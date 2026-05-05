# Plector 项目文档索引导航

> 版本：v3.0.0 | 最后更新：2026-04-28

---

## 一、文档架构说明

### 核心原则

> **工具规范与项目规范分离**
> - Claude Code 工具规范 → `E:/笔记/Claude Code规范/`
> - Plector 项目规范 → 本目录

### 双索引架构

```
┌─────────────────────────────────────────────────────────────┐
│  E:/笔记/Claude Code规范/DOCS_INDEX.md                       │
│  Claude Code 工具规范索引（跨项目通用）                       │
│  └── Agent_Behavior_Rules.md                                │
│  └── Coding_Convention.md                                  │
│  └── Commit_Convention.md                                   │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓ 引用
┌─────────────────────────────────────────────────────────────┐
│  e:/产品/Plector/docs/DOCS_INDEX.md                          │
│  Plector 项目文档索引（项目专用）                            │
│  └── 技能系统                                                │
│  └── 技术规格                                                │
│  └── 规格文档（BRD/PRD/设计）                                │
│  └── 用户指南                                                │
│  └── API 文档                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、Claude Code 工具规范

> ⚠️ 以下规范来自 `E:/笔记/Claude Code规范/`，跨项目通用。
> 完整索引：[E:/笔记/Claude Code规范/DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md)

| 规范 | 说明 |
|------|------|
| [行为规则](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md) | 假设验证、错误熔断、变更记录、主动升级 |
| [Plan 模板](file:///E:/笔记/Claude Code规范/PLAN_Template.md) | 任务计划格式、执行日志 |
| [前端规范](file:///E:/笔记/Claude Code规范/Frontend_Modification_Rules.md) | 考古学家+外科医生模式 |
| [提交规范](file:///E:/笔记/Claude Code规范/Commit_Convention.md) | feat/fix/docs 等 type |
| [代码规范](file:///E:/笔记/Claude Code规范/Coding_Convention.md) | Python 命名、导入、函数设计 |
| [语言约定](file:///E:/笔记/Claude Code规范/Language_Convention.md) | 中文对话/英文代码 |
| [技能开发](file:///E:/笔记/Claude Code规范/Skill_Development_Convention.md) | SKILL.md 格式、工作流 |
| [工具指南](file:///E:/笔记/Claude Code规范/CLAUDE_CODE_TOOLS.md) | Claude Code 使用建议 |

---

## 三、Plector 项目文档

### A. 根目录核心文档（AI 必读）

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](../CLAUDE.md) | 项目入口索引 |
| [SOUL.md](../SOUL.md) | Plector 灵魂（决策树、技能联动） |
| [PLAN_TEMPLATE.md](../PLAN_TEMPLATE.md) | 任务计划模板 |

### B. 开源必备

| 文档 | 说明 |
|------|------|
| [LICENSE](../LICENSE) | MIT 开源许可 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献指南 |
| [SECURITY.md](../SECURITY.md) | 安全策略 |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | 行为准则 |
| [CHANGELOG.md](../CHANGELOG.md) | 版本历史 |
| [README.md](../README.md) | 项目介绍 |

### C. 文档导航

| 文档 | 说明 |
|------|------|
| **docs/DOCS_INDEX.md** | ⭐ 本文件 |
| [PLECTOR_SKILLS.md](PLECTOR_SKILLS.md) | 技能总览（7个技能） |
| [SKILL_DESIGN_PRINCIPLES.md](SKILL_DESIGN_PRINCIPLES.md) | 技能设计原则 |
| [SYNCHRONIZATION_MECHANISM.md](SYNCHRONIZATION_MECHANISM.md) | 同步机制 |

### D. 规格文档（specs/）

| 文档 | 说明 |
|------|------|
| [specs/BRD/SPEC_INDEX.md](specs/BRD/SPEC_INDEX.md) | BRD 索引 |
| [specs/PRD/SPEC_INDEX.md](specs/PRD/SPEC_INDEX.md) | PRD 索引 |
| [specs/Design_Plector_v1.2.md](specs/Design_Plector_v1.2.md) | 技术设计 |

### E. Plector 特有规范（standards/）

| 文档 | 说明 |
|------|------|
| [standards/Behavior_Rules_Plector.md](standards/Behavior_Rules_Plector.md) | 行为规则 |
| [standards/Code_Standard_Plector.md](standards/Code_Standard_Plector.md) | 编码规范 |
| [standards/Commit_Convention_Plector.md](standards/Commit_Convention_Plector.md) | 提交规范 |
| [standards/Frontend_Modification_Rules.md](standards/Frontend_Modification_Rules.md) | 前端修改规则 |
| [standards/Language_Convention_Plector.md](standards/Language_Convention_Plector.md) | 语言约定 |
| [standards/Naming_Convention_Plector.md](standards/Naming_Convention_Plector.md) | 命名规范 |
| [standards/Technical_Spec_Plector.md](standards/Technical_Spec_Plector.md) | 技术规格（JSON-RPC/MCP） |
| [standards/Skill_Development_Plector.md](standards/Skill_Development_Plector.md) | 技能开发规范（Plector tier 系统） |
| [standards/Plan_Execution_Rules.md](standards/Plan_Execution_Rules.md) | Plan 执行规则 |

### F. 用户指南（guides/）

| 文档 | 说明 |
|------|------|
| [guides/Deployment_Guide.md](guides/Deployment_Guide.md) | 部署指南 |
| [guides/MCP_Server_Guide.md](guides/MCP_Server_Guide.md) | MCP Server 开发 |
| [guides/Configuration_Reference.md](guides/Configuration_Reference.md) | 配置参考 |

### G. API 文档（api/）

| 文档 | 说明 |
|------|------|
| [api/REST_API.md](api/REST_API.md) | REST API |
| [api/WebSocket_API.md](api/WebSocket_API.md) | WebSocket API |

### H. 设计笔记（notes/）

| 文档 | 说明 |
|------|------|
| [notes/Plector_前端设计方案.md](notes/Plector_前端设计方案.md) | Vue3 前端架构 |
| [notes/Plector_LobeChat_集成方案.md](notes/Plector_LobeChat_集成方案.md) | Lobe Chat 集成 |
| [notes/Plector_WebSocket_适配代码.md](notes/Plector_WebSocket_适配代码.md) | WebSocket 适配 |

### I. 技能定义（skills/*/）

| 技能 | 说明 |
|------|------|
| [skills/memory/SKILL.md](../skills/memory/SKILL.md) | 记忆系统 |
| [skills/file_utils/SKILL.md](../skills/file_utils/SKILL.md) | 文件操作 |
| [skills/code_writer/SKILL.md](../skills/code_writer/SKILL.md) | 代码编写 |
| [skills/error_knowledge/SKILL.md](../skills/error_knowledge/SKILL.md) | 错误知识库 |
| [skills/web_search/SKILL.md](../skills/web_search/SKILL.md) | 网络搜索 |
| [skills/test_runner/SKILL.md](../skills/test_runner/SKILL.md) | 测试执行 |
| [skills/health_monitor/SKILL.md](../skills/health_monitor/SKILL.md) | 健康监控 |

---

## 四、文档依赖关系图

```
                         ┌─────────────────────────────────────────┐
                         │            CLAUDE.md (项目入口)        │
                         └──────────────────┬──────────────────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────────────────┐
          │                                 │                                 │
          ▼                                 ▼                                 ▼
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│ SOUL.md (灵魂)   │              │ PRD (产品需求)  │              │ Design (技术设计) │
└────────┬─────────┘              └────────┬─────────┘              └────────┬─────────┘
         │                                   │                                 │
         │         ┌───────────────────────┼───────────────────────┐         │
         │         │                       │                       │         │
         ▼         ▼                       ▼                       ▼         ▼
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│   PLECTOR       │              │   Tech Spec     │              │   MCP Server    │
│   SKILLS        │              │  (Plector专用)   │              │   Guide         │
│  (技能系统)      │              └─────────────────┘              └─────────────────┘
└─────────────────┘

                           ┌─────────────────────────────────────────┐
                           │   E:/笔记/Claude Code规范/DOCS_INDEX.md │
                           │   Claude Code 工具规范（跨项目）        │
                           └─────────────────────────────────────────┘
```

---

## 五、快速查找表

| 遇到问题 | 查哪里 |
|----------|--------|
| Plector 有哪些技能 | [PLECTOR_SKILLS.md](PLECTOR_SKILLS.md) |
| 如何开发新技能 | [SKILL_DESIGN_PRINCIPLES.md](SKILL_DESIGN_PRINCIPLES.md) |
| 技术规格是什么 | [standards/Technical_Spec_Plector.md](standards/Technical_Spec_Plector.md) |
| 如何部署 | [guides/Deployment_Guide.md](guides/Deployment_Guide.md) |
| 如何开发 MCP Server | [guides/MCP_Server_Guide.md](guides/MCP_Server_Guide.md) |
| API 接口格式 | [api/REST_API.md](api/REST_API.md) |
| WebSocket 协议 | [api/WebSocket_API.md](api/WebSocket_API.md) |
| 行为规则是什么 | [E:/笔记/Claude Code规范/Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md) |
| 提交规范是什么 | [E:/笔记/Claude Code规范/Commit_Convention.md](file:///E:/笔记/Claude Code规范/Commit_Convention.md) |

---

## 六、版本历史

- `v3.0.0` (2026-04-28)：重构为纯项目索引；Claude Code 工具规范引用到 E:/笔记/Claude Code规范/；移除与通用规范重复的内容
- `v2.0.0` (2026-04-28)：明确"工具是工具，项目是项目"分层原则
- `v1.0.0` (2026-04-28)：初始版本

---

*本索引仅包含 Plector 项目专用文档。通用 Claude Code 规范请见 `E:/笔记/Claude Code规范/DOCS_INDEX.md`*
