# Plector 产品需求文档（PRD）v1.6

**版本**: 1.6
**状态**: 已定稿
**产品经理**: [你的名字]
**关联 BRD 版本**: 2.0
**项目代号**: Plector – 让复杂智能体在企业可落地
**最后更新**: 2026-04-27

> 本次修订（v1.5 → v1.6 战略升级 + 五角色审查优化）：
> - **关联 BRD v2.0**：定位调整为"轻量级企业智能体引擎"
> - **核心竞争力重定义**：从"自我进化"到"可落地的治理与集成"
> - **五角色 Agent 审查结论**：
>   - 架构师：范围精简（174角色→5-10，9中间件→3-4）
>   - 安全合规官：OTel 升级为 P0（阻断发布优先级）
>   - 产品经理：量化指标明确（70% 闭环修复成功率）
>   - 增长顾问：MCP 生态杠杆、Claude Code 场景优先
>   - 运维：OTel MVP 实现、Docker Compose 部署

---

## 1. 产品范围与优先级

### 1.1 功能范围（MoSCoW）

| 优先级 | 功能模块 | 说明 | 状态 |
|--------|----------|------|------|
| **Must** | 自主决策循环（ReAct） | Agent 核心推理-行动-观察循环 | ✅ 已完成 | 保留 |
| **Must** | 工具调用（Function Calling） | 稳定的工具注册与调用机制 | ✅ 已完成 | 保留 |
| **Must** | 事件总线 | 异步发布/订阅，解耦技能与闭环 | ✅ 已完成 | 保留 |
| **Must** | 技能注册表与执行器 | 管理技能元数据和调用 | ✅ 已完成 | 保留 |
| **Must** | 闭环引擎（条件图） | 事件驱动的自愈流程 | ✅ 已完成 | 保留 |
| **Must** | 上下文构建器 | 从项目文件构建系统提示词 | ✅ 已完成 | 保留 |
| **Must** | CLI 接入渠道 | 命令行交互 | ✅ 已完成 | 保留 |
| **Must** | MCP Client | 连接外部 MCP Server | ✅ 已完成 | 保留 |
| **Must** | **OpenTelemetry 可观测性** | Trace/Metrics/Logs 标准输出 | 🔄 进行中 | **P0 升级** |
| **Must** | **不可篡改审计日志** | WORM 存储 + Hash Chain | 🔄 进行中 | **P0 升级** |
| **Must** | **SecurityMiddleware** | 输入验证 + 权限检查 | 🔄 进行中 | **P0 升级** |
| **Should** | 技能治理（健康分、淘汰） | 技能健康监控与自动淘汰 | 🔄 进行中 | 保留 |
| **Should** | 自我审视 | 定期生成依赖、事件完整性报告 | 🔄 进行中 | 保留 |
| **Should** | WebSocket 渠道 | 实时双向通信 | ✅ 已完成 | 保留 |
| **Should** | 技能热更新 | 文件哈希检测，自动重载 | 🔄 进行中 | 保留 |
| Could | HTTP API | RESTful 接口 | 📅 规划中 | v2.x |
| ~~Could~~ | ~~中间件架构（9个）~~ | ~~中间件链~~ | ~~v2.x~~ | **精简至 3-4 个核心中间件** |
| ~~Should~~ | ~~agency_orchestrator（174个角色）~~ | ~~多智能体协作~~ | ~~✅~~ | **v2.x 精简至 5-10 个核心角色** |
| ~~Could~~ | ~~Dialect 编程语言~~ | ~~领域特定语言~~ | ~~远期~~ | **删除，复杂度不匹配** |
| ~~Could~~ | ~~Soul 文件系统~~ | ~~灵魂文件系统~~ | ~~远期~~ | **v2.x，MCP 优先级更高** |

> **安全合规官建议**：OTel、不可篡改审计日志、SecurityMiddleware 升级为 P0 阻断优先级，v1.x 发布前必须完成。

### 1.2 核心竞争力重定义

**新核心命题**：让复杂智能体在企业可落地

| 旧命题 | 新命题 | PRD 对应章节 |
|--------|--------|--------------|
| "自我进化" | **可治理** | 闭环引擎 + 技能治理 |
| "极简" | **可观测** | OpenTelemetry 标准 |
| "事件驱动" | **可集成** | 中间件链 + MCP |
| "闭环自愈" | **可落地** | 安全边界 + 审计日志 |

### 1.4 技能与工具的分层定义

为保持系统简洁可控，Plector 将功能单元区分为**技能（Skill）**和**工具（Tool）**。
**区分标准不是技术特征（是否有状态/事件/依赖），而是"是否参与治理"。**

| 类型 | 定义 | 治理范围 | 数量限制 | 判断原则 |
|------|------|----------|----------|----------|
| **技能** | 需要治理的功能模块（健康分监控、依赖检测、自动淘汰） | 完整治理 | **≤ 15 个** | 该功能出错会影响系统稳定性或核心闭环 |
| **工具** | 不需要治理的纯函数，仅用于辅助任务 | 不治理 | 无限制 | 出错不影响系统核心流程的纯函数 |

**判断示例**：
- `health_monitor`：出错会导致健康监控失效 → **技能**
- `error_knowledge`：错误知识化是闭环核心 → **技能**
- `code_writer`：代码生成出错可能影响闭环 → **技能**
- `markdown_converter`：格式转换失败不影响系统稳定性 → **工具**
- `web_search`：网络搜索失败不影响核心循环 → **工具**

> 注：一个功能模块即使有状态、事件或依赖，若其运行失败不会对系统整体稳定性产生重大影响，也应作为工具实现。反之，一个看似简单的函数如果被闭环依赖且需要健康监控，则必须作为技能。

**核心技能列表（当前实现，11 个）**：

| 技能 | 用途 | 治理 | 建议 |
|------|------|------|------|
| `health_monitor` | 系统健康检查 | ✅ | 保留 |
| `error_knowledge` | 错误记录与分类 | ✅ | 保留 |
| `context_refresher` | 上下文保鲜 | ✅ | 保留 |
| `self_improver` | 自我改进 | ✅ | 个人场景可禁用 |
| `code_writer` | 代码生成 | ✅ | 保留 |
| `test_runner` | 测试执行 | ✅ | 保留 |
| `file_utils` | 文件操作 | ✅ | 禁用，使用 MCP 替代 |
| `memory` | 记忆管理 | ✅ | 保留 |
| `web_search` | 网页搜索 | ✅ | 保留 |
| `agency_orchestrator` | 工作流引擎（174角色） | ✅ | **v2.x 精简至 5-10 个核心角色** |
| `auto_developer` | 自动开发流水线 | ✅ | 个人场景可禁用 |

> **架构师建议**：v1.x 聚焦核心差异化（闭环引擎 + MCP），agency_orchestrator 等复杂功能移至 v2.x。

### 1.5 不包含的功能（v1.x 范围外）

| 功能 | 原计划 | 调整建议 | 原因 |
|------|--------|----------|------|
| 技能市场 | v2.x | 移至 v3.x | 生态建设需要社区基础 |
| 分布式部署 | v2.x | 移至 v2.x 后期 | 企业需求优先级较低 |
| 图形化编排界面 | 远期 | 删除 | 与极简定位冲突 |
| Dialect 编程语言 | 远期 | **删除** | 复杂度不匹配单人维护 |
| Soul 文件系统 | v2.x | 移至 v2.x | MCP 文件系统优先级更高 |
| 9 个中间件 | v2.x | **精简至 3-4 个核心** | 单人维护边界 |

- 技能市场、分布式部署（v2.x）
- 图形化编排界面
- 第三方技能商店（远期）

---

## 2. 用户场景与验收标准

### 2.1 用户故事

**故事1（开发者）：创建一个自愈 Agent**
> 作为开发者，我希望用几行代码创建一个 Agent，并让它自动处理测试失败。例如，当 `test_runner` 失败时，Agent 应调用 `error_knowledge` 记录错误，并尝试用 `code_writer` 修复。

**验收标准**：
- 提供示例脚本，展示 Agent 创建和闭环配置。
- 模拟测试失败，验证闭环自动触发且修复成功率 ≥ 70%。

**故事2（运维）：定义健康恢复闭环**
> 作为 SRE，我希望通过 YAML 定义闭环：当 CPU 过高时，执行 `health_monitor` → `maintenance` → 通知。

**验收标准**：
- 支持 `closed_loops.yaml` 配置，包含条件分支和重试。
- 模拟健康下降，验证闭环执行且日志记录完整。

**故事3（用户）：通过命令行使用 Agent**
> 作为用户，我希望在终端输入 `plector --query "帮我写个爬虫"`，Agent 能自动生成代码并测试。

**验收标准**：
- 命令执行后，返回可运行的代码或错误信息。
- 技能调用链可观测（日志记录）。

**故事4（贡献者）：添加一个新技能**
> 作为社区贡献者，我希望通过编写 `skill.json` 和 `implementation.py` 就能创建一个新技能，系统自动检测其依赖、事件声明，并纳入健康监控。

**验收标准**：
- 提供脚手架命令 `plector new-skill <name>` 生成模板。
- 新技能注册后，`skill_registry` 能正确加载元数据，且依赖检测通过。

**故事5（贡献者）：添加一个新工具**
> 作为开发者，我希望用 `@tool` 装饰器标记一个普通 Python 函数，就能让 Agent 调用它，无需编写 `skill.json` 或处理事件。

**验收标准**：
- 工具函数自动生成 JSON Schema，被 LLM 识别。
- 工具调用失败不影响 Agent 主循环。

### 2.2 关键验收指标

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| 核心代码量 | < 5000 行 | ✅ < 5000 行 |
| 核心技能数量 | ≤ 15 个 | ✅ 11 个 |
| 单元测试覆盖率 | ≥ 80% | 🔄 进行中 |
| 闭环自动修复成功率 | ≥ 70% | 🔄 进行中 |
| 单次 Agent 循环延迟（无工具） | < 100ms | ✅ < 50ms |
| 事件分发延迟 | < 10ms | ✅ < 5ms |

---

## 3. 产品架构

### 3.1 当前架构（v1.x）

```
┌─────────────────────────────────────────────────────────────────┐
│                          接入层                                   │
│   CLI  │  WebSocket  │  Dashboard (Vue3 SPA)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        消息总线（EventBus）                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     核心循环（Agent Loop）                        │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │ 上下文构建器  │→│   LLM 决策   │→│  工具执行    │          │
│   └──────────────┘  └──────────────┘  └──────────────┘          │
│          ↑                │                │                     │
│          └────────────────┴────────────────┘                     │
│                        事件总线                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     技能与工具层（分层）                          │
│   ┌──────────────────────────┐  ┌──────────────────────────┐    │
│   │      核心技能（11个）     │  │      工具函数（48个）    │    │
│   │  - 参与治理                │  │  - 不参与治理             │    │
│   │  - skill.json 元数据       │  │  - @tool 装饰器          │    │
│   └──────────────────────────┘  └──────────────────────────┘    │
│                    技能治理（健康分、淘汰）                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        闭环引擎                                   │
│   (条件图解析与执行，事件驱动自愈流程)                             │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 目标架构（v2.x）- 演进方向

```
┌─────────────────────────────────────────────────────────────────┐
│  渠道网关层 (ChannelGateway) - 多渠道适配                         │
│  WebSocket + Telegram + Discord + 钉钉/飞书                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  中间件链 (MiddlewareChain)                                      │
│  ThreadData → Memory → Summarization → Security → Audit        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  多智能体层 (MultiAgent)                                         │
│  工作区隔离 + 优先级路由 + 子代理池                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  核心层 (Core)                                                  │
│  Agent Loop + Event Bus + Skill Registry + Closure Engine      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 技能与工具的具体差异

| 特性 | 技能（Skill） | 工具（Tool） |
|------|--------------|--------------|
| 元数据 | `skill.json`（名称、描述、事件、依赖、tier） | 无，仅函数签名 |
| 注册方式 | 扫描 `skills/` 目录，自动加载 | `@tool` 装饰器，手动或自动扫描 `tools/` |
| 生命周期 | `post_construct` / `pre_destroy` | 无 |
| 事件 | 可发布/订阅事件 | 不能发布/订阅事件 |
| 依赖 | 可依赖其他技能 | 无依赖 |
| 治理 | 健康分监控、依赖检测、自动淘汰 | 无治理 |
| 调用方式 | `skill_handler.execute(name, method, params)` | 直接函数调用（由 Agent Loop 执行） |

### 3.4 核心模块需求

- **自主决策循环（Agent Loop）**：必须实现标准的推理-行动-观察循环，支持基于 Function Calling 的工具调用。
- **工具调用**：必须支持通过 `@tool` 装饰器将普通 Python 函数暴露为 LLM 可调用的工具。
- **事件总线**：必须提供异步发布/订阅能力，支持事件驱动解耦。
- **技能系统**：必须支持技能注册、元数据管理、生命周期回调。
- **闭环引擎**：必须能够解析 `closed_loops.yaml` 条件图，并按定义执行自愈流程。
- **技能治理**：必须实现技能健康分计算、依赖检测和自动淘汰机制。
- **上下文构建器**：必须能从 `AGENTS.md`, `SOUL.md`, `USER.md` 等文件动态构建系统提示词。
- **接入渠道**：至少提供 CLI 渠道，WebSocket 和 HTTP API 作为可选增强。

---

## 4. 数据模型与接口

### 4.1 skill.json 结构

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "tier": "tier_1_system",
  "version": "1.0.0",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": [],
  "methods": {
    "check_health": {
      "description": "执行健康检查",
      "params": {},
      "returns": {"cpu": "float", "memory": "float", "status": "string"}
    }
  }
}
```

### 4.2 closed_loops.yaml 结构

```yaml
health_degraded_loop:
  trigger_on: ["health.degraded"]
  entry: "diagnose"
  max_iterations: 5
  nodes:
    diagnose:
      type: "skill"
      skill: "health_monitor"
      method: "diagnose"
      next: "repair"
    repair:
      type: "skill"
      skill: "maintenance"
      method: "fix"
      next: "verify"
    verify:
      type: "condition"
      skill: "health_monitor"
      method: "check"
      transitions:
        healthy: "success_end"
        degraded: "diagnose"
    success_end:
      type: "end"
```

---

## 5. 非功能需求

| 类别 | 要求 | 当前状态 |
|------|------|----------|
| **性能** | 单次 Agent 循环（无工具）< 100ms；事件分发 < 10ms | ✅ 已满足 |
| **可靠性** | 闭环修复成功率 ≥ 70%；技能调用失败有重试和降级 | 🔄 进行中 |
| **安全性** | 工具沙箱（禁止危险系统调用）；Shell 工具需用户确认 | ✅ 已实现 |
| **可观测性** | 结构化日志（JSON Lines）记录技能调用、事件、闭环执行 | ✅ 已实现 |
| **可维护性** | 核心代码 < 5000 行；核心技能 ≤ 15 个；单元测试覆盖率 ≥ 80% | ✅/🔄 部分满足 |
| **易用性** | 安装后 5 分钟内可运行第一个示例 | ✅ 已实现 |

---

## 6. 版本规划

| 版本 | 功能 | 状态 |
|------|------|------|
| **v1.0** | 核心引擎 + CLI + 11 个技能 + 59 个工具 | ✅ 已完成 |
| **v1.1** | MCP Client + HTTP+SSE 传输 | ✅ 已完成 |
| **v1.2** | WebSocket + Vue3 SPA + Dashboard | ✅ 已完成 |
| **v1.3** | agency_orchestrator + 174 个角色 | ✅ 已完成 |
| **v1.4** | 技能热更新 + Skill 格式规范 | 🔄 进行中 |
| **v2.0** | 中间件架构 + FTS5 + 多智能体 | 📅 规划中 |

---

## 7. 验收测试计划

### 7.1 单元测试

- 覆盖核心模块：事件总线、技能注册表、闭环解析、工具注册。
- 目标覆盖率 ≥ 80%。

### 7.2 集成测试

- 模拟真实闭环：注入 `test.failed` 事件，验证 `error_knowledge` 和 `code_writer` 被调用。
- 模拟健康下降：触发 `health.degraded`，验证闭环执行。

### 7.3 性能测试

- 压力测试：100 并发请求，测量平均延迟和错误率。
- 闭环执行耗时：记录复杂闭环（5 个节点）的完成时间。

### 7.4 用户验收测试

- 提供示例项目（如"自动修复测试失败"），由外部开发者试用并反馈。

---

## 8. 风险与应对

| 风险 | 应对措施 |
|------|----------|
| 闭环引擎过于复杂，难以调试 | 提供可视化工具（生成 Mermaid 流程图） |
| 技能治理可能导致误淘汰 | 提供"黑名单"机制，允许用户豁免特定技能 |
| 事件总线性能瓶颈 | 支持可插拔后端（Redis、Kafka） |
| 开发者混淆技能与工具 | 提供清晰的文档和脚手架命令，在模板中明确区分；技能与工具的判断标准以"是否参与治理"为准 |

---

## 9. 附录

### 9.1 术语表

- **ReAct**：Reasoning + Acting，推理-行动范式。
- **Function Calling**：LLM 原生工具调用接口。
- **技能（Skill）**：需要治理的功能模块，数量严格限制（≤15）。
- **工具（Tool）**：不需要治理的纯函数，数量不限。
- **闭环（Closure）**：事件驱动的自愈流程。
- **条件图**：定义闭环节点和分支的图结构。
- **中间件（Middleware）**：请求/响应处理链，用于扩展核心功能。

### 9.2 参考资料

- [NanoBot](https://github.com/HKUDS/NanoBot)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Hermes Agent](https://github.com/qhun1028/hermes-agent) - 多终端后端、FTS5 搜索
- [DeerFlow](https://github.com/deerflow-dev/deerflow) - 中间件链、子代理池
- [OpenClaw](https://github.com/nicepav/nicepav.github.io) - 多智能体隔离
- [Lobe Chat](https://github.com/lobehub/lobe-chat) - AI 前端框架参考
- [CrewAI](https://github.com/crewAI/crewAI) - 角色化团队协作
- [Dify](https://github.com/langgenius/dify) - 开源 AI 应用开发平台

### 9.3 开源竞品架构分析

#### 9.3.1 NanoBot 架构亮点（借鉴优先级：P0）

| 设计模式 | 说明 | 对 Plector 的借鉴 |
|----------|------|------------------|
| **MessageBus 解耦** | asyncio.Queue 解耦渠道与核心 | 引入消息总线解耦架构 |
| **AgentHook 生命周期** | 灵活的扩展钩子 | 增强生命周期扩展性 |
| **AgentRunner 可复用** | 与产品层解耦的执行器 | 支持单次和批量执行 |
| **Dream 两阶段记忆** | 语义压缩 + 工具调用更新 | 智能上下文管理 |
| **SubagentManager** | 隔离工作空间 + 并行执行 | 后台任务并行处理 |

#### 9.3.2 Hermes Agent 架构亮点（借鉴优先级：P1）

| 设计模式 | 说明 | 对 Plector 的借鉴 |
|----------|------|------------------|
| **多终端后端抽象** | Local/Docker/SSH/Modal 等 | 多执行环境支持 |
| **FTS5 全文搜索** | 跨会话记忆召回 | 增强记忆系统 |
| **Skills Hub 集成** | 兼容 agentskills.io | 技能市场生态 |

#### 9.3.3 DeerFlow 架构亮点（借鉴优先级：P1）

| 设计模式 | 说明 | 对 Plector 的借鉴 |
|----------|------|------------------|
| **LangGraph 集成** | 基于图的 Agent 编排 | 状态机增强选项 |
| **Sandbox 隔离** | 隔离的文件系统 | 安全沙箱支持 |
| **子代理池** | 专业子代理并行执行 | 并行任务管理 |
| **上下文压缩** | Token 预算 + LLM 摘要 | 记忆压缩策略 |

#### 9.3.4 架构演进路线图

```
Phase 1（短期）：稳固核心
├── MessageBus 解耦
├── AgentHook 扩展系统
└── Provider 抽象（多 LLM 后端）

Phase 2（中期）：提升智能
├── Dream 两阶段记忆压缩
├── FTS5 全文搜索索引
└── SubagentManager 并行执行

Phase 3（长期）：扩展能力
├── 多终端后端支持
├── LangGraph 状态机（可选）
└── Skills Hub 生态集成
```

### 9.4 技术研究员 Agent 研究成果

#### 9.4.1 AI Agent 框架 2024-2025 趋势

| 趋势类别 | 具体表现 |
|----------|----------|
| **Human-in-the-Loop 增强** | Agent 越来越多地融入人在回路机制 |
| **多智能体协作成熟** | 从单 Agent 向多 Agent 系统演进 |
| **自主性与安全平衡** | 提升自主能力的同时强化护栏机制 |
| **小型专用模型应用** | 小型语言模型构建轻量级 Agent |

#### 9.4.2 多智能体架构模式（Google 识别的 8 种核心模式）

| 模式 | 复杂度 | 适用场景 |
|------|--------|----------|
| **Orchestrator-Worker** | 中 | 并行分析、多数据源采集 |
| **Supervisor Routing** | 高 | 动态路由、分层监督 |
| **Sequential Chain** | 低 | 流程任务、顺序处理 |
| **Parallel Execution** | 低 | 独立任务、并行执行 |
| **Reflection** | 中 | 自我反思、质量保证 |
| **Hierarchical Teams** | 高 | 分层协作、复杂组织 |

#### 9.4.3 自我修复 AI Agent 三阶段

| 阶段 | 核心功能 | 实现要点 |
|------|----------|----------|
| **诊断** | 事件分类、严重程度评估、智能升级 | 结构化日志 + 知识库关联 |
| **修复** | 方案匹配、自动化执行、回退策略 | 变更前快照 + 原子化操作 |
| **学习** | 事件后分析、知识沉淀、模式识别 | 因果记忆 + 跨 Agent 共享 |

### 9.5 前端设计方案

#### 9.3.1 功能模块优先级

| 优先级 | 功能模块 | 说明 | 状态 |
|--------|----------|------|------|
| **P0** | 聊天交互 | Markdown 渲染、代码高亮 | 📅 规划中 |
| **P0** | 工具调用可视化 | 展示工具输入输出 | 📅 规划中 |
| **P1** | 记忆管理界面 | 查看、编辑、删除记忆 | 📅 规划中 |
| **P1** | 会话管理 | 创建/切换/删除会话 | 📅 规划中 |
| **P1** | 技能与工具列表 | 动态展示 11 个技能 | 📅 规划中 |
| **P2** | 系统状态监控 | ReAct 循环步骤 | 📅 规划中 |
| **P2** | 配置管理 | 切换 LLM 后端 | 📅 规划中 |

#### 9.3.2 技术选型

**推荐方案：Vue 3 + Vite + TypeScript + Tailwind CSS**

| 组件 | 选项 | 推荐 |
|------|------|------|
| **框架** | Vue 3 / React | Vue 3（简化） |
| **构建** | Vite | Vite |
| **样式** | Tailwind CSS | Tailwind CSS |
| **Markdown** | markdown-it + highlight.js | markdown-it + highlight.js |
| **图标** | Lucide React/Vue | Lucide |
| **HTTP 客户端** | fetch / axios | fetch（简化） |

#### 9.3.3 Lobe Chat 集成路线图

**阶段一：基础部署**
- 克隆 Lobe Chat 仓库
- 使用 `pnpm dev` 本地运行
- 部署到 Vercel

**阶段二：WebSocket 适配**

| 方案 | 描述 | 复杂度 |
|------|------|--------|
| **方案 A：独立前端** | 纯原生实现，通过 WebSocket 连接 Plector | 中（完全控制） |
| **方案 B：集成 Lobe Chat** | 在 Lobe Chat 侧添加 Plector Provider | 高（需要插件开发） |

**阶段三：插件开发 + UI 定制**
- 扩展 Agent 相关接口
- 实现 Function Calling 可视化
- 展示 ReAct 循环步骤

#### 9.3.4 WebSocket 消息协议

```typescript
export interface PlectorMessage {
  type: 'user_message' | 'agent_start' | 'text_delta' | 'tool_call' | 'agent_end';
  content?: string;
  tool?: string;
  input?: any;
  output?: any;
  session_id?: string;
}
```

---

## 10. 记忆系统增强设计

### 10.1 艾宾浩斯遗忘曲线遗忘机制

**核心思想**："对 AI 来说，时间 = 对话轮次，不是日历时间"

**强度计算公式**：
```
strength = e^(-turns_ago / adjusted_stability)
adjusted_stability = stability × (1 + log(1 + access_count))
```

**稳定性等级**：

| 值 | 含义 | 应用场景 |
|----|------|---------|
| 5 | 临时 | 对话记录 |
| 10 | 默认 | 普通知识 |
| 30 | 重要 | 关键知识 |
| 50 | 核心 | 用户偏好 |

**强度等级阈值**：

| 阈值 | 等级 |
|------|------|
| >= 0.8 | alive (鲜活) |
| >= 0.5 | normal (正常) |
| >= 0.2 | fading (衰退) |
| < 0.05 | forgotten (遗忘) |

### 10.2 联想式记忆网络设计

**8 种联想模式**：

| 模式 | 触发时机 | 调 LLM | 说明 |
|------|---------|--------|------|
| 语义相似 | 每次检索 | 否 | ChromaDB 向量检索 |
| 触景生情 | 每次检索 | 否 | 关键词触发 |
| 触类旁通 | 检索时 | 否 | 关联概念扩展 |
| 时序联想 | 检索时 | 否 | 附近轮次记忆 |
| 温故知新 | 每50轮 | 是 | LLM 重新理解旧记忆 |
| 举一反三 | 存储时 | 是 | LLM 生成适用场景 |
| 推陈出新 | 用户请求时 | 是 | LLM 融合生成新方案 |
| 恍然大悟 | 存储时 | 是 | 矛盾检测 |

**联想权重配置**：
```python
SOURCE_WEIGHTS = {
    "semantic": 0.4,      # 语义相似
    "trigger": 0.3,       # 触景生情
    "association": 0.2,   # 触类旁通
    "temporal": 0.15,     # 时序联想
    "review": 0.1,       # 温故知新
}
```

### 10.3 记忆优先级计算

**综合分数公式**：
```
combined_score = source_score × (0.3 + 0.7 × strength)
```

---

## 11. 错误处理与自愈机制

### 11.1 AI Agent 特有错误类型

| 类型 | 特征 | 示例 | 处理策略 |
|------|------|------|----------|
| **结构错误** | 确定性、格式问题 | JSON 破损、参数缺失 | Pydantic 严格验证，不重试 |
| **运行时错误** | 非确定性、外部依赖 | API 超时、限流(429)、服务不可用(503) | 指数退避 + 重试 |
| **逻辑错误** | 非确定性、语义问题 | 幻觉、引用不存在资源 | 验证 + 反馈循环，不重试 |

### 11.2 自愈流程

```
错误检测 → 错误分类 → 反馈生成 → 代理重新规划 → 验证循环
```

### 11.3 重试策略

| 错误类型 | 可重试 | 最大重试 | 退避策略 |
|----------|--------|----------|----------|
| 网络超时 | 是 | 3-5 | 指数 |
| 429 限流 | 是 | 3 | 线性到上限 |
| 500 服务错误 | 是 | 2-3 | 指数 |
| 格式错误 | 否 | 0 | - |
| 逻辑错误/幻觉 | 否 | 0 | - |

---

## 12. 技能与架构增强

### 12.1 SKILL.md 技能格式规范

**必需字段**：
- Description：简短描述
- Triggers：触发词列表
- Actions：动作定义

**可选字段**：
- Examples、Constraints、Dependencies、Configuration、Notes、Metadata

### 12.2 LangGraph 状态机集成

**状态模式设计**：
```python
class PlectorState(TypedDict):
    messages: Annotated[list, add_messages]
    current_tool: str | None
    tool_results: Annotated[list, add_tool_results]
    context: dict
    metadata: dict
```

### 12.3 中间件链架构

```
执行顺序：Logging → Security → Governance → Memory → SkillChain
```

**内置中间件**：

| 中间件 | 功能 | 优先级 |
|--------|------|--------|
| **LoggingMiddleware** | 请求/响应日志 | P0 |
| **SecurityMiddleware** | 输入验证 | P0 |
| **GovernanceMiddleware** | 技能健康分监控 | P1 |
| **MemoryMiddleware** | 结果自动记忆 | P1 |
| **SkillChainMiddleware** | 技能联动触发 | P1 |

### 12.4 个人场景精简配置

**核心设计思想**：对个人 agent 助手场景，精简非必需模块，提升系统启动速度和运行效率。

**可禁用的功能**：

| 功能 | 复杂度 | 问题 | 建议 |
|------|--------|------|------|
| `agency_orchestrator` | 174个AI角色、DAG并行 | 启动延迟、配置复杂 | `enabled: false` |
| `auto_developer` | 自动开发流水线 | 面向团队，个人场景不需要 | 可选禁用 |
| `self_improver` | meta自我改进 | 自我修改代码有风险 | 暂时禁用 |
| `file_utils` | 文件操作工具 | 与MCP filesystem重复 | 禁用，使用MCP替代 |

**推荐保留的 Skills（7个）**：

| Skill | 用途 | 优先级 |
|-------|------|--------|
| `context_refresher` | 防止长对话遗忘 | P0 |
| `memory` | 记忆系统 | P0 |
| `health_monitor` | 健康检查 | P1 |
| `code_writer` | 代码编写 | P1 |
| `test_runner` | 测试运行 | P1 |
| `web_search` | 网络搜索 | P1 |
| `error_knowledge` | 错误记录 | P2 |

### 12.5 闭环系统实现细节

**核心组件**：

| 组件 | 文件 | 机制 |
|------|------|------|
| **ClosureEngine** | `core/closure_engine.py` | YAML 声明式配置 |
| **EventBus** | `core/event_bus_v2.py` | CloudEvents 1.0 格式 |
| **context_refresher** | `skills/context_refresher/` | GSDContext 数据结构 |

**事件发布点**：

| 事件 | 发布位置 |
|------|----------|
| `error.stored` | skills/error_knowledge |
| `health.{status}` | skills/health_monitor |
| `memory.stored` | skills/memory |
| `context.preserved` | drive_plector_core.py |
| `code.written` | skills/code_writer |

**GSDContext 数据结构**：
```python
@dataclass
class GSDContext:
    session_id: str        # 会话ID
    goal: str = ""         # 初始目标
    constraints: list[str] = []   # 约束条件
    completed: list[str] = []     # 已完成项
    in_progress: list[str] = []   # 进行中项
    turn_count: int = 0          # 轮次计数
    last_refresh: float = 0.0    # 上次保鲜时间
```

### 12.6 Critical 断点修复

| 断点 | 严重度 | 问题 | 修复方案 |
|------|--------|------|---------|
| **#1** | Critical | `recommended_actions` 返回后未执行 | 实现 `_execute_recommended_actions()` |
| **#2** | Critical | `context_refresher` 未集成 | 实现每 N 轮自动保鲜 |
| **#3** | High | ClosureEngine 事件缺失 | 添加 `closure_loop.completed/failed` |
| **#4** | High | Governance 未集成 | GovernanceMiddleware |
| **#5** | Medium | 工具结果未保存记忆 | MemoryMiddleware |

---

## 13. 多智能体框架对比

### 13.1 三大主流框架定位

| 框架 | 核心定位 | 主要优势 | 适用场景 |
|------|---------|---------|---------|
| **LangChain** | 全能型 AI 应用框架 | 600+ 集成、LCEL 表达式链、LangGraph 状态图 | 金融/医疗合规、复杂 RAG、企业级集成 |
| **CrewAI** | 多智能体协作平台 | 角色驱动、直观易用、A2A 协议 | 团队协作流程、医疗诊断、内容创作 |
| **AutoGen** | 会话式多代理 | 无代码 Studio、GroupChat、微软生态 | 快速原型、代码审查、数据分析 |

### 13.2 Plector agency-orchestrator 定位

**差异化优势**：
- 174 个预定义角色 - 开箱即用
- 断点续跑机制 - 长任务不怕中断
- MCP 原生集成 - 连接外部工具
- YAML 声明式工作流 - 易于版本控制
- DAG 并行执行 - 自动检测可并行步骤

### 13.3 PRD v1.5 补充内容

#### 13.3.1 性能优化建议

**向量搜索优化**：
- 批量索引：减少 API 调用次数
- HNSW 参数：`ef_construction=200`, `ef_search=100`, `M=16`
- 量化：`bits=8` 量化，采样率 10%

**LLM 调用优化**：
- 请求批处理：最大批次 10，请求等待 500ms
- 模型降级策略：`gpt-4-turbo` → `gpt-3.5-turbo` → `claude-3-haiku`

#### 13.3.2 数据库 Schema（补充）

```sql
-- memories 表（核心）
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    session_id TEXT,
    conversation_id TEXT,
    content TEXT NOT NULL,
    memory_type TEXT NOT NULL,  -- 'fact', 'preference', 'context', 'summary'
    intensity REAL DEFAULT 1.0,  -- 艾宾浩斯强度
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tenant (tenant_id),
    INDEX idx_type (memory_type)
);

-- FTS5 全文索引
CREATE VIRTUAL TABLE memories_fts USING fts5(content, tokenize='unicode61');
```

#### 13.3.3 API 端点（补充）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/sessions` | GET | 列出会话 |
| `/api/v1/memories` | GET/POST | 搜索/创建记忆 |
| `/api/v1/skills` | GET | 列出技能 |
| `/api/v1/admin/stats` | GET | 系统统计 |

#### 13.3.4 已知问题清单

| 框架 | 问题 | 严重度 | 临时解决方案 |
|------|------|--------|-------------|
| **Hermes** | MCP 断开不自动重连 | 中 | 手动重启 |
| **DeerFlow** | 子代理超时状态不一致 | 高 | 手动清理 threads |
| **Plector** | 技能热更新有时失效 | 高 | 重启服务 |
| **Plector** | 向量搜索延迟高 | 中 | 优化索引参数 |

#### 13.3.5 实施优先级细分

| 阶段 | 任务 | 来源 | 工作量 |
|------|------|------|--------|
| **P0** | 技能热更新修复 | Hermes | 3天 |
| **P0** | MCP 重连机制 | Hermes | 2天 |
| **P1** | FTS5 全文索引 | Hermes | 5天 |
| **P1** | LLM 记忆提取 | DeerFlow | 4天 |
| **P2** | 中间件架构改造 | DeerFlow | 5天 |
| **P2** | 子代理并行执行 | DeerFlow | 4天 |
| **P3** | RBAC 权限系统 | 新增 | 4天 |

---

**文档状态**: 已定稿
**版本历史**：
- v1.6：五角色 Agent 审查结论整合（架构师范围精简、安全合规官 OTel P0 升级、产品经理量化指标、增长顾问 MCP 生态、运维 OTel MVP 实现）
- v1.5：新增记忆系统增强（艾宾浩斯遗忘曲线、联想式记忆）、错误处理与自愈机制、技能与架构增强（LangGraph、中间件链）、多智能体框架对比、个人场景精简、闭环系统实现细节、数据库 Schema/API 规范补充
- v1.4：新增开源竞品架构分析（NanoBot/Hermes/DeerFlow），添加技术研究员 Agent 研究成果，更新竞品参考
- v1.3：添加架构增强路线图（v2.x 演进方向），更新功能状态
- v1.2：明确技能/工具区分标准，移出技术设计细节
- v1.1：初始版本

---

## 14. 安全治理详细设计

### 14.1 安全中间件实现

```python
class SecurityMiddleware(AgentMiddleware):
    """输入验证 + 权限检查"""

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 输入清理
        ctx.messages = self.sanitize_input(ctx.messages)

        # 2. 权限检查
        if not self.check_permissions(ctx):
            raise PermissionDeniedError()

        # 3. 继续处理
        return await next_handler()

class AuditMiddleware(AgentMiddleware):
    """不可篡改审计日志"""

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        result = await next_handler()

        # 写入不可篡改日志（WORM）
        await self.audit_log.append({
            "timestamp": time.time(),
            "user_id": ctx.user_id,
            "session_id": ctx.session_id,
            "action": "agent.execute",
            "result": "success" if result else "failure"
        })

        return result
```

### 14.2 OpenTelemetry 可观测性

| 可观测性维度 | 实现方式 | 企业集成 |
|-------------|----------|----------|
| **Traces** | 分布式链路追踪 | Jaeger/Zipkin |
| **Metrics** | Counter/Gauge/Histogram | Prometheus/Grafana |
| **Logs** | 结构化 JSON Lines | ELK/Loki |
| **Spans** | 技能执行时长、工具调用延迟 | 链路可视化 |

---

## 15. 开源治理与社区建设需求

### 15.1 贡献者文档清单

| 文档 | 内容 | 优先级 |
|------|------|--------|
| **CONTRIBUTING.md** | 贡献流程、代码规范、PR 模板 | P0 |
| **CODE_OF_CONDUCT.md** | 社区行为准则 | P0 |
| **SECURITY.md** | 安全漏洞报告流程 | P0 |
| **CHANGELOG.md** | 版本变更记录 | P0 |
| **Why Plector?** | 与竞品对比文档 | P1 |

### 15.2 版本发布生命周期

| 阶段 | 说明 | 工具 |
|------|------|------|
| **Alpha** | 内部测试，功能不稳定 | - |
| **Beta** | 公开测试，欢迎反馈 | GitHub Releases |
| **RC** | 候选发布，准备生产 | Tagging |
| **GA** | 正式发布，生产可用 | GitHub Releases + PyPI |

---

## 16. Why Plector 对比文档规划

### 16.1 对比维度

| 维度 | LangGraph | CrewAI | Dify | **Plector** |
|------|-----------|--------|------|--------------|
| **定位** | 企业级复杂工作流 | 多智能体协作 | 低代码全家桶 | **轻量级企业底座** |
| **学习曲线** | 陡峭（2-3周） | 平缓（数小时） | 中等 | **最平缓（5分钟）** |
| **代码量** | 数万行 | ~10K | ~50K | **< 5000 行** |
| **安全治理** | ❌ | ✅ 企业版 | ✅ | **✅ 原生** |
| **可观测性** | 部分 | 部分 | ✅ | **✅ OpenTelemetry** |
| **中间件架构** | ✅ | ❌ | 部分 | **✅ 原生** |
| **MCP 支持** | 部分 | 部分 | ✅ | **✅ 原生** |

### 16.2 差异化卖点

| 卖点 | 说明 |
|------|------|
| **极简上手** | 5 分钟内运行第一个示例 |
| **企业安全** | 原生安全中间件 + 审计日志 |
| **可观测性** | OpenTelemetry 标准输出 |
| **开放架构** | 插件化设计，定制灵活 |
| **可治理** | 技能健康分 + 闭环自愈 |
