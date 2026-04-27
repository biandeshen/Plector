# Plector 产品需求文档（PRD）v1.7

**版本**: 1.7
**状态**: 待审核
**关联 BRD**: 2.1
**日期**: 2026-04-27

---

## 1. 功能范围（MoSCoW）

| 优先级 | 功能模块 | 说明 | 状态 |
|--------|----------|------|------|
| **Must** | 自主决策循环（ReAct） | Agent 核心推理-行动-观察循环 | ✅ 已完成 |
| **Must** | 工具调用（Function Calling） | 稳定的工具注册与调用机制 | ✅ 已完成 |
| **Must** | 事件总线 | 异步发布/订阅，解耦技能与闭环 | ✅ 已完成 |
| **Must** | 技能注册表与执行器 | 管理技能元数据和调用 | ✅ 已完成 |
| **Must** | 闭环引擎 | 事件驱动的自愈流程 | ✅ 已完成 |
| **Must** | CLI 接入渠道 | 命令行交互 | ✅ 已完成 |
| **Must** | MCP Client | 连接外部 MCP Server | ✅ 已完成 |
| **Should** | 技能治理 | 技能健康监控与自动淘汰 | 🔄 进行中 |
| **Should** | WebSocket 渠道 | 实时双向通信 | ✅ 已完成 |
| **Should** | 技能热更新 | 文件哈希检测，自动重载 | 🔄 进行中 |
| **Could** | OpenTelemetry 集成 | 标准链路追踪输出 | 📅 规划中 |
| **Could** | 审计日志中间件 | 不可篡改操作日志 | 📅 规划中 |
| **Could** | HTTP API | RESTful 接口 | 📅 规划中 |

---

## 2. 核心用户故事

### 故事1：开发者创建自愈 Agent

> 作为开发者，我希望用几行代码创建一个 Agent，让它自动处理测试失败。当 `test_runner` 失败时，Agent 应调用 `error_knowledge` 记录错误，并尝试用 `code_writer` 修复。

**验收标准**：
- 提供示例脚本，展示 Agent 创建和闭环配置
- 模拟测试失败，验证闭环自动触发且修复成功率 ≥ 70%

### 故事2：运维定义健康恢复闭环

> 作为 SRE，我希望通过 YAML 定义闭环：当 CPU 过高时，执行 `health_monitor` → `maintenance` → 通知。

**验收标准**：
- 支持 `closed_loops.yaml` 配置
- 模拟健康下降，验证闭环执行且日志完整

### 故事3：用户 5 分钟内运行第一个 Agent

> 作为用户，我希望在终端输入 `plector --query "帮我写个爬虫"`，Agent 能自动生成代码并测试。

**验收标准**：
- 命令执行后，返回可运行的代码或错误信息
- 技能调用链可观测（日志记录）

---

## 3. 技术架构（v1.x）

```
┌──────────────────────────────────────┐
│  接入层                               │
│  CLI  │  WebSocket                  │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│  核心循环（Agent Loop）               │
│  上下文构建 → LLM 决策 → 工具执行    │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│  事件总线（EventBus）                │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│  技能层（≤15）+ 工具层（无限制）     │
└──────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│  闭环引擎（条件图执行）              │
└──────────────────────────────────────┘
```

**技能与工具区分**：

| 类型 | 定义 | 治理 | 数量 |
|------|------|------|------|
| 技能 | 需要治理的功能模块 | 完整治理 | ≤ 15 个 |
| 工具 | 不需要治理的纯函数 | 无 | 无限制 |

**当前核心技能（11个）**：

1. `health_monitor` – 系统健康检查
2. `error_knowledge` – 错误记录与分类
3. `context_refresher` – 上下文保鲜
4. `self_improver` – 自我改进
5. `code_writer` – 代码生成
6. `test_runner` – 测试执行
7. `file_utils` – 文件操作
8. `memory` – 记忆管理
9. `web_search` – 网页搜索
10. `agency_orchestrator` – 工作流引擎
11. `auto_developer` – 自动开发流水线

---

## 4. 数据模型

### skill.json 结构

```json
{
  "name": "health_monitor",
  "description": "获取系统健康状态",
  "tier": "tier_1_system",
  "version": "1.0.0",
  "dependencies": [],
  "events_produced": ["health.degraded", "health.recovered"],
  "events_consumed": []
}
```

### closed_loops.yaml 结构

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
```

---

## 5. 发布计划

| 版本 | 功能 | 状态 |
|------|------|------|
| v1.0 | 核心引擎 + CLI + 11 技能 | ✅ 已完成 |
| v1.1 | MCP Client + WebSocket | ✅ 已完成 |
| v1.2 | Vue3 前端 + Dashboard | ✅ 已完成 |
| v1.3 | agency_orchestrator + 174 角色 | ✅ 已完成 |
| v1.4 | 技能热更新 + Skill 格式规范 | 🔄 进行中 |
| v1.5 | 技能治理 + 闭环自愈 | 🔄 进行中 |
| v2.0 | OTel 可观测性 + 审计日志 | 📅 规划中 |

---

## 6. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 技能治理过于复杂，用户不愿使用 | 中 | 提供默认治理策略，允许关闭 |
| 闭环修复失败导致事故扩大 | 高 | 人工通知 + 保留现场 |
| 事件总线性能瓶颈 | 中 | 支持 Redis 后端 |

---

## 7. 非功能需求

| 类别 | 要求 | 状态 |
|------|------|------|
| 性能 | Agent 循环 < 100ms，事件分发 < 10ms | ✅ |
| 可靠性 | 闭环修复成功率 ≥ 70% | 🔄 |
| 安全性 | 工具沙箱 + 用户确认 | ✅ |
| 可观测性 | 结构化日志（JSON Lines） | ✅ |
| 易用性 | 5 分钟内可运行第一个示例 | ✅ |

---

## 8. 验收测试计划

### 单元测试
- 覆盖核心模块：事件总线、技能注册表、闭环解析、工具注册
- 目标覆盖率 ≥ 80%

### 集成测试
- 模拟 `test.failed` 事件，验证 `error_knowledge` + `code_writer` 闭环
- 模拟 `health.degraded`，验证闭环执行

### 性能测试
- 100 并发请求，测量平均延迟和错误率
