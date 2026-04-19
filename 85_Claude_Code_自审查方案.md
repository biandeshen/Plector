# Claude Code 自审查方案

> **创建时间**: 2026-04-18
> **序号**: 85
> **标签**: claude-code, hooks, skills, 自审查, 质量保障
> **状态**: 归档

---

## 一、核心需求

**目标**：让 Claude Code 在完成代码编写后，能够自动审查自己的产出，确保与需求一致，没有缺陷、冗余或错误。

这是一个典型的"自举"或"自检"场景，需要建立闭环机制：**需求 → 编码 → 自动审查 → 反馈修复**。

---

## 二、方案对比

| 方案 | 实现方式 | 优点 | 缺点 |
|------|----------|------|------|
| **方案一：Hooks + /review** | PostToolUse Hook 触发审查命令 | 自动化程度高 | 启动新会话，token 消耗翻倍 |
| **方案二：claude-code-loops** | coder + reviewer 双 Agent 循环 | 专为自审设计，开箱即用 | 需额外安装，工作流固定 |
| **方案三：self-review Skill** | 教导 Claude 写完就自查 | 最轻量，单会话完成 | 依赖指令遵循能力 |
| **方案四：MCP 增强** | 结合 MCP 工具深度审查 | 审查深度更强 | 需额外配置 MCP |

---

## 三、方案一：Hooks + Slash Command

### 3.1 创建审查 Slash Command

在 `.claude/commands/review.md` 中创建：

```markdown
---
description: 审查最近修改的代码是否与需求一致、有无缺陷/冗余/错误
---

请审查以下代码变更：

**需求描述**：
{{需求摘要}}

**变更的文件**：
{{$files}}

请按以下维度进行严格审查：
1. **需求一致性**：代码是否实现了所有需求点？有无遗漏或偏离？
2. **逻辑缺陷**：是否存在空指针、边界条件未处理、异常未捕获、死循环等？
3. **冗余代码**：是否有重复逻辑、未使用的变量/函数？
4. **错误处理**：错误是否被正确传播或处理？
5. **代码规范**：命名、格式、注释是否符合项目约定？

输出格式：
- ❌ **严重问题**（必须修复才能继续）
- ⚠️ **一般问题**（建议修复）
- 💡 **优化建议**（可选）

如果未发现问题，输出 ✅ **审查通过**。
```

### 3.2 配置 Hook

在 `.claude/settings.json` 中添加：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "claude -p \"/review\" --allowedTools Read,Grep"
          }
        ]
      }
    ]
  }
}
```

---

## 四、方案二：claude-code-loops

### 4.1 简介

`claude-code-loops` 创建两个 Agent：`coder` 负责写代码，`reviewer` 负责审查，两者交替运行直到审查通过。

### 4.2 安装与使用

```bash
# 全局安装
npm install -g claude-code-loops

# 在项目目录中运行
claude-code-loops "实现用户登录功能，包括密码加密和 JWT 生成"
```

### 4.3 工作流程

1. `coder` 编写代码
2. `reviewer` 审查代码
3. 发现问题则返回给 `coder` 修复
4. 重复直到审查通过或达到最大迭代次数

---

## 五、方案三：self-review Skill

### 5.1 创建 Skill

在 `.claude/skills/self-review.md` 中创建：

```markdown
---
name: self-review
description: 在完成任何代码编写或修改后，立即对产出进行质量审查
---

# 自审查流程

当你使用 `Write` 或 `Edit` 工具完成代码变更后，**必须**立即执行以下步骤：

1. 回顾用户提出的原始需求（从对话历史中获取）。

2. 逐条检查代码是否满足需求。

3. 使用 `grep`、`ast-grep` 等工具静态分析代码，查找潜在缺陷：
   - 空指针风险
   - 未处理的异常
   - 边界条件
   - 死循环
   - 资源泄漏

4. 识别重复代码或未使用的变量/函数。

5. 输出审查结果，格式如：
   - ✅ 通过：无问题
   - ⚠️ 警告：列出问题和建议
   - ❌ 失败：严重问题，必须立即修复

如果发现问题，**立即修复**，然后**再次审查**，直到通过为止。
```

### 5.2 在 CLAUDE.md 中引用

```markdown
## 行为准则
- 完成任何代码编写后，必须遵循 `self-review` Skill 进行自查。
```

---

## 六、方案四：MCP 增强审查

### 6.1 MCP 工具推荐

| MCP | 作用 | 安装命令 |
|-----|------|---------|
| `sequential-thinking` | 结构化推理，更系统地分析缺陷 | `claude mcp add sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking` |
| `code-simplifier` | 自动检测并简化冗余代码 | `/plugin install code-simplifier` |
| `ast-grep` | 通过 Bash 调用，进行精确的代码模式匹配 | 安装 `sg` CLI |

### 6.2 在审查中使用的命令示例

```markdown
- 使用 `sg -p 'if ($NULL != $$$)'` 查找可能的空指针判断错误
- 使用 `rg 'catch.*Exception'` 检查异常处理是否恰当
```

---

## 七，推荐方案

| 场景 | 推荐方案 |
|------|----------|
| **个人轻量开发** | 方案三（self-review Skill）|
| **复杂 Agent 严格审查** | 方案二（claude-code-loops）|
| **完全自动化** | 方案一（Hooks）|
| **深度审查** | 方案四（MCP 增强）+ 方案三（Skill）|

### 最佳实践组合

**方案三 + 方案四**：
1. 创建 `self-review` Skill 嵌入项目
2. 安装 `sequential-thinking` 和 `code-simplifier`
3. 在 `CLAUDE.md` 中声明每次编辑后必须自检
4. 最轻量，无需额外工具

---

## 八、下一步行动

1. 在当前项目中创建 `.claude/commands/review.md` 和 `.claude/skills/self-review.md`
2. 在 `CLAUDE.md` 中添加自检要求
3. 测试：完成一个简单函数，观察是否自动输出审查结果

---

## 相关文档

- [[84_AI助手_核心框架参考]] - AI助手框架参考
- [[66_规范_技能开发规范]] - 技能开发规范
- [[64_规范_代码开发规范]] - 代码开发规范
