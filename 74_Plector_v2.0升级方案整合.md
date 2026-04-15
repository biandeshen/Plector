# Plector v2.0 升级方案 — 整合版

> 原始文档：`E:\产品\Plector\docs\reports\upgrade_plan_v2.0.md`（2025-12-19）
> 整合补充：AI 工具链整合方案（#73）
> 审查修复：P0-P3 共 23 项问题（2026-04-15）
> 整合日期：2026-04-15

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

## 三、分阶段实施计划（整合版）

> 原 v2.0：10 周（Phase 1-5）
> 新增：GSD + LangGraph + CrewAI + DeerFlow 融入各阶段

### Phase 1：核心稳定性 + GSD 上下文保鲜（2 周）

**来源**：v2.0 Phase 1 + #73 GSD

| ID | 任务 | 产出 |
|----|------|------|
| P1-1 | 统一错误处理层 | `core/error_handler.py` |
| P1-2 | 事件总线内存优化 | `event_bus_v2.py` |
| P1-3 | 敏感信息加密 | `core/security/secrets_manager.py` |
| P1-4 | 技能沙箱基础实现 | `core/skill_sandbox.py` |
| P1-5 | 单元测试补全 | `tests/core/` |
| **P1-N** | **GSD 上下文保鲜** | **`skills/context_refresher/` + 双 collection 记忆** |

**GSD 上下文保鲜详细设计**：
```
问题：长对话 AI 遗忘初始目标

机制：
1. 对话轮次 % N（N=10）触发"保鲜"
2. LLM 提取 {goal, constraints, completed[], in_progress[]}
3. 存入 vector_memory 单独 collection: "context_saver"
4. 新消息注入时拼接 {保鲜上下文 + 最近 5 轮} 而非全量历史
5. 初始目标变化时（用户明确修改）触发"重锚定"

新增文件：
- skills/context_refresher/
- core/memory.py（改造：双 collection 逻辑）
```

---

### Phase 2：性能优化 + LangGraph 工作流（2 周）

**来源**：v2.0 Phase 2 + #73 LangGraph

| ID | 任务 | 产出 |
|----|------|------|
| P2-1 | LLM 流式响应支持 | `core/llm_client_v2.py` |
| P2-2 | 技能热加载机制 | `core/skill_loader.py` |
| P2-3 | `image_handler.py` 拆分 | `core/image/` 目录 |
| P2-4 | 向量检索优化 | `core/vector_memory_v2.py` |
| P2-5 | 连接池管理 | `core/utils/connection_pool.py` |
| **P2-N** | **LangGraph 图状工作流** | **`core/workflow_graph.py` + `skills/conditional_chain/`** |

**LangGraph 工作流详细设计**：
```
问题：当前 skill_chain 线性静态，无法分支/循环/断点恢复

机制：
1. 用 LangGraph StateGraph 定义工作流
   - 节点：技能调用（复用 SkillHandler）
   - 边：条件判断（result 满足条件走对应边）
   - 循环：self_loops（重复直到退出条件）
2. 状态持久化到 vector_memory，支持断点恢复
3. 与现有 event_bus 集成（事件驱动图节点）
4. 174 角色 YAML 作为图的序列化格式

新增文件：
- core/workflow_graph.py（~150行，LangGraph 封装）
- skills/conditional_chain/（改造自 skill_chain/）
```

---

### Phase 3：模块化重构 + CrewAI 角色委派（3 周）

**来源**：v2.0 Phase 3 + #73 CrewAI

| ID | 任务 | 产出 |
|----|------|------|
| P3-1 | `mcp_client.py` 模块化 | `core/mcp/` 目录 |
| P3-2 | `agent_loop.py` 精简 | `core/agent_loop_v2.py`（< 500 行） |
| P3-3 | 配置中心化 | `core/config/config_manager.py` |
| P3-4 | 插件系统 | `core/plugin/plugin_system.py` |
| P3-5 | API 接口标准化 | `core/api/` 目录 |
| **P3-N** | **CrewAI 角色委派模式** | **`skills/role_delegator/` + `skill_orchestrator` 改造** |

**CrewAI 角色委派详细设计**：
```
问题：skill_orchestrator 编排能力弱，无多角色协作

机制：
1. 定义 Role 类：{name, goal, backstory, tools, verbose}
2. 任务进入时，根据目标匹配角色（或角色组合）
3. 角色间通过 event_bus 传递结果（模拟 CrewAI 的 task_output）
4. 支持"人类审批"节点（暂停等待人工确认）

新增文件：
- skills/role_delegator/（角色化任务分派）
- 改造 core/skill_orchestrator.py（复用现有逻辑）
```

---

### Phase 4：可观测性建设（1 周）

**来源**：v2.0 Phase 4

| ID | 任务 | 产出 |
|----|------|------|
| P4-1 | 健康检查端点 | `core/observability/health.py` |
| P4-2 | Prometheus 指标 | `core/observability/metrics.py` |
| P4-3 | 结构化日志 | `core/observability/logging.py` |
| P4-4 | 链路追踪 | `core/observability/tracing.py` |

---

### Phase 5：企业级功能 + DeerFlow 运行时（2 周）

**来源**：v2.0 Phase 5 + #73 DeerFlow

| ID | 任务 | 产出 |
|----|------|------|
| P5-1 | 多租户隔离 | 企业版功能 |
| P5-2 | API Gateway | 企业版功能 |
| **P5-N** | **DeerFlow 企业运行时** | **`core/checkpoint.py` + `core/sandbox/`** |

**DeerFlow 运行时详细设计**：
```
问题：agent_loop 无检查点，任务失败无法断点恢复

机制：
1. 每次技能执行后保存检查点（skill_name + args + result hash）
2. 任务失败时从最后一个检查点恢复
3. sandbox 层限制文件/网络操作（基于已有的 _check_safe_path）
4. 长期记忆：关键决策点写入 vector_memory，跨 session 恢复

新增文件：
- core/checkpoint.py（检查点持久化）
- core/sandbox/（沙箱执行层）
```

---

## 四、技术选型（整合版）

在 v2.0 基础上新增：

| 组件 | 来源 | 用途 |
|------|------|------|
| LangGraph | #73 新增 | 图状工作流 |
| langchain-core | 依赖 | LangGraph 底层 |
| CrewAI | #73 参考 | 角色委派模式参考 |

---

## 五、资源估算

| 阶段 | 原计划 | 整合后 | 新增内容 |
|------|--------|--------|---------|
| Phase 1 | 2 人 2 周 | 2 人 2.5 周 | GSD 上下文保鲜 |
| Phase 2 | 2 人 2 周 | 2 人 3 周 | LangGraph 工作流 |
| Phase 3 | 2 人 3 周 | 2 人 3.5 周 | CrewAI 角色委派 |
| Phase 4 | 1 人 1 周 | 1 人 1 周 | 无变化 |
| Phase 5 | 2 人 2 周 | 2 人 2.5 周 | DeerFlow 运行时 |
| **总计** | **10 周** | **12.5 周** | +2.5 周 |

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
