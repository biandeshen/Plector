# Claude Code 工具速查

> Claude Code 内置工具、MCP、Skill 在 Plector 项目中的用法。

---

## 内置工具

| 工具 | 典型用法 |
|------|----------|
| `Bash` | `git log`、`pytest`、`ruff check` |
| `Read` | 读取文件完整内容 |
| `Edit` | 精确替换代码（最小变更） |
| `Write` | 创建新文件 |
| `Grep` / `Glob` | 搜索引用、找文件 |
| `Task*` | 复杂任务分解跟踪 |
| `SendMessage` | 输出假设、请求确认 |

---

## MCP 工具

| 工具 | 典型用法 |
|------|----------|
| `chrome-devtools` | 前端截图对比 |
| `code-reasoning` | 复杂逻辑分析 |
| `fetch` | 查文档 |

---

## Claude Code Skill

| 技能 | 典型用法 |
|------|----------|
| `memory` | 保存/检索开发经验 |
| `error_knowledge` | 记录分类错误 |
| `self_improver` | 连续失败时自动修复 |
| `agency_orchestrator` | 复杂任务多角色编排 |
| `test_runner` | 运行测试 |
| `context_refresher` | 长对话保鲜目标 |
