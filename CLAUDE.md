# Plector 开发规范

> Claude Code 会话启动时自动读取。
> 版本：v7.0.0 | 最后更新：2026-04-28

---

## 通用规范（来源：E:/笔记/）

> ⚠️ 以下规范存放在 `E:/笔记/Claude Code规范/`，由 Git 统一维护。
> 版本检查：`cd E:/笔记/ && git log -1 --format="%h %s"`

| 规范 | 内容 | 位置 |
|------|------|------|
| 行为规则 | 假设验证、错误熔断、变更记录、主动升级 | [Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md) |
| Plan 模板 | 任务计划格式、执行日志 | [PLAN_Template.md](file:///E:/笔记/Claude Code规范/PLAN_Template.md) |
| 前端规范 | 考古学家+外科医生模式、三步防退化 | [Frontend_Modification_Rules.md](file:///E:/笔记/Claude Code规范/Frontend_Modification_Rules.md) |
| 提交规范 | feat/fix/docs 等 type 定义 | [Commit_Convention.md](file:///E:/笔记/Claude Code规范/Commit_Convention.md) |
| 语言约定 | 中文对话/英文代码标识符 | [Language_Convention.md](file:///E:/笔记/Claude Code规范/Language_Convention.md) |
| 代码规范 | Python 命名、导入、函数设计 | [Coding_Convention.md](file:///E:/笔记/Claude Code规范/Coding_Convention.md) |
| 技能开发 | 技能开发流程、SKILL.md 格式 | [Skill_Development_Convention.md](file:///E:/笔记/Claude Code规范/Skill_Development_Convention.md) |

---

## Plector 特有规范

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
├── core/           # 核心引擎（agent_loop, skill_registry 等）
├── skills/         # 技能（≤15 个，定义在 skill.json）
├── tools/          # 工具函数（无限制）
├── channels/       # 通信渠道（CLI, WebSocket）
├── config/         # 配置文件（YAML）
├── docs/           # 文档
│   ├── standards/  # 项目特有规范
│   ├── specs/     # 规格文档（BRD/PRD/设计）
│   ├── guides/    # 用户指南
│   └── api/       # API 文档
├── tests/          # 单元测试
└── scripts/        # 工具脚本
```

---

## 文档索引

| 内容 | 位置 |
|------|------|
| **完整文档索引** | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |
| **Plector 灵魂** | [SOUL.md](SOUL.md) |
| **Plan 模板** | [PLAN_TEMPLATE.md](PLAN_TEMPLATE.md) |
| **同步机制** | [docs/SYNCHRONIZATION_MECHANISM.md](docs/SYNCHRONIZATION_MECHANISM.md) |
| **工具使用指南** | [CLAUDE_CODE_TOOLS.md](CLAUDE_CODE_TOOLS.md) |

---

## 版本历史

- `v7.0.0` (2026-04-28)：移除通用规范内容，改为直接引用 E:/笔记/Claude Code规范/；仅保留 Plector 特有内容（技能系统、项目结构、文档索引）
- `v6.1.0`：添加规范版本信息和来源标记
- `v6.0.0`：重构为索引模式
