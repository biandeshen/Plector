# Plector 升级改造路线图

> 综合研究报告 — 基于 Obsidian 知识库（`E:\Plector开发流程\docs\`）100+ 文档分析
> 分析日期：2026-05-05
> 分析范围：102、103、104、105、106、110 等核心规划文档 + 当前 master 分支代码状态

---

## 关键发现：develop/agency-orchestrator 分支

远程 `origin/develop/agency-orchestrator` 分支包含 **603 files changed, +108,780 / -10,936 lines**，
大量 Obsidian 文档中规划的功能已在该分支实现。以下标注状态：
- ✅ **已实现** (develop分支) — 需合并到 master
- ❌ **未实现** — 需新建
- ⚠️ **部分实现** — 有代码但集成不完整

---

## 一、架构升级项

### P0 — 断点修复（影响系统闭环，未实现）

| ID | 问题 | 位置 | 状态 | 说明 |
|----|------|------|:----:|------|
| B1 | recommended_actions 未执行 | `agent_loop.py:500-536` | ❌ | 复杂度分析返回推荐动作，但 run_streaming 只打日志，从未实际调用 |
| B2 | context_refresher 未集成 | `agent_loop.py` + `skills/context_refresher/` | ⚠️ | skill 已创建（develop分支），但 AgentLoop 中无自动保鲜触发 |
| B3 | ClosureEngine 事件缺失 | `closure_engine.py` | ⚠️ | 闭环执行后不发布 completion/failure 事件 |
| B4 | Governance 未与 AgentLoop 集成 | `governance.py` → `agent_loop.py` | ❌ | 3-color DFS + EMA 健康分已实现，但 AgentLoop 从不调用 |

### P1 — 架构增强（部分已实现，需合并或补完）

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| A1 | **MiddlewareChain** | ✅ | `core/middleware_chain.py` 已实现（develop），5 个中间件 |
| A2 | **Skill Sandbox** | ✅ | `core/skill_sandbox.py` 已实现（develop），进程级隔离 |
| A3 | **SSRF 防护模块化** | ✅ | `core/security/ssrf_guard.py` 已提取（develop） |
| A4 | **PathManager** | ✅ | `core/path_manager.py` 已实现（develop），消除硬编码路径 |
| A5 | **LLM 客户端模块化** | ✅ | 拆分为 base/openai/anthropic/minimax/ollama（develop） |
| A6 | **FTS5 混合检索** | ❌ | 全文+向量融合搜索未实现 |
| A7 | **LLM 记忆提取** | ❌ | 从对话中主动提取关键信息未实现 |
| A8 | **并行工具执行** | ❌ | 工具调用仍是串行，未用 asyncio.gather |
| A9 | **技能版本与依赖解析** | ❌ | semver + 拓扑排序依赖解析未实现 |
| A10 | **技能文件监听** | ❌ | 当前轮询（5秒），未升级到 inotify/FSEvents |

### P2 — 扩展增强

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| E1 | **渠道网关** (ChannelGateway) | ❌ | 多平台适配（Telegram/Discord/钉钉/飞书） |
| E2 | **工作区隔离 + 多智能体** | ⚠️ | Agency Orchestrator 完整（develop），但工作区级资源隔离未实现 |
| E3 | **RBAC/ABAC 权限系统** | ❌ | 基于角色的工具/技能访问控制 |
| E4 | **审计日志 (WORM)** | ❌ | 不可变审计日志 + 哈希链防篡改 |
| E5 | **OpenTelemetry 可观测性** | ❌ | 分布式追踪、指标导出、Langfuse 集成 |
| E6 | **Pydantic 输入验证** | ❌ | AgentContext 用 Pydantic 模型替代裸 dict |
| E7 | **指数退避重试** | ❌ | MCP/LLM 连接失败时 exponential backoff + jitter |
| E8 | **内容安全过滤** | ✅ | `core/content_filter.py` 已实现（develop） |
| E9 | **限流器** | ✅ | `core/rate_limiter.py` 已实现（develop） |
| E10 | **密钥管理** | ✅ | `core/security/secrets_manager.py` 已实现（develop） |

---

## 二、记忆系统升级

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| M1 | **艾宾浩斯遗忘曲线** | ✅ | `vector_memory_v2.py` 已实现（develop），4 层强度 |
| M2 | **查询缓存** | ✅ | LRU 淘汰 + TTL 5min（develop） |
| M3 | **8 种联想模式** | ✅ | 语义相似/触景生情/触类旁通等（develop） |
| M4 | **FTS5 全文搜索** | ❌ | SQLite FTS5 扩展全文索引未启用 |
| M5 | **LLM 主动记忆提取** | ❌ | 对话结束后 LLM 提取关键实体/事实/偏好 |
| M6 | **生成式记忆反思** | ❌ | 定时触发器对记忆进行总结、抽象和合并 |
| M7 | **3D 记忆评分** | ❌ | 综合 recency/relevance/importance 三维评分 |
| M8 | **图谱记忆** | ❌ | 实体-关系图谱存储（Neo4j/NetworkX） |

---

## 三、安全加固

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| S1 | **输入清理 (InputSanitizer)** | ❌ | 检测危险模式（os.system/subprocess/exec） |
| S2 | **RBAC 权限控制** | ❌ | user/developer/admin 三级角色，工具级权限 |
| S3 | **Agent 身份令牌** | ❌ | Agent 间调用的身份认证和授权 |
| S4 | **审计日志** | ❌ | WORM 存储 + 哈希链完整性验证 |
| S5 | **沙箱执行** | ✅ | `skill_sandbox.py` 进程池 + 资源限制（develop） |
| S6 | **密钥扫描增强** | ⚠️ | `.secret-allowlist` 模式覆盖不足（约 60%） |
| S7 | **依赖 CVE 扫描** | ❌ | `requirements.txt` 无自动 CVE 检测 |
| S8 | **MCP 协议升级** | ❌ | 升级到 MCP 2025-06-18 规范 |

---

## 四、闭环系统扩展

当前 master 闭环状态：**只有 2 个闭环**（error_record_loop + health_check_loop）

| ID | 闭环 | 触发事件 | 状态 |
|----|------|----------|:----:|
| L1 | error_record_loop | test.failed | ✅ master |
| L2 | health_check_loop | health.degraded | ✅ master |
| L3 | context_refresh_loop | turn.count_reached | ❌ |
| L4 | complex_task_loop | complexity.detected | ❌ |
| L5 | skill_failure_loop | skill.failed | ❌ |
| L6 | self_improve_loop | error_accumulated | ❌ |

---

## 五、前端增强

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| F1 | **停止生成按钮** | ✅ | develop 分支 |
| F2 | **代码块复制 + 语言标签** | ✅ | develop 分支 |
| F3 | **工具面板动画** | ✅ | develop 分支 |
| F4 | **重新生成按钮** | ❌ | 待实现 |
| F5 | **思考气泡独立展示** | ⚠️ | 思考应独立为 thinking 事件而非工具附属 |
| F6 | **虚拟滚动** | ❌ | 长对话性能优化 |
| F7 | **移动端响应式** | ❌ | 待适配 |
| F8 | **侧边栏搜索** | ❌ | 对话历史搜索 |
| F9 | **主题切换** | ❌ | 暗色/亮色模式 |
| F10 | **工具执行时间线视图** | ❌ | 步骤时间线替代当前折叠面板 |

---

## 六、工作流引擎升级

| ID | 项目 | 状态 | 说明 |
|----|------|:----:|------|
| W1 | **Agency Orchestrator MCP Server** | ✅ | 完整 TypeScript 实现（develop），30+ 预定义工作流 |
| W2 | **条件分支 + 循环** | ✅ | DAG + condition/loop 节点（develop） |
| W3 | **Temporal 持久化执行** | ❌ | 长时间运行工作流的断点续传 |
| W4 | **LangGraph StateGraph** | ❌ | 有状态图执行 + checkpoint 回滚 |
| W5 | **YAML 工作流模板** | ✅ | 多部门协作模板已内置（develop） |

---

## 七、竞品差距分析

与 Hermes Agent / DeerFlow / OpenClaw 对比：

| 维度 | Plector (master) | Plector (develop) | 竞品最佳 |
|------|:---:|:---:|------|
| 中间件链 | ❌ | ✅ 5个 | DeerFlow: 9个 |
| 多平台渠道 | 2 (CLI+WS) | 2 | Hermes: 18 |
| 记忆全文搜索 | ❌ | ❌ | Hermes: FTS5 |
| 执行后端 | 1 (local) | 1 + sandbox | Hermes: 6种 |
| LLM 记忆提取 | ❌ | ❌ | DeerFlow: ✅ |
| 技能热更新 | 轮询5s | 轮询5s | 事件驱动 |
| RBAC | ❌ | ❌ | OpenClaw: ✅ |
| 工作流引擎 | YAML DAG | YAML DAG + MCP | Temporal/LangGraph |
| 可观测性 | 日志 | 日志 + metrics | OpenTelemetry |
| 前端 | Vue3 SPA | Vue3 SPA+ | Hermes: React |

---

## 八、实施建议

### 立即（1-2 周）

1. **合并 develop/agency-orchestrator 到 master** — 一次性获得 18 个已完成升级项
2. **修复 4 个 P0 断点** (B1-B4) — AgentLoop 集成补全
3. **扩展闭环配置** (L3-L6) — `closed_loops.yaml` 新增 4 个闭环

### 短期（3-6 周）

4. **FTS5 全文搜索** (M4) — SQLite FTS5 扩展 + BM25 融合
5. **LLM 记忆提取** (M5) — 对话后 LLM 提取关键信息
6. **输入清理** (S1) — InputSanitizer 中间件
7. **OpenTelemetry** (E5) — 分布式追踪 + Langfuse

### 中期（6-12 周）

8. **渠道网关** (E1) — 先加 Telegram + 飞书
9. **RBAC 权限** (S2) — 工具/技能级访问控制
10. **审计日志** (S4) — WORM + 哈希链
11. **前端增强** (F5-F10) — 思考气泡、虚拟滚动、移动端

### 长期（3-6 月）

12. **多智能体工作区隔离** (E2) — 资源隔离 + 优先级路由
13. **Temporal/LangGraph 工作流** (W3-W4) — 持久化执行
14. **Agent 身份令牌** (S3) — Agent-to-Agent 认证
15. **图谱记忆** (M8) — 实体关系网络

---

## 九、统计汇总

| 类别 | 总数 | ✅已完成 | ⚠️部分 | ❌待实现 |
|------|:---:|:---:|:---:|:---:|
| 架构升级 | 15 | 6 | 2 | 7 |
| 记忆系统 | 8 | 3 | 0 | 5 |
| 安全加固 | 8 | 1 | 1 | 6 |
| 闭环系统 | 6 | 2 | 0 | 4 |
| 前端增强 | 10 | 3 | 1 | 6 |
| 工作流引擎 | 5 | 3 | 0 | 2 |
| **总计** | **52** | **18** | **4** | **30** |

> **关键行动**：合并 `develop/agency-orchestrator` 分支可一次性解决 18 个已完成的升级项。

---

## 十、参考文档

| 文档 | 内容 |
|------|------|
| `E:/Plector开发流程/102_Plector未来升级改造演进方案.md` | 架构蓝图 + 6 阶段计划 |
| `E:/Plector开发流程/103_Plector深度技术分析报告.md` | 代码级架构分析 |
| `E:/Plector开发流程/106_Plector最终实施计划方案.md` | 6 断点修复详细方案（含代码） |
| `E:/Plector开发流程/110_v2.x_重构优化计划.md` | v2.x 重构（大部分已完成于 develop） |
| `E:/Plector开发流程/105_Plector功能联动融合方案.md` | 功能联动设计 |
| `E:/Plector开发流程/93_Plector与同类开源Agent项目对比.md` | 竞品对比 |
| `E:/Plector开发流程/97_Plector技能与架构增强方案.md` | 技能与架构增强 |

---

*报告生成于 2026-05-05 · 基于 Obsidian 知识库 100+ 文档分析*
