# 任务：ReAct 元认知 + 技能主动联动 ⚠️ 核心任务

## 核心原则：ReAct 不需要写代码

ReAct 本身就是 LLM 的推理模式：
```
观察 → 推理 → 行动 → 观察 → ...
```

**LLM 本身就在 ReAct 循环中**。关键是要让 LLM **主动**把技能串起来。

---

## 技能联动触发规则（必须实现）

### 当遇到任务时，LLM 应主动推理：

1. **这个任务需要哪些技能？**
2. **这些技能谁先谁后？**
3. **哪些技能需要多角色协作？**

### 决策规则：

```
任务进来
    ↓
["这个任务够复杂吗？"]
    ↓
如果复杂（多角色/多阶段/跨领域）
    → 调用 context_refresher 分析
    → 调用 agency_orchestrator.compose_workflow 编排多角色
    → 从 external-skills/ 匹配合适角色
    ↓
如果简单（单步/单领域/已知模式）
    → 直接执行
    ↓
注意：永远不要不调用任何工具就直接执行复杂任务
```

### 示例决策路径：

```
任务："为 Plector 项目生成一份 PPT"
↓
LLM 推理：
  "这需要内容创作 + 视觉设计 + 项目分析"
  → 应该调用 agency_orchestrator.compose_workflow
  → 从 external-skills/ 匹配角色
  → 多角色协作完成
  → 不是自己直接写 PPT 内容

任务："改进 Plector 的某段代码"
↓
LLM 推理：
  "需要代码分析 + 架构评估 + 实施"
  → context_refresher 分析复杂度
  → 如果复杂 → agency_orchestrator 多角色
  → 如果简单 → self_improver 直接执行
```

---

## 不要做的事：

- ❌ 自己直接写代码 / 写内容
- ❌ 不调用任何工具就直接执行
- ❌ 只用一个技能完成复杂任务
- ❌ 遇到复杂任务不主动构建工作流

## 应该做的事：

- ✅ 先分析任务复杂度
- ✅ 调用 agency_orchestrator 编排多角色
- ✅ 从 external-skills/ 匹配合适角色
- ✅ 让多个技能协作完成
- ✅ brainstorming superpower 参与方案生成

---

## 核心原则：少写死代码，多用 YAML + LLM

```
代码越少越灵活，逻辑越少越通用
YAML = 声明式 = 灵活
LLM = 真正的执行器
```

**代码只做**：解析YAML → 调用工具 → 读写文件
**YAML描述**：角色A做什么、角色B做什么、brainstorming参与什么
**LLM自己**：读取所有配置，自己决定用哪个、怎么串

### 不应该做的事：

- ❌ 用 Python 代码写死执行逻辑
- ❌ 在 implementation.py 里写"先调A再调B"的硬编码流程
- ❌ 创建新的 Python 角色类（已有 external-skills/roles/）

### 应该做的事：

- ✅ 纯 YAML 驱动：agency_orchestrator 的工作流本身就是 YAML
- ✅ skill.json 的 description + triggers 描述清楚"什么时候用"
- ✅ LLM 读取配置自己决定怎么组合
- ✅ 代码只做机械性的事（加载、执行、返回）

### 示例：应该 vs 不应该

```
不应该（写死）：
  implementation.py 里写 _execute_with_roles(A, B, C)

应该（YAML驱动）：
  workflows/self_improve/self_improve.yaml
  LLM 读取后自己决定调用哪些角色
```

---

## 关键实现点

### 1. skill.json 的 triggers 字段

所有技能的 triggers 必须清晰描述"什么时候用我"：

```json
{
  "triggers": [
    "任务涉及多角色协作",
    "需要从不同角度分析问题",
    "复杂的多阶段任务"
  ]
}
```

### 2. context_refresher 的核心作用

```json
{
  "description": "分析任务复杂度，判断是否需要多角色协作。
    - 输入：任务描述 + 对话历史
    - 输出：{complexity: 'low'/'medium'/'high', reasoning: '...', recommended_skills: [...]}
    - 触发场景：遇到非平凡任务时"
}
```

### 3. agency_orchestrator 的核心作用

```json
{
  "description": "多角色工作流编排。当任务需要多角色协作时使用。
    - compose_workflow: 组合多角色工作流
    - run_workflow: 执行已创建的工作流
    - 触发场景：context_refresher 判断为复杂任务时"
}
```

### 4. self_improver 的核心作用

```json
{
  "description": "Plector 改进执行。当任务需要代码改造时使用。
    - 分析改进需求
    - 生成改进方案
    - 执行改进（通常需要多角色协作）
    - 触发场景：需要改进 Plector 系统时"
}
```

---

## 交付标准

1. LLM 遇到复杂任务时，**主动**调用 `context_refresher` 分析复杂度
2. 复杂任务通过 `agency_orchestrator.compose_workflow` 编排多角色
3. `external-skills/` 中的 superpower 技能被真正利用
4. `brainstorming` 在方案生成阶段被调用
5. 简单任务才直接执行，不强行复杂化

## 状态：✅ 完成

- SOUL.md 已创建（LLM 元认知规则）
- CLAUDE.md 已更新（纳入决策树和触发词表）
- 测试 77/77 通过
