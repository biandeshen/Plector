---
tags:
  - v2.0
  - upgrade
  - integration
  - architecture
  - security
type: upgrade-plan
created: 2026-04-15
related-to:
  - [[72_系统审查与改进方案]]
  - [[73_AI工具链整合方案]]
  - [[41_v2.x_MiniMax集成]]
  - [[79_v2.x_流式响应-工具可视化实现方案]]
---

# Plector v2.0 升级方案 — 整合版

> 原始文档：`E:\产品\Plector\docs\reports\upgrade_plan_v2.0.md`（2025-12-19）
> 整合补充：AI 工具链整合方案（[[73_AI工具链整合方案]]）
> 审查修复：P0-P3 共 23 项问题（[[72_系统审查与改进方案]]）
> 整合日期：2026-04-15

关联：[[72_系统审查与改进方案]] | [[73_AI工具链整合方案]] | [[79_v2.x_流式响应-工具可视化实现方案]]

---

## 一、当前系统状态（2026-04-15 审查后）

### 已解决问题（P0-P3 全部清零）

| 提交 | 内容 |
|------|------|
| `54a4fb4` | P0-1~4：test_runner shell注入、web_search SSRF、code_writer路径穿越、.env泄露 |
| `df70f3d` | P1-1~7：MCP重叠合并、硬编码路径参数化、stdio超时、EventBus异常、Governance实现、LLM复用、Anthropic多system |
| `68c28dd` + `d44c12d` | P2-1~8：image_handler异常返回、Schema深拷贝、file_utils os.sep、health_monitor跨平台、auto_developer跨技能import、file_utils路径检查、VALID_TIERS |
| `19fc800` | P3-1~4：测试补齐10用例、AGENT.md删除、SkillRegistry缓存失效 |
| `d5b1c47` | 删除损坏的test_minimax_search.py + pyproject.toml加no-capture |
| `3e43b53` | MiniMax LLM provider 集成（已回退，仅改.env） |

**分支**：`develop/agency-orchestrator`
**测试**：pytest 19/19 通过 ✅

### 待解决问题（来自 v2.0 原始文档）

| 类别 | 问题 | 优先级 |
|------|------|--------|
| 架构 | `agent_loop.py` 超 10k 行 | P0 |
| 架构 | `mcp_client.py` 超 15k 行 | P0 |
| 架构 | `image_handler.py` 超 20k 行 | P1 |
| 性能 | LLM 无流式响应 | P1 |
| 性能 | 事件总线内存泄漏风险 | P0 |
| 性能 | 技能冷加载延迟 | P1 |
| 安全 | 技能执行沙箱缺失 | P0 |
| 安全 | 敏感信息加密存储 | P1 |
| 可观测性 | 无 Prometheus/链路追踪 | P2 |

---

## 二、整合升级目标（v2.0 + 工具链）

在 v2.0 原目标基础上，新增 AI 工具链整合目标：

### 2.1 原有功能目标（来自 v2.0）

- [ ] 多会话并发（100+）
- [ ] LLM 流式响应
- [ ] 技能热更新（无需重启）
- [ ] 增强记忆（结构化查询）
- [ ] 审计日志

### 2.2 新增工具链目标（来自 #73）

- [ ] **GSD 上下文保鲜**：长对话不再"遗忘"初始目标
- [ ] **LangGraph 图状工作流**：替代 ReAct 线性循环，支持分支/循环/断点恢复
- [ ] **CrewAI 角色委派**：多角色任务分派与协作
- [ ] **DeerFlow 企业运行时**：沙箱 + 长期记忆 + 断点恢复

---

## 三、当前进展（持续更新）

### ✅ Phase 1：核心稳定性（已完成）

| 任务 | 产出 | 状态 |
|------|------|------|
| 统一错误处理层 | `core/error_handler.py` | ✅ |
| 事件总线内存优化 | `event_bus_v2.py` | ✅ |
| 敏感信息加密 | `core/security/secrets_manager.py` | ✅ |
| 技能沙箱基础实现 | `core/skill_sandbox.py` | ✅ |
| 单元测试补全 | `tests/` | ✅ 77 passed |
| GSD 上下文保鲜 | `skills/context_refresher/` | ✅ |

### ✅ Phase 2：性能优化（已完成）

| 任务 | 产出 | 状态 |
|------|------|------|
| LLM 流式响应支持 | `core/llm_client_v2.py` | ✅ |
| 技能热加载机制 | `core/skill_loader.py` | ✅ |
| image_handler 拆分 | `core/image/` | ✅ |
| 向量检索优化 | `core/vector_memory_v2.py` | ✅ |
| LangGraph 图状工作流 | `core/workflow_graph.py` | ✅ |
| 连接池管理 | `core/utils/connection_pool.py` | ✅ |

### 🔄 Phase 3：LLM 主动串技能（进行中）

**核心目标**：让 LLM 能主动把技能串起来，而不是写死代码逻辑。

| 任务 | 状态 |
|------|------|
| skill.json triggers 规范化 | ✅ 已在各技能实现 |
| context_refresher 复杂度分析 | ✅ 增强版已实现 |
| agency_orchestrator 多角色协作 | ✅ compose_workflow 可用 |
| **LLM 元认知规则** | ⚠️ **核心待实现** |

**核心原则（已确立）**：
- ReAct 不需要写代码，LLM 本身就在循环中
- 少写死代码，多用 YAML + LLM 驱动
- 代码只做机械性事（加载/执行/读写）
- 遇到复杂任务 → context_refresher 分析 → agency_orchestrator 编排 → 多角色协作

### ⏸️ Phase 4：可观测性（暂缓）

| 任务 | 产出 | 状态 |
|------|------|------|
| 健康检查端点 | `core/observability/` | ⏸️ 已创建，暂缓 |
| Prometheus 指标 | metrics.py | ⏸️ |
| 结构化日志 | logging.py | ⏸️ |
| 链路追踪 | tracing.py | ⏸️ |

### ⏸︎ Phase 5：企业级功能（远期）

| 任务 | 状态 |
|------|------|
| 多租户隔离 | ⏸️ |
| API Gateway | ⏸️ |
| checkpoint 断点恢复 | ⏸️ |
| sandbox 沙箱 | ⏸️ |

---

## 四、技术选型（整合版）

在 v2.0 基础上新增：

| 组件 | 来源 | 用途 |
|------|------|------|
| LangGraph | #73 新增 | 图状工作流 |
| langchain-core | 依赖 | LangGraph 底层 |
| CrewAI | #73 参考 | 角色委派模式参考 |

---

## 五、持续改进（无终点）

对 AI 来说没有长期/短期之分。能干就一直干。

**当前核心任务**：Phase 3 - LLM 主动串技能
**后续任务**：Phase 4 可观测性 → Phase 5 企业级
**无固定周期**：每个任务完成后自动进入下一个，直到验收通过

---

## 六、已排除的工具

| 工具 | 排除原因 |
|------|---------|
| Superpowers | 已在 Plector（superpowers-zh 20技能） |
| AgencyAgent | 已在 Plector（agency-orchestrator 174角色） |
| OpenSpec | Phase 5 后考虑（作为 skills/spec_writer） |
| SpecKit | Phase 5 后考虑（作为 skills/requirement_engine） |
| BMAD | 太厚重（21 Agent），企业专用 |
| AutoGen | 多 Agent 对话暂不需要，复杂度高 |

---

## 七、验收标准（补充）

在 v2.0 原标准基础上新增：

- [ ] 长对话（50+ 轮）后 AI 仍能准确回答初始目标（GSD 保鲜验证）
- [ ] 条件分支工作流正确执行（LangGraph 验证）
- [ ] 多角色协作任务正确分派（CrewAI 模式验证）
- [ ] 任务失败后从检查点恢复（DeerFlow 验证）

