# Plector 与通用规范仓库同步机制

> 版本：v1.0.0 | 最后更新：2026-04-28
>
> 本文档定义了 Plector 项目与 `E:/笔记/Claude Code规范/` 之间的同步规则。

---

## 一、同步原则

### 1.1 单一来源原则

- **公共规范**（跨项目通用）在 `E:/笔记/Claude Code规范/` 中维护
- **项目规范**（Plector 特有）在 `e:\产品\Plector\` 中维护
- Plector 项目通过引用方式使用公共规范

### 1.2 版本锁定原则

- CLAUDE.md 顶部记录公共规范的版本信息
- 更新公共规范后，需要同步更新 Plector 项目的引用版本

### 1.3 分层原则

```
公共规范层（E:/笔记/Claude Code规范/）
    │
    ├── Agent_Behavior_Rules.md      ← 通用行为规则
    ├── Coding_Convention.md         ← 通用代码规范
    ├── Commit_Convention.md          ← 通用提交规范
    └── ...

项目规范层（e:\产品\Plector\）
    │
    ├── CLAUDE.md                     ← 项目入口 + 引用
    ├── docs/standards/               ← 项目特有规范
    └── ...
```

---

## 二、文档分类与归属

### 2.1 公共规范（来自 `E:/笔记/Claude Code规范/`）

| 规范 | 用途 | 归属 |
|------|------|------|
| Agent_Behavior_Rules.md | Agent 行为规则（假设验证、熔断等） | 公共 |
| Coding_Convention.md | 代码规范（Python、命名等） | 公共 |
| Naming_Convention.md | 命名规范 | 公共 |
| Commit_Convention.md | Git 提交规范 | 公共 |
| Language_Convention.md | 语言约定（中英文使用） | 公共 |
| Frontend_Modification_Rules.md | 前端修改规范 | 公共 |
| PLAN_Template.md | 任务计划模板 | 公共 |
| Skill_Development_Convention.md | 技能开发规范 | 公共 |
| Secrets_Management.md | 密钥管理规范 | 公共 |

### 2.2 项目规范（Plector 特有）

| 规范 | 用途 | 归属 |
|------|------|------|
| docs/standards/Behavior_Rules_Plector.md | Plector 行为约束（含应用场景） | 项目 |
| docs/standards/Code_Standard_Plector.md | Plector 代码规范（含第8章技能规范） | 项目 |
| docs/standards/Naming_Convention_Plector.md | Plector 命名规范（含事件命名） | 项目 |
| docs/standards/Skill_Development_Plector.md | Plector 技能开发规范（含 tier 系统） | 项目 |
| docs/standards/Technical_Spec_Plector.md | 技术规格（JSON-RPC/MCP） | 项目 |
| docs/PLECTOR_SKILLS.md | Plector 技能总览 | 项目 |
| SOUL.md | Plector 灵魂（决策树、技能联动） | 项目 |

---

## 三、同步规则

### 3.1 公共规范更新流程

当 `E:/笔记/Claude Code规范/` 中的规范更新时：

```
1. 识别受影响的规范
   ├── Agent_Behavior_Rules.md 更新 → 影响 Plector 行为约束
   ├── Coding_Convention.md 更新 → 影响 Plector 代码规范
   └── ...

2. 评估影响
   ├── 仅补充说明 → 无需修改 Plector 文档
   ├── 规范冲突 → 需要协调 Plector 文档
   └── 重大变更 → 需要重新同步
```

### 3.2 版本更新规则

每次公共规范更新时，同步更新：

```markdown
<!-- 在 CLAUDE.md 顶部 -->
> **规范版本信息**
> - 公共规范来源：`E:/笔记/Claude Code规范/`
> - 公共规范版本：vX.X.X | 检查日期：YYYY-MM-DD
```

### 3.3 同步检查频率

- **每次 Plector 项目更新时**：检查 CLAUDE.md 版本信息
- **每季度**：全面检查公共规范与项目规范的对应关系
- **发现问题时**：立即同步

---

## 四、文档引用规范

### 4.1 CLAUDE.md 中的引用格式

```markdown
> ⚠️ 通用规范见 [E:/笔记/Claude Code规范/Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md)
```

### 4.2 引用原则

| 场景 | 引用方式 |
|------|----------|
| 项目特有规范 | 使用相对路径：`docs/standards/xxx.md` |
| 公共规范 | 使用绝对路径：`file:///E:/笔记/Claude Code规范/xxx.md` |
| 根目录文档 | 使用相对路径：`SOUL.md`、`PLAN_TEMPLATE.md` |

### 4.3 文件链接格式

```markdown
<!-- 项目内文档 -->
[docs/standards/Behavior_Rules_Plector.md](docs/standards/Behavior_Rules_Plector.md)

<!-- 外部文档（绝对路径） -->
[E:/笔记/Claude Code规范/Agent_Behavior_Rules.md](file:///E:/笔记/Claude Code规范/Agent_Behavior_Rules.md)
```

---

## 五、冲突处理

### 5.1 规范冲突场景

当 Plector 项目规范与公共规范出现冲突时：

| 冲突类型 | 处理方式 |
|----------|----------|
| **Plector 特有内容** | 保留项目规范，公共规范作为补充 |
| **公共规范更新** | 评估后决定是否同步更新 |
| **版本不一致** | 以公共规范为准，更新项目引用 |

### 5.2 冲突解决流程

```
1. 识别冲突内容
2. 判断是公共规范还是项目特有
3. 如果是公共规范 → 评估是否需要更新项目文档
4. 如果是项目特有 → 保留项目文档，添加说明
5. 更新 CLAUDE.md 版本信息
```

---

## 六、维护清单

### 6.1 每次更新前检查

- [ ] 公共规范版本是否已更新？
- [ ] Plector 项目的 CLAUDE.md 版本是否同步？
- [ ] 外链路径是否仍然有效？
- [ ] 项目规范与公共规范是否有冲突？

### 6.2 定期检查（每季度）

- [ ] 检查所有外链是否有效
- [ ] 对比公共规范与项目规范的重叠度
- [ ] 评估是否需要重构项目规范
- [ ] 更新本同步机制文档

### 6.3 版本同步记录

| 日期 | 公共规范版本 | Plector 更新内容 | 更新人 |
|------|-------------|-----------------|--------|
| 2026-04-28 | v1.0.0 | CLAUDE.md v6.1.0 | Qoder |

---

## 七、附录

### 7.1 公共规范目录结构

```
E:/笔记/Claude Code规范/
├── Agent_Behavior_Rules.md
├── CLAUDE_CODE_TOOLS.md
├── CLAUDE_Template.md
├── Coding_Convention.md
├── Commit_Convention.md
├── Frontend_Modification_Rules.md
├── Language_Convention.md
├── Naming_Convention.md
├── PLAN_Template.md
├── Secrets_Management.md
├── Skill_Development_Convention.md
└── SOUL_Template.md
```

### 7.2 Plector 项目规范目录结构

```
e:\产品\Plector\docs\standards\
├── Behavior_Rules_Plector.md
├── Code_Standard_Plector.md
├── Commit_Convention_Plector.md
├── Frontend_Modification_Rules.md
├── Language_Convention_Plector.md
├── Naming_Convention_Plector.md
├── Plan_Execution_Rules.md
├── Skill_Development_Plector.md
└── Technical_Spec_Plector.md
```

---

*本同步机制会随着项目发展持续更新。*
