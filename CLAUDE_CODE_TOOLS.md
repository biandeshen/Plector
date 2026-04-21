# Claude Code 工具速查

> Claude Code 内置工具、MCP、Skill 在 Plector 项目中的用法。
> 版本：v1.0.0 | 最后更新：2026-04-20

---

## 内置工具

| 工具 | 典型用法 | 说明 |
|------|----------|------|
| `Bash` | `git log`、`pytest`、`ruff check` | 执行命令，与 Git/测试/代码检查交互 |
| `Read` | 读取文件完整内容 | 获取代码或文档内容 |
| `Edit` | 精确替换代码（最小变更） | 精确修改，保留上下文 |
| `Write` | 创建新文件 | 用于新建文件或重写 |
| `Grep` / `Glob` | 搜索引用、找文件 | 搜索代码或定位文件 |
| `Task*` | 复杂任务分解跟踪 | 分解大任务，跟踪子任务 |
| `SendMessage` | 输出假设、请求确认 | 向用户提问或报告状态 |

### 常用 Bash 命令

```bash
# Git 操作
git log -p -3 -- <file>  # 查看文件历史
git status                # 查看变更
git diff                  # 查看差异

# 代码验证
python -m py_compile <file>.py    # 语法检查
pytest tests/ -v                  # 单元测试
ruff check core/ skills/ channels/ # 代码格式

# 项目命令
python channels/cli.py --query "你好"  # CLI 测试
python channels/websocket.py --port 8080  # Web 服务
```

---

## MCP 工具

| 工具 | 典型用法 | 说明 |
|------|----------|------|
| `chrome-devtools` | 前端截图对比 | 前端修改后验证视觉 |
| `code-reasoning` | 复杂逻辑分析 | 需要深度思考的逻辑问题 |
| `fetch` | 查文档 | 获取外部文档内容 |

---

## Claude Code Skill

> 注意：这些是 Claude Code 自身的 Skill，与 Plector 系统技能不同。

| 技能 | 典型用法 | 说明 |
|------|----------|------|
| `memory` | 保存/检索开发经验 | 保存开发经验到 Claude Code 记忆 |
| `error_knowledge` | 记录分类错误 | 记录错误模式 |
| `self_improver` | 连续失败时自动修复 | 自动分析并修复问题 |
| `agency_orchestrator` | 复杂任务多角色编排 | 多角色协作完成复杂任务 |
| `test_runner` | 运行测试 | 执行测试套件 |
| `context_refresher` | 长对话保鲜目标 | 保持上下文一致性 |

---

## 与 CLAUDE.md 的关系

此文档是 `CLAUDE.md` 中「Claude Code 工具速查」章节的详细展开。
CLAUDE.md 中的工具速查表是精简版，本文档是完整参考版。

---

*版本：v1.0.0 | 最后更新：2026-04-20*
