# Plector 文档索引导航

> AI 文档阅读指南 | 版本: v1.2.0 | 最后更新: 2026-04-28

---

## 零、完整文档索引

> 以下是 Plector 项目**所有文档**的完整索引，包含位置、分类、层级和关联关系。

### A. 根目录核心文档（AI 必读）

| 文档 | 分类 | 层级 | 说明 |
|------|------|------|------|
| [CLAUDE.md](../CLAUDE.md) | 行为规范 | ⭐⭐⭐ 必须 | AI 行为约束、熔断机制、假设验证 |
| [SOUL.md](../SOUL.md) | 元认知 | ⭐⭐ 重要 | 决策树、技能联动、复杂任务处理 |
| [PLAN_TEMPLATE.md](../PLAN_TEMPLATE.md) | 模板 | ⭐ 辅助 | 任务计划模板 |

### B. 开源必备文档（根目录）

| 文档 | 分类 | 说明 |
|------|------|------|
| [LICENSE](../LICENSE) | 许可证 | MIT 开源许可 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献 | 如何贡献代码、提交规范 |
| [SECURITY.md](../SECURITY.md) | 安全 | 安全漏洞报告流程、内置安全功能 |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | 社区 | Contributor Covenant 行为准则 |
| [CHANGELOG.md](../CHANGELOG.md) | 版本 | 版本历史和变更记录 |
| [README.md](../README.md) | 介绍 | 项目概述、快速开始 |

### C. 项目专用文档（docs/ 目录）

#### C1. 文档导航（⭐ 本系统入口）

| 文档 | 说明 |
|------|------|
| **docs/DOCS_INDEX.md** | ⭐ 本文件 - 统一文档导航入口 |
| [docs/PLECTOR_SKILLS.md](PLECTOR_SKILLS.md) | 技能总览与治理规则 |
| [docs/SKILL_DESIGN_PRINCIPLES.md](SKILL_DESIGN_PRINCIPLES.md) | 技能设计原则与模式 |
| [docs/SECRETS.md](SECRETS.md) | 密钥管理规范 |

#### C2. 规格文档（specs/）

| 文档 | 分类 | 说明 |
|------|------|------|
| [specs/BRD/SPEC_INDEX.md](specs/BRD/SPEC_INDEX.md) | 商业 | BRD 索引 |
| [specs/BRD/BRD_Plector_v2.2.md](specs/BRD/BRD_Plector_v2.2.md) | 商业 | 商业需求文档 v2.2 |
| [specs/PRD/SPEC_INDEX.md](specs/PRD/SPEC_INDEX.md) | 产品 | PRD 索引 |
| [specs/PRD/PRD_Plector_v1.8.md](specs/PRD/PRD_Plector_v1.8.md) | 产品 | 产品需求文档 v1.8 |
| [specs/Design_Plector_v1.2.md](specs/Design_Plector_v1.2.md) | 技术 | 技术设计文档 |

#### C3. 开发标准（standards/）

| 文档 | 分类 | 说明 |
|------|------|------|
| [standards/Code_Standard_Plector.md](standards/Code_Standard_Plector.md) | 代码 | Python 代码规范 |
| [standards/Naming_Convention_Plector.md](standards/Naming_Convention_Plector.md) | 命名 | 文件/函数/类命名规范 |
| [standards/Skill_Development_Plector.md](standards/Skill_Development_Plector.md) | 技能 | 技能开发规范 |
| [standards/Technical_Spec_Plector.md](standards/Technical_Spec_Plector.md) | 技术 | 技术规格（JSON-RPC/MCP） |
| [standards/Behavior_Rules_Plector.md](standards/Behavior_Rules_Plector.md) | 行为 | ⭐ 强制行为约束（假设验证/熔断/变更记录） |
| [standards/Plan_Execution_Rules.md](standards/Plan_Execution_Rules.md) | 执行 | Plan.md 结构与执行日志规范 |
| [standards/Commit_Convention_Plector.md](standards/Commit_Convention_Plector.md) | 提交 | Git 提交规范与检查流程 |
| [standards/Frontend_Modification_Rules.md](standards/Frontend_Modification_Rules.md) | 前端 | 前端修改三步防退化流水线 |
| [standards/Language_Convention_Plector.md](standards/Language_Convention_Plector.md) | 语言 | 中英文使用规范与命名约定 |

#### C4. 用户指南（guides/）

| 文档 | 分类 | 说明 |
|------|------|------|
| [guides/Deployment_Guide.md](guides/Deployment_Guide.md) | 部署 | 环境要求、部署步骤、故障排查 |
| [guides/MCP_Server_Guide.md](guides/MCP_Server_Guide.md) | MCP | MCP Server 开发与注册 |
| [guides/Configuration_Reference.md](guides/Configuration_Reference.md) | 配置 | config.yaml 参考 |

#### C5. API 文档（api/）

| 文档 | 分类 | 说明 |
|------|------|------|
| [api/REST_API.md](api/REST_API.md) | REST | REST API 端点 |
| [api/WebSocket_API.md](api/WebSocket_API.md) | WS | WebSocket 实时通信 |

#### C6. 设计笔记（notes/）

| 文档 | 说明 |
|------|------|
| [notes/Plector_前端设计方案.md](notes/Plector_前端设计方案.md) | Vue3 前端架构 |
| [notes/Plector_LobeChat_集成方案.md](notes/Plector_LobeChat_集成方案.md) | Lobe Chat 集成 |
| [notes/Plector_WebSocket_适配代码.md](notes/Plector_WebSocket_适配代码.md) | WebSocket 适配 |

#### C7. 状态报告（reports/）

| 文档 | 说明 |
|------|------|
| [reports/Project_Status_Plector_20260404.md](reports/Project_Status_Plector_20260404.md) | 项目状态报告 |

#### C8. 其他文档

| 文档 | 说明 |
|------|------|
| [docs/PLECTOR_SKILLS.md](PLECTOR_SKILLS.md) | 技能清单 |
| [docs/SKILL_DESIGN_PRINCIPLES.md](SKILL_DESIGN_PRINCIPLES.md) | 技能设计原则 |

### D. 技能定义（skills/*/SKILL.md）

| 技能 | 路径 | 说明 |
|------|------|------|
| `memory` | [skills/memory/SKILL.md](../skills/memory/SKILL.md) | 记忆系统 |
| `context_refresher` | [skills/context_refresher/SKILL.md](../skills/context_refresher/SKILL.md) | 上下文保鲜 |
| `error_knowledge` | [skills/error_knowledge/SKILL.md](../skills/error_knowledge/SKILL.md) | 错误知识库 |
| `self_improver` | [skills/self_improver/SKILL.md](../skills/self_improver/SKILL.md) | 自我改进 |
| `code_writer` | [skills/code_writer/SKILL.md](../skills/code_writer/SKILL.md) | 代码编写 |
| `test_runner` | [skills/test_runner/SKILL.md](../skills/test_runner/SKILL.md) | 测试执行 |
| `health_monitor` | [skills/health_monitor/SKILL.md](../skills/health_monitor/SKILL.md) | 健康监控 |
| `file_utils` | [skills/file_utils/SKILL.md](../skills/file_utils/SKILL.md) | 文件操作 |
| `web_search` | [skills/web_search/SKILL.md](../skills/web_search/SKILL.md) | 网络搜索 |
| `agency_orchestrator` | [skills/agency_orchestrator/SKILL.md](../skills/agency_orchestrator/SKILL.md) | 工作流编排 |

### E. 公共规范（外部 Obsidian 仓库）

> 这些规范存放在 `E:/笔记/Claude Code规范/`，可跨项目通用。

| 规范 | 位置 |
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

---

## 一、任务-文档映射（按场景）

| 场景 | 层级 | 文档路径 |
|------|------|----------|
| **理解 AI 行为约束** | 基础 | CLAUDE.md（第 1-6 节）→ 本索引 |
| **理解决策树** | 基础 | SOUL.md → 决策树章节 |
| **规划复杂任务** | 基础 | PLAN_TEMPLATE.md → 模板 |
| **开发新功能** | 开发 | CLAUDE.md → PRD → Design → Code Std → Naming |
| **修复 Bug** | 修复 | CLAUDE.md 第 1-3 节 → Design → Code Std |
| **开发新技能** | 技能 | CLAUDE.md → PLECTOR_SKILLS → SKILL_DESIGN_PRINCIPLES → Skill Dev |
| **修改前端** | 前端 | CLAUDE.md 第 3 节 → 前端设计方案 |
| **开发 API** | API | Tech Spec → REST_API/WebSocket_API |
| **部署系统** | 运维 | Deployment_Guide → Configuration_Reference |
| **贡献代码** | 开源 | CONTRIBUTING.md → Code Std → Naming → Commit |

---

## 二、文档依赖关系图

```
                    ┌─────────────────────────────────────────┐
                    │            CLAUDE.md (⭐AI必读)         │
                    │     行为约束 / 熔断 / 假设验证          │
                    └──────────────────┬──────────────────────┘
                                       │
                   ┌───────────────────┼───────────────────┐
                   │                   │                   │
                   ▼                   ▼                   ▼
           ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
           │   SOUL.md   │     │   PRD      │     │   BRD      │
           │  (元认知)   │     │ (产品需求)  │     │ (商业需求) │
           └──────┬──────┘     └──────┬──────┘     └─────────────┘
                  │                   │
                  └─────────┬─────────┘
                            ▼
                    ┌─────────────┐
                    │   Design    │
                    │  (技术设计) │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ Tech Spec   │ │ Skill Dev   │ │ Code Std    │
    │ (技术规格)   │ │ (技能开发)  │ │ (代码规范)  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┴───────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Naming Conv    │
                   │  (命名规范)     │
                   └─────────────────┘
```

---

## 三、文档阅读路径

### 3.1 新功能开发路径

```
1. [CLAUDE.md] → 行为约束（假设验证、熔断、变更记录）
       ↓
2. [SOUL.md] → 理解决策树和技能联动
       ↓
3. [specs/PRD/PRD_Plector_v1.8.md] → 理解功能范围和验收标准
       ↓
4. [specs/Design_Plector_v1.2.md] → 理解架构设计和模块关系
       ↓
5. [standards/Technical_Spec_Plector.md] → 理解接口规范（JSON-RPC/MCP）
       ↓
6. [standards/Code_Standard_Plector.md] → 遵循代码规范
       ↓
7. [standards/Naming_Convention_Plector.md] → 遵循命名规范
       ↓
8. [skills/*/SKILL.md] → 参考现有技能实现模式（如需新技能）
       ↓
9. [PLECTOR_SKILLS.md] → 运行验证命令
       ↓
10. 创建/更新 Plan.md → 记录执行过程
```

### 3.2 Bug 修复路径

```
1. [CLAUDE.md 第 1-3 节] → 假设验证 + 熔断机制
       ↓
2. [SOUL.md 出错处理流程] → 2次熔断规则
       ↓
3. [specs/Design_Plector_v1.2.md] → 理解设计意图
       ↓
4. [standards/Code_Standard_Plector.md] → 理解代码规范
       ↓
5. [skills/test_runner/SKILL.md] → 运行测试
       ↓
6. [rules check] → ruff check core/ skills/ channels/
```

### 3.3 技能开发路径

```
1. [CLAUDE.md] → 行为规范
       ↓
2. [PLECTOR_SKILLS.md] → 理解技能体系（11个核心技能）
       ↓
3. [SKILL_DESIGN_PRINCIPLES.md] → 设计原则（分层、治理、触发词）
       ↓
4. [standards/Skill_Development_Plector.md] → 开发规范（skill.json/SKILL.md）
       ↓
5. [skills/memory/SKILL.md] → 参考技能示例
       ↓
6. [skills/agency_orchestrator/SKILL.md] → 参考复杂技能模式
       ↓
7. 运行验证 → python scripts/validate_skills.py
```

### 3.4 前端修改路径

```
1. [CLAUDE.md 第 3 节] → 前端修改规范（三步防退化流水线）
       ↓
2. [SOUL.md 第 5 节] → 决策流程
       ↓
3. [notes/Plector_前端设计方案.md] → 前端架构（Vue3/TypeScript）
       ↓
4. [notes/Plector_WebSocket_适配代码.md] → 通信层
       ↓
5. [standards/Code_Standard_Plector.md] → CSS 规范
       ↓
6. 验证 → chrome-devtools MCP 截图对比
```

### 3.5 API 开发路径

```
1. [standards/Technical_Spec_Plector.md] → 技术规格（JSON-RPC 2.0/MCP）
       ↓
2. [api/REST_API.md] → REST 端点（/api/health, /api/conversations）
       ↓
3. [api/WebSocket_API.md] → WebSocket 协议
       ↓
4. [guides/MCP_Server_Guide.md] → MCP Server 开发
       ↓
5. [specs/Design_Plector_v1.2.md] → 接口设计背景
```

### 3.6 部署运维路径

```
1. [guides/Deployment_Guide.md] → 环境要求、部署步骤
       ↓
2. [guides/Configuration_Reference.md] → config.yaml 参考
       ↓
3. [api/REST_API.md] → 健康检查端点
       ↓
4. [SECURITY.md] → 安全配置
       ↓
5. [reports/Project_Status_Plector_20260404.md] → 项目状态
```

---

## 四、快速查找表

| 遇到问题 | 查哪里 |
|----------|--------|
| 不确定任务复杂度 | SOUL.md → 决策树 |
| 修改现有代码 | CLAUDE.md → 三步防退化流水线 |
| 创建新技能 | SKILL_DESIGN_PRINCIPLES.md |
| 不知道用什么命名 | Naming_Convention_Plector.md |
| 不知道接口格式 | Technical_Spec_Plector.md |
| 需要运行测试 | test_runner/SKILL.md |
| 不知道有哪些技能 | PLECTOR_SKILLS.md |
| 想了解项目架构 | Design_Plector_v1.2.md |
| 想了解功能范围 | PRD_Plector_v1.8.md |
| 想了解商业目标 | BRD_Plector_v2.2.md |
| 如何贡献代码 | CONTRIBUTING.md |
| 发现安全漏洞 | SECURITY.md |
| 查看版本历史 | CHANGELOG.md |
| 配置 MCP Server | MCP_Server_Guide.md |
| 前端 UI 修改 | notes/Plector_前端设计方案.md |

---

## 五、交叉引用标记

| 标记 | 指向 | 示例 |
|------|------|------|
| `[规范:代码标准]` | Code_Standard_Plector.md | 用于编码时参考 |
| `[规范:命名]` | Naming_Convention_Plector.md | 用于命名检查 |
| `[规范:技能]` | Skill_Development_Plector.md | 用于技能开发 |
| `[规格:PRD]` | PRD_Plector_v1.8.md | 用于需求理解 |
| `[规格:BRD]` | BRD_Plector_v2.2.md | 用于商业目标 |
| `[规格:设计]` | Design_Plector_v1.2.md | 用于架构理解 |
| `[指南:部署]` | Deployment_Guide.md | 用于部署操作 |
| `[指南:MCP]` | MCP_Server_Guide.md | 用于 MCP 开发 |
| `[API:REST]` | REST_API.md | 用于 API 集成 |
| `[技能:xxx]` | skills/xxx/SKILL.md | 用于技能参考 |
| `[模板:Plan]` | PLAN_TEMPLATE.md | 用于任务计划 |

---

## 六、版本历史

- v1.2.0 (2026-04-28)：完整索引重构，新增分类体系（A-E）、层级关系、关联标注
- v1.1.0 (2026-04-28)：新增开源必备文档索引
- v1.0.0 (2026-04-28)：初始版本，定义文档索引导航系统
