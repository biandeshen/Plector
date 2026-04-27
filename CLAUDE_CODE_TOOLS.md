# Claude Code 工作流规范（公共规范）

> 版本：v1.0.0 | 更新：2026-04-21
> 本文档描述 Claude Code 如何组合使用已有工具和技能形成高效工作流。

---

## 一、文档定位

```
CLAUDE.md              ← 项目规范入口（仅 Plector 项目约束）
CLAUDE_CODE_TOOLS.md   ← Claude Code 工作流规范（通用，任何项目可用）
CLAUDE_PLECTOR_TOOLS.md ← Plector 项目技能文档（仅 Plector 项目）
```

---

## 二、Claude Code 内置工具速查

| 工具 | 典型用法 |
|------|----------|
| `Bash` | `git log`、`pytest`、`ruff` |
| `Read` / `Edit` / `Write` | 读写代码 |
| `Grep` / `Glob` | 搜索引用、找文件 |
| `Task` | 复杂任务分解跟踪 |
| `SendMessage` | 输出假设、请求确认 |

---

## 三、常用工作流模式

### 3.1 代码审查工作流

```
Read(目标文件) → Bash(git log -p -3) → Grep(检查引用) → Task(分析报告)
```

**场景**：用户要求审查代码
**执行步骤**：
1. `Read` 读取目标文件完整内容
2. `Bash: git log -p -3 -- <file>` 分析历史变更
3. `Grep` 检查相关引用和依赖
4. `Task` 启动 code-reviewer 子代理进行深入分析
5. `SendMessage` 输出审查报告

### 3.2 Bug 修复工作流

```
Read(错误上下文) → Grep(定位问题) → Bash(pytest) → Edit(修复) → Bash(验证)
```

**场景**：用户报告 bug
**执行步骤**：
1. `Read` 读取报错文件或日志
2. `Grep` 定位问题代码位置
3. `Bash: pytest` 或 `ruff check` 复现错误
4. `[假设]` 输出假设并记录到 Plan.md
5. `Edit` 进行最小化修复
6. `Bash: pytest` 验证修复

### 3.3 重构工作流

```
Task(分解任务) → Read(理解结构) → Grep(检查依赖) → Write(新实现) → Bash(测试)
```

**场景**：需要重构代码
**执行步骤**：
1. `Task` 分解大任务为子任务
2. `Read` 理解当前代码结构
3. `Grep` 检查所有引用点
4. `[假设]` 输出重构方案假设
5. `Write` 创建新实现或 `Edit` 逐步修改
6. `Bash: pytest` + `ruff check` 验证

### 3.4 文档编写工作流

```
Glob(找模板) → Read(参考) → Write(新建) → Bash(git add)
```

**场景**：编写文档
**执行步骤**：
1. `Glob` 查找相关模板或参考文档
2. `Read` 读取模板格式
3. `Write` 按照模板格式编写
4. `Bash: git add` 添加到版本控制

---

## 四、Skill 调用工作流

### 4.1 可用 Skill 列表

Claude Code 的 Skill 存储在 `.claude/skills/` 目录下，通过 `<available_skills>` 标签提供访问。

当前可用的 Skill：
| Skill | 说明 |
|-------|------|
| `ai-image-generation` | AI 图片生成 |
| `create-skill` | 创建新 Skill |
| `create-skill-ui` | 创建 Skill HTML 界面 |
| `create-subagent` | 创建子代理 |
| `ui-designer` | Web UI 设计 |

### 4.2 Skill 调用模式

```
用户触发 → Skill(技能名) → 加载 SKILL.md → 执行技能指令
```

**场景**：需要创建 UI 界面
1. 用户要求创建 Web 界面
2. 调用 `Skill: ui-designer`
3. Skill 加载设计指南和输出规范
4. 执行 UI 设计流程

### 4.3 Skill 组合工作流

复杂任务可组合多个 Skill：

```
Skill(ui-designer) → Skill(create-skill-ui) → Bash(部署)
```

---

## 五、主动升级模式

以下情况立即暂停，请求确认：

| 触发条件 | 动作 |
|----------|------|
| 提交含 `!important`/`hack`/`fix` | `Bash: git log -p` 检查 |
| 影响超过 3 个组件 | `Grep` 检查引用 |
| 不可逆操作 | `SendMessage` 请求确认 |
| 假设被否定 | 立即停止，重新分析 |

---

## 六、快速索引

| 内容 | 位置 |
|------|------|
| Plector 项目规范 | `CLAUDE.md` |
| Plector 项目技能 | `CLAUDE_PLECTOR_TOOLS.md` |
| Claude Code 工作流模式 | 参见本文档第三、四章 |
| 公共规范（独立维护） | `E:/笔记/Claude Code规范/` |

**公共规范文档**（在 Obsidian 笔记仓库中维护）：
- `E:/笔记/Claude Code规范/Coding_Convention.md` - 代码规范
- `E:/笔记/Claude Code规范/Agent_Behavior_Rules.md` - Agent 行为规则
- `E:/笔记/Claude Code规范/Commit_Convention.md` - 提交规范
- `E:/笔记/Claude Code规范/Language_Convention.md` - 语言约定
- `E:/笔记/Claude Code规范/Frontend_Modification_Rules.md` - 前端修改规范

---

*版本：v1.0.0 | 更新：2026-04-21*
