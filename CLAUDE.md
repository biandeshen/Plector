# Plector 开发规范

> Claude Code 会话启动时自动读取。
> 版本：v6.1.0 | 最后更新：2026-04-28

> **规范版本信息**
> - 公共规范来源：`E:/笔记/Claude Code规范/`（跨项目通用）
> - 公共规范版本：v1.0.0 | 检查日期：2026-04-28
> - 项目规范：Plector 特有规范（见下方章节）

---

## 一、Plector 核心行为约束

> ⚠️ 通用规范见 [E:/笔记/Claude Code规范/Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md)
> 详见 [docs/standards/Behavior_Rules_Plector.md](docs/standards/Behavior_Rules_Plector.md)

### 假设验证优先
- 修改代码前，**必须**在对话中输出：`[假设] 我认为 [描述]，因为 [依据]`
- 同时用 `Edit` 将假设写入 `Plan.md`
- 若假设被否定，**立即停止**，禁止原路径修补

### 错误熔断（2次）
- 同一操作失败 1 次：记录错误到 Plan.md，输出分析报告
- 同一操作失败 2 次：**立即停止**，请求人工介入
- 禁止对同一问题连续尝试超过 2 次未经调整的相同方案

### 变更即记录
- 每次修改后，在 Plan.md 追加：`HH:MM | [动作] | [结果] | [下一步]`
- 5 分钟无日志更新，主动询问用户

### 主动升级（可不等失败）
- 提交含 `!important`/`hack`/`fix` → 立即暂停
- 影响超过 3 个组件 → 立即暂停
- 不可逆操作（数据库迁移、文件删除）→ 立即暂停

---

## 二、Plector 技能系统（项目特有）

> 详见 [docs/PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md)

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `memory` | 保存/检索开发经验 | "记住"、"回忆"、"偏好" |
| `context_refresher` | 长对话保鲜目标 | "继续"、"有任何进展" |
| `error_knowledge` | 记录分类错误 | "报错"、"出错了" |
| `self_improver` | 连续失败时自动修复 | "自我改进"、"自动优化" |
| `agency_orchestrator` | 复杂任务多角色编排 | 复杂任务 |
| `test_runner` | 运行测试 | "测试"、"跑测试" |
| `health_monitor` | 系统健康检查 | "系统健康"、"CPU"、"内存" |
| `web_search` | 网络搜索 | "搜索"、"网上找" |
| `file_utils` | 文件操作 | "列出"、"查看文件" |
| `code_writer` | 代码编写 | "写代码"、"修改代码" |

---

## 三、Plan.md 强制机制

> ⚠️ 通用任务管理规范见 [E:/笔记/Claude Code规范/PLAN_Template.md](file:///E:/笔记/Claude Code规范/PLAN_Template.md)
> 详见 [docs/standards/Plan_Execution_Rules.md](docs/standards/Plan_Execution_Rules.md)

复杂任务用 `Write` 创建 `Plan.md`，每步执行后用 `Edit` 追加日志。

模板见 [PLAN_TEMPLATE.md](PLAN_TEMPLATE.md)

---

## 四、前端/UI 修改规范

> ⚠️ 通用前端规范见 [E:/笔记/Claude Code规范/Frontend_Modification_Rules.md](file:///E:/笔记/Claude Code规范/Frontend_Modification_Rules.md)
> 详见 [docs/standards/Frontend_Modification_Rules.md](docs/standards/Frontend_Modification_Rules.md)

**三步防退化流水线**：
1. 影响面分析（git log -p）
2. 最小变更策略（精准切除，不伤害健康组织）
3. 视觉回归自检

**考古学家 + 外科医生模式**：
- ❌ 推土机模式：直接重写，忽略历史
- ✅ 考古学家模式：先理解"为什么这里要这样写"
- ✅ 外科医生模式：精准切除病变组织

---

## 五、提交规范

> ⚠️ 通用提交规范见 [E:/笔记/Claude Code规范/Commit_Convention.md](file:///E:/笔记/Claude Code规范/Commit_Convention.md)
> 详见 [docs/standards/Commit_Convention_Plector.md](docs/standards/Commit_Convention_Plector.md)

格式：`<type>(<scope>): <subject>`

类型：feat/fix/docs/refactor/test/chore

推送前执行：
```bash
ruff check core/ skills/ channels/
python scripts/validate_skills.py
```

---

## 六、语言约定

> ⚠️ 通用语言约定见 [E:/笔记/Claude Code规范/Language_Convention.md](file:///E:/笔记/Claude Code规范/Language_Convention.md)
> 详见 [docs/standards/Language_Convention_Plector.md](docs/standards/Language_Convention_Plector.md)

- 中文（对话、文档、代码注释）
- 英文（对外 API、技术术语、函数名、变量名）

---

## 七、快速索引

### 索引分类速查

| 分类 | 说明 | 入口 |
|------|------|------|
| **A. 根目录核心** | AI 必读的行为规范 | CLAUDE.md、SOUL.md、PLAN_TEMPLATE.md |
| **B. 开源必备** | LICENSE/CONTRIBUTING/SECURITY | 根目录 |
| **C1. 文档导航** | 本系统入口 | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |
| **C2. 规格文档** | BRD/PRD/设计 | [docs/specs/](docs/specs/) |
| **C3. 开发标准** | 代码/命名/技能规范 | [docs/standards/](docs/standards/) |
| **C4. 用户指南** | 部署/MCP/配置 | [docs/guides/](docs/guides/) |
| **C5. API 文档** | REST/WebSocket | [docs/api/](docs/api/) |
| **D. 技能定义** | 10 个技能的 SKILL.md | [skills/*/SKILL.md](skills/) |

### 快速入口（按任务）

| 任务 | 入口 |
|------|------|
| 新功能开发 | [docs/DOCS_INDEX.md → 新功能开发路径](docs/DOCS_INDEX.md#新功能开发路径) |
| Bug 修复 | [docs/DOCS_INDEX.md → Bug修复路径](docs/DOCS_INDEX.md#bug修复路径) |
| 技能开发 | [docs/DOCS_INDEX.md → 技能开发路径](docs/DOCS_INDEX.md#技能开发路径) |
| 前端修改 | [docs/DOCS_INDEX.md → 前端修改路径](docs/DOCS_INDEX.md#前端修改路径) |
| API 开发 | [docs/DOCS_INDEX.md → API开发路径](docs/DOCS_INDEX.md#api开发路径) |
| 部署运维 | [docs/DOCS_INDEX.md → 部署运维路径](docs/DOCS_INDEX.md#部署运维路径) |

### 规范文档（详情外置）

| 章节 | 主题 | 项目文档 | 公共规范 |
|------|------|----------|----------|
| 第一章 | 强制行为约束 | [Behavior_Rules_Plector.md](docs/standards/Behavior_Rules_Plector.md) | [Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md) |
| 第二章 | Plector 技能系统 | [PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md) | - |
| 第三章 | 前端修改规范 | [Frontend_Modification_Rules.md](docs/standards/Frontend_Modification_Rules.md) | [Frontend_Modification_Rules.md](file:///E:/笔记/Claude Code规范/Frontend_Modification_Rules.md) |
| 第四章 | Plan.md 机制 | [Plan_Execution_Rules.md](docs/standards/Plan_Execution_Rules.md) | [PLAN_Template.md](file:///E:/笔记/Claude Code规范/PLAN_Template.md) |
| 第五章 | 提交规范 | [Commit_Convention_Plector.md](docs/standards/Commit_Convention_Plector.md) | [Commit_Convention.md](file:///E:/笔记/Claude Code规范/Commit_Convention.md) |
| 第六章 | 语言约定 | [Language_Convention_Plector.md](docs/standards/Language_Convention_Plector.md) | [Language_Convention.md](file:///E:/笔记/Claude Code规范/Language_Convention.md) |

### 常用文档直接访问

| 内容 | 位置 |
|------|------|
| 完整文档索引 | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |
| Plector 灵魂 | [SOUL.md](SOUL.md) |
| 技能总览与治理 | [docs/PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md) |
| 技能设计原则 | [docs/SKILL_DESIGN_PRINCIPLES.md](docs/SKILL_DESIGN_PRINCIPLES.md) |
| 代码规范 | [docs/standards/Code_Standard_Plector.md](docs/standards/Code_Standard_Plector.md) |
| 命名规范 | [docs/standards/Naming_Convention_Plector.md](docs/standards/Naming_Convention_Plector.md) |
| 技术规格 | [docs/standards/Technical_Spec_Plector.md](docs/standards/Technical_Spec_Plector.md) |
| 技术设计 | [docs/specs/Design_Plector_v1.2.md](docs/specs/Design_Plector_v1.2.md) |
| 部署指南 | [docs/guides/Deployment_Guide.md](docs/guides/Deployment_Guide.md) |
| REST API | [docs/api/REST_API.md](docs/api/REST_API.md) |
| WebSocket API | [docs/api/WebSocket_API.md](docs/api/WebSocket_API.md) |
| 贡献指南 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 安全策略 | [SECURITY.md](SECURITY.md) |

### 公共规范（跨项目通用）

> ⚠️ 这些规范来自 `E:/笔记/Claude Code规范/`，跨项目通用

| 规范 | 位置 | 版本 |
|------|------|------|
| Agent 行为规则 | [Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md) | v1.0.0 |
| 代码规范 | [Coding_Convention.md](file:///E:/笔记/Claude Code规范/Coding_Convention.md) | v1.0.0 |
| 命名规范 | [Naming_Convention.md](file:///E:/笔记/Claude Code规范/Naming_Convention.md) | v1.0.0 |
| 提交规范 | [Commit_Convention.md](file:///E:/笔记/Claude Code规范/Commit_Convention.md) | v1.0.0 |
| 语言约定 | [Language_Convention.md](file:///E:/笔记/Claude Code规范/Language_Convention.md) | v1.0.0 |
| 前端修改规范 | [Frontend_Modification_Rules.md](file:///E:/笔记/Claude Code规范/Frontend_Modification_Rules.md) | v1.0.0 |
| 任务计划模板 | [PLAN_Template.md](file:///E:/笔记/Claude Code规范/PLAN_Template.md) | v1.0.0 |
| 技能开发规范 | [Skill_Development_Convention.md](file:///E:/笔记/Claude Code规范/Skill_Development_Convention.md) | v1.0.0 |
| 密钥管理 | [Secrets_Management.md](file:///E:/笔记/Claude Code规范/Secrets_Management.md) | v1.0.0 |

---

## 八、工具分类

| 类型 | 文档 |
|------|------|
| Claude Code 工具使用 | [CLAUDE_CODE_TOOLS.md](CLAUDE_CODE_TOOLS.md) |
| Plector 技能系统 | [docs/PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md) |

---

**版本历史**：
- `v6.1.0` (2026-04-28)：新增规范版本信息和来源标记；明确项目规范与公共规范的对应关系；添加公共规范快速索引表
- `v6.0.0` (2026-04-28)：重构为索引模式，规范详情外置到 docs/standards/；明确工具规范(Plector技能)与项目规范(Plector开发流程)的职责边界
