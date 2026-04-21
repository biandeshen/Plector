---
tags:
  - AI-Agent
  - workflow
  - claude-code
  - 方法论
  - 框架
type: research
created: 2026-04-21
related-to:
  - [[84_AI助手_核心框架参考]]
  - [[90_多智能体框架深度对比]]
  - [[73_AI工具链整合方案]]
  - [[91_AI_Agent错误处理与自愈机制]]
  - [[92_Temporal工作流与AI_Agent持久化]]
---

# AI 开发方法论矩阵：从单兵到军团

> 整理自多轮讨论。核心洞察：**单 Agent 与多 Agent 框架不是互斥的，而是适用于不同层级的需求。两条路径应结合使用。

---

## 一、两种路径的本质

| 路径 | 本质 | 核心杠杆 |
|------|------|----------|
| **单 Agent 极限作战** | 深度用好一个 AI 助手 | 规范文件 + Spec 先行 + TDD + 自动化循环 |
| **多 Agent 框架协作** | 构建虚拟团队 | 框架 + 角色 + 流程 |
| **流程框架管控** | 轻量约束 AI 行为 | 轻量框架按需引入 |

---

## 二、三层方案矩阵

### 第一层：单兵极限作战（Claude Code 本地深度玩法）

**适用场景**：日常开发、单次长任务、个人项目、原型验证。

**核心思想**：充分利用 AI 自身的能力 + 简单脚本，实现高效、可控的自动化。

| 需求 | 具体方案 | 操作要点 |
|------|---------|----------|
| **产出符合规范** | `CLAUDE.md` + Spec 先行 | 手动维护 `CLAUDE.md` 作为唯一真相源，每次功能前先对 Spec |
| **代码质量** | TDD 流程 + AI 生成测试 | 先让 AI 写失败测试，再实现功能，最后 `npm test` 验证 |
| **无人值守长任务** | `tmux` + `claude-auto-continue` | 创建 tmux 会话，启动守护工具，下达长任务后断开连接 |
| **自动响应 Git 事件** | Headless 模式 + Git Hooks | 在 `.git/hooks` 中调用 AI 生成代码 |
| **自主开发循环** | Bash 脚本 + Headless 模式 | 读取任务清单，依次调用 AI 执行并记录结果 |

#### 完整工作流

```bash
# 1. 创建 tmux 会话
tmux new -s dev_session

# 2. 进入项目启动守护 AI
cd my-project
claude-auto-continue

# 3. 下达任务
> 基于 spec.md 实现用户认证模块，每完成一个子功能就提交一次

# 4. 分离会话，让任务后台运行
Ctrl+B, D

# 5. 第二天查看结果
tmux attach -t dev_session
```

---

### 第二层：流程框架管控（小队流程化作战）

**适用场景**：团队协作、需要严格流程管控、老项目维护、需求变更频繁。

**核心思想**：用轻量框架**规范 AI 的协作过程**，而不是替换 AI。

| 工具 | 如何结合 | 最佳场景 |
|------|---------|---------|
| **OpenSpec** | 管理变更提案，AI 阅读 `openspec/changes/` 目录并按提案实施 | 存量项目新增功能或重构，保留变更历史 |
| **gstack** | 用角色命令切换视角，如 `/architect` 后再提问 | 需要多视角评审架构决策 |
| **Superpowers** | 将 TDD 强制流程写入 `CLAUDE.md`，让 AI 遵循 | 对代码质量要求极高的项目 |

#### OpenSpec + AI 工作流

```bash
# 1. 创建变更提案
openspec change add two-factor-auth

# 2. 让 AI 实施方案
> 阅读 openspec/changes/add-two-factor-auth/ 下的所有文件，按照 proposal.md 实现双因素认证

# 3. 完成后归档
openspec archive add-two-factor-auth
```

---

### 第三层：多 Agent 框架（军团集群化作战）

**适用场景**：大型项目从零到一、复杂系统、需要模拟不同角色进行决策。

**核心思想**：用多 Agent 框架构建虚拟开发团队，AI 作为其中一个执行单元。

| 工具 | 如何与 AI 结合 | 最佳场景 |
|------|------------|---------|
| **BMAD** | 提供 PRD 和架构设计，AI 作为编码 Agent | 企业级大型项目，需要完整文档和合规流程 |
| **AgencyAgent** | 启动多 Agent 模拟开发公司，编码 Agent 对接 AI | 快速验证产品想法，需要全面职能覆盖 |
| **SpecKit** | 用 SpecKit 生成规范蓝图，AI 按 `tasks.md` 执行开发 | GitHub 生态内的新项目启动 |
| **DeerFlow** | 将 AI 包装为可调度节点，处理长耗时任务 | 需要任务持久化和断点恢复的复杂场景 |

#### AgencyAgent + AI 混合架构

```yaml
# agency agents 配置
agents:
  - name: coder
    role: senior full-stack developer
    tool: claude_code_headless
    prompt: "You are an expert coder. Implement tasks assigned by architect."
```

---

## 三、成长路线图

| 阶段 | 目标 | 具体行动 |
|------|------|----------|
| **第一阶段（当前** | 精通单 Agent 模式 | 建立 `CLAUDE.md`、Spec、TDD、人工校验的肌肉记忆 |
| **第二阶段** | 实现本地自动化 | 掌握 `tmux` + `claude-auto-continue`，让长任务无人值守跑通 |
| **第三阶段** | 引入流程框架 | 选择一个轻量框架（推荐 OpenSpec），融入 AI 工作流 |
| **第四阶段** | 探索多 Agent 框架 | 根据项目需求，尝试搭建虚拟团队，让 AI 作为执行单元 |

---

## 四、混合方案示例

**场景**：Next.js 项目添加复杂新功能，团队要求完整文档和评审记录。

### 混合方案

1. **OpenSpec** 管理变更提案，记录需求和设计决策
2. **TDD 流程**写入 `CLAUDE.md`，AI 必须遵循红-绿-重构循环
3. **tmux 会话**中启动 `claude-auto-continue`，AI 通宵实施
4. **安全评审**用角色命令检查漏洞
5. **小步提交**保留清晰历史

### 核心原则

> 不需要学习全新的复杂工具，只是在现有 AI 工作流上按需叠加轻量"插件"。在**不丢失灵活性**的前提下，获得**团队协作级**的掌控力。

---

## 五、关键要点

| 要点 | 说明 |
|------|------|
| **规范文件是核心** | `CLAUDE.md` / `SPEC.md` / `tasks.md` 是 AI 动作的约束层 |
| **TDD 是质量盾** | 先写测试再实现，自动化验证 |
| **小步提交是历史追溯** | 每完成一个子任务就提交，保留清晰历史 |
| **框架按需引入** | 不必一次性引入所有工具 |

---

*整理自多轮讨论，2026-04-21*
