# Plector 开发规范

> Claude Code 会话启动时自动读取。
> 版本：v8.0.0 | 最后更新：2026-04-28

---

## 双索引架构

> **工具规范与项目规范分离**

| 索引 | 说明 | 位置 |
|------|------|------|
| **Claude Code 工具规范** | 跨项目通用规范 | [E:/笔记/Claude Code规范/DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) |
| **Plector 项目文档** | 项目专用文档 | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |

---

## Claude Code 工具规范

> ⚠️ 这些是通用规范，存放在 `E:/笔记/Claude Code规范/`，由 Git 统一维护。

| 规范 | 说明 | 位置 |
|------|------|------|
| 行为规则 | 假设验证、错误熔断、变更记录、主动升级 | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → Agent_Behavior_Rules.md |
| Plan 模板 | 任务计划格式、执行日志 | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → PLAN_Template.md |
| 前端规范 | 考古学家+外科医生模式 | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → Frontend_Modification_Rules.md |
| 提交规范 | feat/fix/docs 等 type | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → Commit_Convention.md |
| 代码规范 | Python 命名、导入、函数设计 | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → Coding_Convention.md |
| 语言约定 | 中文对话/英文代码 | [DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) → Language_Convention.md |

完整索引：[E:/笔记/Claude Code规范/DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md)

---

## Plector 项目特有规范

### 技能系统（10个技能）

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

### 项目结构

```
plector/
├── core/           # 核心引擎
├── skills/         # 技能（≤15个，定义在 skill.json）
├── tools/          # 工具函数
├── channels/       # 通信渠道
├── config/         # 配置文件
├── docs/           # 文档
│   ├── standards/  # 项目特有规范
│   ├── specs/     # 规格文档
│   ├── guides/    # 用户指南
│   └── api/       # API 文档
├── tests/          # 单元测试
└── scripts/        # 工具脚本
```

### 技术规格（Plector 特有）

| 规格 | 说明 | 位置 |
|------|------|------|
| JSON-RPC/MCP 协议 | 技术规格 | [docs/standards/Technical_Spec_Plector.md](docs/standards/Technical_Spec_Plector.md) |
| 技能开发规范 | Plector tier 系统 | [docs/standards/Skill_Development_Plector.md](docs/standards/Skill_Development_Plector.md) |
| 闭环引擎 | 任务执行引擎 | [SOUL.md](SOUL.md) |

---

## 文档索引

| 内容 | 位置 |
|------|------|
| **Claude Code 工具规范索引** | [E:/笔记/Claude Code规范/DOCS_INDEX.md](file:///E:/笔记/Claude Code规范/DOCS_INDEX.md) |
| **Plector 项目文档索引** | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |
| **Plector 灵魂** | [SOUL.md](SOUL.md) |
| **Plan 模板** | [PLAN_TEMPLATE.md](PLAN_TEMPLATE.md) |

---

## 版本历史

- `v8.0.0` (2026-04-28)：明确双索引架构；Claude Code 规范与 Plector 规范完全分离；各引用其对应的 DOCS_INDEX.md
- `v7.0.0`：重构为纯索引模式
- `v6.0.0`：索引模式重构

---

*核心原则：工具是工具，项目是项目。Claude Code 工具规范在 `E:/笔记/Claude Code规范/`，Plector 项目规范在 `docs/`*
