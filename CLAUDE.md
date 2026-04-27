# Plector 开发规范

> Claude Code 会话启动时自动读取。版本 `v5.0.0`

---

## 一、【项目规范】Plector 强制行为约束

> 以下规范仅适用于 Plector 项目。

### 🛑 1. 假设验证优先
- 修改代码前，**必须**在对话中输出：`[假设] 我认为 [描述]，因为 [依据]`
- 同时用 `Write`/`Edit` 将假设写入 `Plan.md`
- 若假设被否定，**立即停止**，禁止原路径修补

### 🛑 2. 错误即停（2 次熔断）

**"同一操作"判定**（满足任一即视为同一）：
1. 相同工具 + 相同参数
2. 同文件同区块 + 相同性质修改
3. 同目标 + 本质相同方案

| 失败次数 | 动作 | 使用的工具 |
|----------|------|------------|
| **1次** | 记录错误到 `Plan.md`，输出分析报告 | `Edit` 写日志 |
| **2次** | **立即停止**，请求人工介入 | `SendMessage` 求助 |

> 例外：外部环境变化导致失败，不计入连续次数。

### 🛑 3. 变更即记录
- 每次修改后，用 `Edit` 在 `Plan.md` 追加：`HH:MM | [动作] | [结果] | [下一步]`
- 5 分钟无日志更新，用 `SendMessage` 主动询问用户

### 🛑 4. 主动升级（可不等失败）
用 `Bash: git log -p` 检查历史，若发现以下情况，立即暂停请求确认：
- 提交含 `!important`/`hack`/`fix`
- 影响超过 3 个组件（用 `Grep` 检查引用）
- 不可逆操作（数据库迁移、文件删除）

### 🛑 禁止（硬性拦截）
- ❌ 假设未验证就 `Edit`/`Write`
- ❌ 同一方案连续尝试 ≥3 次
- ❌ 忽略 `Bash: pytest` / `ruff` 错误继续执行
- ❌ 未更新 `Plan.md` 连续修改多个文件
- ❌ 未确认需求就写代码

---

## 二、【项目规范】Plector 技能

> 这些是 Plector 项目开发的技能，不是 Claude Code 的 Skill。

| 技能 | 典型用法 | 说明 |
|------|----------|------|
| `memory` | 保存/检索开发经验 | 记忆系统 |
| `context_refresher` | 长对话保鲜目标 | 上下文保鲜 |
| `error_knowledge` | 记录分类错误 | 错误知识库 |
| `self_improver` | 连续失败时自动修复 | 自我改进 |
| `agency_orchestrator` | 复杂任务多角色编排 | 工作流引擎 |
| `test_runner` | 运行测试 | 测试执行 |

---

## 三、【项目规范】前端/UI 修改规范

**修改前必做**：
1. `Read` 文件完整内容
2. `Bash: git log -p -3 -- <file>` 分析历史

| 场景 | 策略 | 工具 |
|------|------|------|
| 修改样式 | 只改 CSS，不动 HTML/JS | `Edit` |
| 添加功能 | 追加不改原有 | `Edit` |
| 修复 bug | 只改问题行 | `Edit` |
| 修改 Vue 组件 | 先列 props/emits/computed | `Read` + `Grep` |
| 重写页面 | **需用户明确授权** | `Write` |

**修改后验证**：
- `Bash: pytest` 或 `Bash: python scripts/validate_skills.py`
- 前端可用 `chrome-devtools` MCP 截图对比

---

## 四、【项目规范】Plan.md 强制机制

复杂任务用 `Write` 创建 `Plan.md`，模板见 `PLAN_TEMPLATE.md`。
每步执行后用 `Edit` 追加日志。

---

## 五、【项目规范】提交规范

`<type>(<scope>): <subject>` — feat/fix/docs/refactor/test/chore

推送前执行：
```bash
ruff check core/ skills/ channels/
python scripts/validate_skills.py
```

---

## 六、【项目规范】语言约定

中文（对话、文档、代码注释）；英文（对外 API、技术术语）

---

## 七、快速索引

> **完整索引**：[docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) ⭐ 包含所有公共规范和项目专属文档的完整索引

### 核心规范（必读）

| 内容 | 位置 |
|------|------|
| **文档索引导航** | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) ⭐ 任务-文档映射表 |
| Plector 技能文档 | [docs/PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md) |
| Plector 代码规范 | [docs/standards/Code_Standard_Plector.md](docs/standards/Code_Standard_Plector.md) |
| Plector 命名规范 | [docs/standards/Naming_Convention_Plector.md](docs/standards/Naming_Convention_Plector.md) |
| Plector 技能开发 | [docs/standards/Skill_Development_Plector.md](docs/standards/Skill_Development_Plector.md) |
| 设计文档 | [docs/specs/Design_Plector_v1.2.md](docs/specs/Design_Plector_v1.2.md) |

### 快速入口（按任务）

| 任务 | 入口文档 |
|------|----------|
| 新功能开发 | [docs/DOCS_INDEX.md → 新功能开发路径](docs/DOCS_INDEX.md#新功能开发路径) |
| Bug 修复 | [docs/DOCS_INDEX.md → Bug修复路径](docs/DOCS_INDEX.md#bug修复路径) |
| 技能开发 | [docs/DOCS_INDEX.md → 技能开发路径](docs/DOCS_INDEX.md#技能开发路径) |
| 前端修改 | [docs/DOCS_INDEX.md → 前端修改路径](docs/DOCS_INDEX.md#前端修改路径) |
| API 开发 | [docs/DOCS_INDEX.md → API开发路径](docs/DOCS_INDEX.md#api开发路径) |

> 💡 **提示**：遇到不确定该读哪个文档时，先查阅 [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) 的任务-文档映射表。

---

**版本历史**：
- `v4.3.0`：新增前端设计方案、Lobe Chat 集成方案、WebSocket 适配代码三个笔记文档。
- `v4.2.0`：同步 Plector 开发流程文档到 Obsidian，新增命名/技能/密钥规范。
- `v4.1.0`：公共规范统一迁移到 Obsidian 笔记仓库，新增 CLAUDE/SOUL/PLAN 模板。
- `v4.0.0`：快速索引分为公共规范（Obsidian 笔记仓库）和项目专属（Plector）两部分。
- `v3.0.0`：明确区分公共规范与项目专属规范。
- `v2.0.0`：CLAUDE.md 精简为行为约束层，详细索引外链到 DOCS_INDEX.md
