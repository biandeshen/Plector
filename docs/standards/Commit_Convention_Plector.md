# Plector 代码提交规范

> 版本: v1.0.0 | 最后更新: 2026-04-28
>
> 本文档是 CLAUDE.md 第五节的详细扩展版。

---

## 一、提交格式

### 1.1 标准格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 1.2 各部分说明

| 部分 | 说明 | 必填 |
|------|------|------|
| `type` | 提交类型 | 是 |
| `scope` | 影响范围（可选） | 否 |
| `subject` | 简短描述（≤50字符） | 是 |
| `body` | 详细说明（可选） | 否 |
| `footer` | 关联 Issue（可选） | 否 |

### 1.3 示例

```
feat(skills): add memory skill for knowledge storage

- Add VectorMemory class with 8 recall modes
- Implement Ebbinghaus decay curve
- Add LLM auto-association on save

Closes #123
```

---

## 二、提交类型（Type）

### 2.1 类型列表

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| `feat` | 新功能 | 添加新技能、新工具、新接口 |
| `fix` | Bug 修复 | 修复已知问题 |
| `docs` | 文档更新 | 更新文档内容 |
| `refactor` | 重构 | 代码重构，不改变功能 |
| `perf` | 性能优化 | 提升性能，不改变功能 |
| `test` | 测试 | 添加/修改测试用例 |
| `chore` | 维护 | 构建脚本、依赖更新 |
| `ci` | CI/CD | CI 配置变更 |
| `revert` | 回退 | 回退之前的提交 |

### 2.2 类型选择指南

```
我添加了一个新的技能模块
  → feat(skills)

我修复了一个 Bug
  → fix(core)

我更新了文档
  → docs

我重构了代码但没有改变功能
  → refactor

我优化了性能
  → perf

我添加了测试
  → test

我更新了依赖版本
  → chore
```

---

## 三、影响范围（Scope）

### 3.1 常用 Scope

| Scope | 说明 | 示例 |
|-------|------|------|
| `core` | 核心模块 | `fix(core): 修复 EventBus 事件分发 bug` |
| `skills` | 技能系统 | `feat(skills): 添加 memory 技能` |
| `skills/memory` | 特定技能 | `feat(skills/memory): 添加联想记忆功能` |
| `skills/agency` | agency 编排 | `feat(skills/agency): 支持 DAG 并行执行` |
| `channels` | 接入渠道 | `feat(channels): 添加 WebSocket 支持` |
| `cli` | 命令行 | `feat(cli): 添加 --verbose 参数` |
| `api` | API 接口 | `feat(api): 添加 /api/health 端点` |
| `docs` | 文档 | `docs: 更新 README` |
| `tests` | 测试 | `test: 添加 EventBus 单元测试` |
| `ci` | CI/CD | `ci: 配置 GitHub Actions` |
| `deps` | 依赖 | `chore(deps): 升级 ruff 到 0.3.0` |

### 3.2 多 Scope 情况

如果一个提交涉及多个 Scope，使用主要 Scope 或省略 Scope：

```
# 主要涉及 skills，次要涉及 cli
feat(skills): 添加命令行技能创建命令

# 涉及多个主要模块
feat: 支持多技能协作和命令行交互
```

---

## 四、主题描述（Subject）

### 4.1 规则

- 使用**现在时**而非过去时
- 不使用句号结尾
- 首个字母小写（除非以大写字母开头）
- 保持简短，≤50 字符
- 不解释"为什么"，只说明"做了什么"

### 4.2 好/坏示例

| 坏 | 好 | 原因 |
|---|-----|------|
| `Added new feature` | `add new feature` | 使用动词原形 |
| `Fixed bug in event bus` | `fix EventBus event dispatch bug` | 简洁具体 |
| `Updated documentation for skills` | `docs: update skills documentation` | 包含 type |
| `I fixed the test` | `test: fix flaky test` | 描述动作非角色 |
| `More changes for memory module` | `feat(skills/memory): add联想记忆模式` | 过于模糊 |

### 4.3 常用动词

| 动词 | 说明 |
|------|------|
| `add` | 添加新功能/文件 |
| `fix` | 修复问题 |
| `update` | 更新现有功能 |
| `remove` | 移除功能/文件 |
| `refactor` | 重构代码 |
| `implement` | 实现功能 |
| `support` | 支持新特性 |
| `improve` | 改进性能/体验 |
| `enable` | 启用功能 |
| `disable` | 禁用功能 |

---

## 五、详细说明（Body）

### 5.1 使用场景

- 提交涉及多个文件的逻辑变更
- 需要解释"为什么"做了这个变更
- 需要说明变更的影响

### 5.2 格式

```markdown
<type>(<scope>): <subject>

本次变更的详细说明：

1. 第一点说明
2. 第二点说明
3. 第三点说明

变更影响：
- 影响范围 A
- 影响范围 B
```

### 5.3 示例

```
feat(skills): add memory skill with 8 recall modes

本次变更：
- 添加 VectorMemory 类实现动态记忆系统
- 实现艾宾浩斯衰减曲线
- 添加 8 种联想模式检索
- 支持 LLM 自动生成关联

影响：
- skills/memory/ 目录结构变更
- core/vector_memory.py 新增
- 需要更新 PLECTOR_SKILLS.md
```

---

## 六、关联 Footer

### 6.1 格式

```markdown
Closes #123
Fixes #456
Related to #789
See also #111
```

### 6.2 多个 Issue

```
Closes #123, #124, #125
```

---

## 七、提交前检查

### 7.1 必须执行

```bash
# 代码检查
ruff check core/ skills/ channels/

# 技能验证
python scripts/validate_skills.py

# 运行测试
python -m pytest
```

### 7.2 完整检查流程

```bash
# 1. 代码检查
ruff check core/ skills/ channels/
if [ $? -ne 0 ]; then
    echo "❌ ruff check failed"
    exit 1
fi

# 2. 技能验证
python scripts/validate_skills.py
if [ $? -ne 0 ]; then
    echo "❌ skills validation failed"
    exit 1
fi

# 3. 运行测试
python -m pytest
if [ $? -ne 0 ]; then
    echo "❌ tests failed"
    exit 1
fi

# 4. 提交
git add -A
git commit -m "..."
git push
```

### 7.3 自动检查（pre-commit）

项目已配置 pre-commit hooks，会在提交前自动运行检查。

---

## 八、提交消息示例

### 8.1 新功能

```
feat(skills): add memory skill for knowledge storage

- Add VectorMemory class with 8 recall modes
- Implement Ebbinghaus decay curve
- Add LLM auto-association on save
- Add retrieval reinforcement mechanism

Closes #45
```

### 8.2 Bug 修复

```
fix(core): resolve EventBus event ordering issue

事件分发顺序不正确，导致某些监听器收到过期事件。
修改了事件队列的实现，使用先进先出顺序。

Fixes #78
```

### 8.3 重构

```
refactor(skills/agency): simplify workflow execution

重构 agency_orchestrator 的工作流执行逻辑：
- 移除复杂的 DAG 解析，直接使用状态机
- 简化并行执行逻辑
- 提升 30% 执行性能

No breaking changes.
```

### 8.4 文档更新

```
docs: update README with quick start guide

添加 5 分钟快速开始指南，包括：
- 环境配置
- 基本使用
- 示例代码

Related to #89
```

### 8.5 测试

```
test: add unit tests for ClosureEngine

添加 ClosureEngine 单元测试：
- test_simple_loop
- test_nested_conditions
- test_retry_mechanism
- test_failure_handling

Coverage: 85%
```

### 8.6 维护

```
chore(deps): upgrade ruff from 0.2.0 to 0.3.0

升级 ruff 以获得更好的 lint 规则支持。
无需其他代码变更。
```

---

## 九、常见问题

### Q1: 提交消息写错了怎么办？

```bash
# 修改最后一次提交消息
git commit --amend -m "correct message"

# 已经 push 了
git push --force-with-lease
```

### Q2: 提交了不该提交的文件怎么办？

```bash
# 从提交中移除文件（保留工作区）
git reset --soft HEAD~1
git reset HEAD path/to/file
git commit -m "..."
```

### Q3: 提交消息太长怎么办？

使用 `git commit -e` 打开编辑器分行写，或使用 body 部分：

```
feat(skills): add new skill

This is the subject line (≤50 chars)

This is the body paragraph that can be as long as needed
to explain what was done and why. It can span multiple
lines and paragraphs as needed.

- Point 1
- Point 2
- Point 3
```

---

## 十、版本历史

- v1.0.0 (2026-04-28)：初始版本
