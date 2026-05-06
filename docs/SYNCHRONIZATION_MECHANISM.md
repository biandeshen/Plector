# Plector 与通用规范仓库同步机制

> 版本：v2.0.0 | 最后更新：2026-04-28
>
> 本文档定义了 Plector 项目与 `E:/笔记/Claude Code规范/` 之间的同步规则。
>
> **重要**：笔记仓库已纳入 Git 版本控制，本文档基于 Git 的版本追踪能力。

---

## 一、架构概述

### 1.1 双仓库结构

```
┌─────────────────────────────────────────────────────────────┐
│  E:/笔记/ (Git 仓库)                                        │
│  公共规范仓库 - Claude Code 通用规范                          │
│  ├── Agent_Behavior_Rules.md                                 │
│  ├── Coding_Convention.md                                   │
│  ├── Commit_Convention.md                                    │
│  └── ...                                                     │
│                                                              │
│  Git 状态: last commit 2026-04-27                           │
└─────────────────────────────────────────────────────────────┘
                              ↕ 引用
┌─────────────────────────────────────────────────────────────┐
│  E:/workspace/Plector/ (Git 仓库)                                 │
│  Plector 项目 - 包含项目特有规范                              │
│  ├── CLAUDE.md ← 引用公共规范 + 版本信息                       │
│  ├── SOUL.md                                                 │
│  └── docs/standards/ ← 项目特有规范                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 同步原则

| 原则 | 说明 |
|------|------|
| **Git 追踪** | 使用 Git 命令获取公共规范的版本信息 |
| **版本锁定** | CLAUDE.md 记录 git commit hash 或 describe |
| **自动同步** | 定期运行 `git fetch` 检查更新 |

---

## 二、版本信息获取

### 2.1 获取公共规范版本

在 `E:/笔记/` 目录下执行以下命令：

```bash
# 获取最新 commit hash（推荐）
git log -1 --format="%h %s"
# 示例输出: a1b2c3d 更新 Agent 行为规则

# 获取带日期的版本
git log -1 --format="%h - %s (%ad)" --date=short
# 示例输出: a1b2c3d - 更新 Agent 行为规则 (2026-04-27)

# 如果有 tags
git describe --tags
# 示例输出: v1.0.0
```

### 2.2 CLAUDE.md 中的版本信息格式

在 CLAUDE.md 顶部使用以下格式：

```markdown
> **公共规范版本**
> - 仓库：`E:/笔记/` (Git 仓库)
> - 最新 commit：`a1b2c3d` (2026-04-27)
> - 更新命令：`cd E:/笔记/ && git log -1 --format="%h %s"`
```

### 2.3 版本检查脚本

创建 `scripts/check_public_standards.sh`：

```bash
#!/bin/bash
# 检查公共规范版本
echo "=== 公共规范版本检查 ==="
cd "E:/笔记/"
echo "最新提交: $(git log -1 --format='%h - %s (%ad)' --date=short)"
echo "提交作者: $(git log -1 --format='%an')"
echo "=== 检查完成 ==="
```

---

## 三、同步流程

### 3.1 日常同步检查

```bash
# 在 E:/笔记/ 目录执行
git fetch origin
git log -1 --format="%h %s"  # 查看最新版本
```

### 3.2 发现更新后的处理

```
1. 执行 git fetch
2. 对比当前记录的 commit hash
3. 如果有更新：
   ├── 更新 CLAUDE.md 顶部的版本信息
   ├── 评估影响（检查相关规范是否冲突）
   └── 如有重大变更，更新项目文档
```

### 3.3 同步检查频率

| 场景 | 频率 | 触发条件 |
|------|------|----------|
| Plector 项目开发 | 每次会话开始 | 检查版本变化 |
| 定期维护 | 每两周 | 全面检查 |
| 重大更新时 | 按需 | 公共规范有重大变更 |

---

## 四、文档引用规范

### 4.1 引用格式

```markdown
> ⚠️ 通用规范见 [E:/笔记/Claude Code规范/Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md)
```

### 4.2 引用原则

| 场景 | 路径类型 | 示例 |
|------|----------|------|
| 项目特有规范 | 相对路径 | `docs/standards/xxx.md` |
| 公共规范 | 绝对路径（file://） | `file:///E:/笔记/Claude Code规范/xxx.md` |
| 根目录文档 | 相对路径 | `SOUL.md` |

---

## 五、冲突处理

### 5.1 冲突场景

| 类型 | 判断依据 | 处理方式 |
|------|----------|----------|
| Plector 特有 | 内容包含 `Plector` 关键字 / 位于项目目录 | 保留项目文档 |
| 公共规范 | 内容为通用规则 / 位于 `E:/笔记/` | 以公共规范为准 |
| 版本冲突 | commit hash 变化 | 评估是否需要同步 |

### 5.2 冲突解决流程

```
发现冲突
    ↓
检查文件来源（E:/笔记/ vs E:/workspace/Plector/）
    ↓
├── 来自 E:/笔记/ → 评估是否需要更新项目文档
└── 来自 Plector → 保留，添加说明
    ↓
更新 CLAUDE.md 版本信息
```

---

## 六、维护清单

### 6.1 版本检查命令

```bash
# 检查公共规范版本
cd E:/笔记/ && git log -1 --format="%h - %s (%ad)" --date=short

# 检查 Plector 项目版本
cd E:/workspace/Plector/ && git log -1 --format="%h - %s (%ad)" --date=short
```

### 6.2 同步检查步骤

- [ ] 在 `E:/笔记/` 执行 `git fetch`
- [ ] 对比 CLAUDE.md 中记录的 commit hash
- [ ] 如有更新，执行 `git log -1` 获取新版本信息
- [ ] 更新 CLAUDE.md 顶部的版本信息
- [ ] 评估是否需要更新项目文档

### 6.3 版本同步记录

```bash
# 记录格式
| 日期 | 公共规范 Commit | Plector 更新 | 操作 |
|------|-----------------|--------------|------|
| 2026-04-28 | a1b2c3d | CLAUDE.md v6.1.0 | 初始同步 |
```

---

## 七、附录

### 7.1 公共规范目录

```
E:/笔记/Claude Code规范/
├── Agent_Behavior_Rules.md         ← 被 Plector CLAUDE.md 第一章引用
├── Coding_Convention.md            ← 被 Plector Code_Standard 引用
├── Commit_Convention.md            ← 被 Plector CLAUDE.md 第五章引用
├── Frontend_Modification_Rules.md   ← 被 Plector CLAUDE.md 第三章引用
├── Language_Convention.md          ← 被 Plector CLAUDE.md 第六章引用
├── Naming_Convention.md
├── PLAN_Template.md                 ← 被 Plector CLAUDE.md 第四章引用
├── Skill_Development_Convention.md
├── Secrets_Management.md
├── CLAUDE_CODE_TOOLS.md
├── CLAUDE_Template.md
└── SOUL_Template.md
```

### 7.2 Plector 项目特有文档

```
E:/workspace/Plector/docs/standards/
├── Behavior_Rules_Plector.md        ← 扩展自 Agent_Behavior_Rules.md
├── Code_Standard_Plector.md         ← 扩展自 Coding_Convention.md
├── Naming_Convention_Plector.md    ← 扩展自 Naming_Convention.md
├── Commit_Convention_Plector.md     ← 扩展自 Commit_Convention.md
├── Frontend_Modification_Rules.md   ← 扩展自 Frontend_Modification_Rules.md
├── Language_Convention_Plector.md  ← 扩展自 Language_Convention.md
├── Plan_Execution_Rules.md          ← 扩展自 PLAN_Template.md
├── Skill_Development_Plector.md     ← Plector 特有（tier 系统）
└── Technical_Spec_Plector.md         ← Plector 特有（技术规格）
```

### 7.3 快速参考

```bash
# 查看公共规范版本
git -C "E:/笔记/" log -1 --format="%h %s"

# 查看 Plector 项目版本
git -C "E:/workspace/Plector/" log -1 --format="%h %s"

# 检查更新
git -C "E:/笔记/" fetch && git -C "E:/笔记/" log --oneline -5
```

---

## 八、版本历史

- v2.0.0 (2026-04-28)：基于 Git 的同步方案，替代手动版本号；使用 git log/fetch 命令获取版本信息
- v1.0.0 (2026-04-28)：初始版本，手动版本号管理

---

*本同步机制会随着项目发展持续更新。*
