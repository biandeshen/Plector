# Plector 开发规范

> Claude Code 会话启动时自动读取。版本 `v2.5.0`

---

## 🛑 强制行为约束（优先级最高）

### 1. 假设验证优先
- 修改代码前，**必须**在对话中输出：`[假设] 我认为 [描述]，因为 [依据]`
- 同时用 `Write`/`Edit` 将假设写入 `Plan.md`
- 若假设被否定，**立即停止**，禁止原路径修补

### 2. 错误即停（2 次熔断）
**"同一操作"判定**（满足任一即视为同一）：
1. 相同工具 + 相同参数
2. 同文件同区块 + 相同性质修改
3. 同目标 + 本质相同方案

| 失败次数 | 动作 | 使用的工具 |
|----------|------|------------|
| **1次** | 记录错误到 `Plan.md`，输出分析报告 | `Edit` 写日志，`Skill: error_knowledge` |
| **2次** | **立即停止**，请求人工介入 | `SendMessage` 求助 |

> 例外：外部环境变化导致失败，不计入连续次数。

### 3. 变更即记录
- 每次修改后，用 `Edit` 在 `Plan.md` 追加：`HH:MM | [动作] | [结果] | [下一步]`
- 5 分钟无日志更新，用 `SendMessage` 主动询问用户

### 4. 主动升级（可不等失败）
用 `Bash: git log -p` 检查历史，若发现以下情况，立即暂停请求确认：
- 提交含 `!important`/`hack`/`fix`
- 影响超过 3 个组件（用 `Grep` 检查引用）
- 不可逆操作（数据库迁移、文件删除）

### 禁止（硬性拦截）
- ❌ 假设未验证就 `Edit`/`Write`
- ❌ 同一方案连续尝试 ≥3 次
- ❌ 忽略 `Bash: pytest` / `ruff` 错误继续执行
- ❌ 未更新 `Plan.md` 连续修改多个文件
- ❌ 未确认需求就写代码

---

## 语言约定
中文（对话、文档、代码注释）；英文（对外 API、技术术语）

---

## 🔒 前端/UI 修改规范

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
- `Bash: pytest` 或 `Skill: test_runner`
- 前端可用 `chrome-devtools` MCP 截图对比
- 不确定时输出：`⚠️ 高风险修改：请人工复核视觉`

---

## 🧰 Claude Code 工具速查（本项目用法）

| 工具类型 | 工具名 | 典型用法 |
|----------|--------|----------|
| 内置 | `Bash` | `git log`、`pytest`、`ruff` |
| 内置 | `Read` / `Edit` / `Write` | 读写代码 |
| 内置 | `Grep` / `Glob` | 搜索引用、找文件 |
| 内置 | `Task*` | 复杂任务分解跟踪 |
| 内置 | `SendMessage` | 输出假设、请求确认 |
| MCP | `chrome-devtools` | 前端截图对比 |
| MCP | `code-reasoning` | 复杂逻辑分析 |
| MCP | `fetch` | 查文档 |
| Skill | `memory` | 保存/检索开发经验 |
| Skill | `error_knowledge` | 记录分类错误 |
| Skill | `self_improver` | 连续失败时自动修复 |
| Skill | `agency_orchestrator` | 复杂任务多角色编排 |
| Skill | `test_runner` | 运行测试 |
| Skill | `context_refresher` | 长对话保鲜目标 |

---

## Plan.md 强制机制
复杂任务用 `Write` 创建 `Plan.md`，模板见 `PLAN_TEMPLATE.md`。
每步执行后用 `Edit` 追加日志。

---

## 提交规范
`<type>(<scope>): <subject>` — feat/fix/docs/refactor/test/chore

推送前执行：
```bash
ruff check core/ skills/ channels/
python scripts/validate_skills.py
```

---

## 快速索引

| 内容 | 位置 |
|------|------|
| Claude Code 工具速查 | `CLAUDE_CODE_TOOLS.md` |
| Plector 技能清单 | `docs/PLECTOR_SKILLS.md` |
| 代码规范 | `docs/standards/Code_Standard_Plector.md` |
| 命名规范 | `docs/standards/Naming_Convention_Plector.md` |
| 技能开发 | `docs/standards/Skill_Development_Plector.md` |
| MCP Server | `docs/guides/MCP_Server_Guide.md` |
| 设计文档 | `docs/specs/Design_Plector_v1.2.md` |

---

**版本历史**：
- `v2.5.0`：融入 Claude Code 实际可用工具链，规则与工具映射清晰可执行。
- `v2.4.0`：精简文档，保留核心强制规则。
