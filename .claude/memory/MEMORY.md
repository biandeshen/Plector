# 项目记忆

> AI 启动时读取此文件（~2KB），使用 `/remember` 管理记忆。
> 模板版本：v1.1.0 | 最后更新：2026-05-05

## 索引

| memory-id | 日期 | 类型 | 优先级 | access_count | 摘要 |
|-----------|------|------|:------:|:------------:|------|
| ADR-001 | 2026-05-04 | ADR | P0 | 0 | 多 LLM 后端抽象基类架构 |
| ADR-002 | 2026-05-04 | ADR | P0 | 0 | MCP 协议作为技能定义标准 |
| ADR-003 | 2026-05-04 | ADR | P0 | 0 | CloudEvents 1.0 事件总线 |
| ADR-004 | 2026-05-04 | ADR | P1 | 0 | ReAct 循环 + 闭包引擎架构 |
| ADR-005 | 2026-05-04 | ADR | P1 | 0 | ChromaDB 向量记忆系统 |
| ADR-006 | 2026-05-05 | ADR | P0 | 0 | AgentLoop 拆分为 4 个专注模块 |
| ADR-007 | 2026-05-05 | ADR | P0 | 0 | MCPManager 合并到 MCPClient |
| BUG-001 | 2026-05-05 | Bug | P1 | 0 | get_all_tools() 外层循环导致工具重复 |

## ID 命名规范

| 类型 | ID 前缀 | 示例 |
|------|---------|------|
| 架构决策 | ADR | ADR-001 |
| Bug 记录 | BUG | BUG-001 |
| 编码模式 | PAT | PAT-001 |
| 领域知识 | CTX | CTX-001 |

`access_count` 表示该记忆被检索次数。
每次通过 /remember search 或 /remember show 检索到记忆时自动递增。
GC 依据：>90 天且 access_count < 2（即几乎未被检索过）→ 归档。

---

## 架构决策 (ADR)

### ADR-001: 多 LLM 后端抽象基类架构
- **状态**: 已采纳
- **日期**: 2026-05-04
- **背景**: 需要同时支持 Ollama（本地）、OpenAI、Anthropic 等多个 LLM 后端
- **决策**: 使用 `core/llm_client.py` 作为单文件 LLM 客户端，各后端通过内部分支实现
- **后果**: 所有后端集中在单一文件中，新增后端需修改同一文件，但降低了文件间耦合
- **关联文件**: `core/llm_client.py`

### ADR-002: MCP 协议作为技能定义标准
- **状态**: 已采纳
- **日期**: 2026-05-04
- **背景**: 技能系统需要标准化的接口定义格式
- **决策**: 采用 Model Context Protocol (MCP) Tool 格式定义技能的 skill.json，通过 `core/mcp_client.py` 处理协议交互
- **后果**: 可与外部 MCP Server 互通，但需追踪 MCP 协议演进
- **关联文件**: `core/mcp_client.py`, `core/skill_registry.py`, `core/skill_handler.py`

### ADR-003: CloudEvents 1.0 事件总线
- **状态**: 已采纳
- **日期**: 2026-05-04
- **背景**: 组件间需要异步解耦通信
- **决策**: 采用 CloudEvents 1.0 标准格式作为事件总线协议
- **后果**: 标准化的事件格式便于外部集成，但增加了序列化开销
- **关联文件**: `core/event_bus.py`

### ADR-004: ReAct 循环 + 闭包引擎架构
- **状态**: 已采纳
- **日期**: 2026-05-04
- **背景**: Agent 需要自主推理-行动循环能力
- **决策**: 采用 ReAct (Reasoning + Acting) 循环作为主执行流程，搭配闭包引擎实现条件图执行和自动修复
- **后果**: 支持复杂多步推理，但循环深度需限制以防止失控
- **关联文件**: `core/agent_loop.py`, `core/closure_engine.py`

### ADR-005: ChromaDB 向量记忆系统
- **状态**: 已采纳
- **日期**: 2026-05-04
- **背景**: Agent 需要持久化的语义记忆能力
- **决策**: 使用 ChromaDB 作为向量存储后端，实现语义搜索和关联记忆
- **后果**: 支持大规模记忆检索，但增加了 ChromaDB 运维依赖
- **关联文件**: `core/vector_memory.py`

### ADR-006: AgentLoop 拆分为 4 个专注模块
- **状态**: 已采纳
- **日期**: 2026-05-05
- **背景**: `core/agent_loop.py` 267 行包含图片处理、记忆加载、对话持久化、ReAct 循环 4 种职责，违反单一职责原则
- **决策**: 提取 ImageRouter（图片路由）、MemoryLoader（记忆加载）、ConversationStore（对话存储）为独立模块，AgentLoop 仅保留编排职责
- **后果**: AgentLoop 从 267 行降至 175 行（-34%），依赖从 11 个减少到 4 个核心组合对象；新增 3 个模块各 ~50-70 行，职责单一
- **关联文件**: `core/agent_loop.py`, `core/image_router.py`, `core/memory_loader.py`, `core/conversation_store.py`

### ADR-007: MCPManager 合并到 MCPClient
- **状态**: 已采纳
- **日期**: 2026-05-05
- **背景**: `core/mcp_manager.py`（124 行）是 MCPClient 的薄包装层，重复了连接管理、工具注册逻辑
- **决策**: 删除 MCPManager，将其 config 文件加载、工具注册表功能合并到 MCPClient 自身
- **后果**: 消除 MCP 双连接路径风险，MCPClient 可直接接受 config 文件路径或 dict，减少一层间接调用
- **关联文件**: `core/mcp_client.py`, `core/mcp_manager.py`（已删除）, `core/skill_registry.py`, `tests/test_minimax_*.py`

---

## Bug 模式

### BUG-001: get_all_tools() 外层循环导致工具重复
- **状态**: 已修复
- **日期**: 2026-05-05
- **症状**: `MCPClient.get_all_tools()` 返回的工具列表包含重复条目（N 个 server × M 个工具）
- **根因**: 从 MCPManager 迁移时错误地添加了 `for server_name in self.servers` 外层循环，而 `_tool_registry` 已包含所有 server 的工具
- **修复**: 移除外层循环，仅遍历 `_tool_registry.items()`
- **教训**: 迁移数据聚合方法时，检查内部数据结构是否已是全集；`_tool_registry` 的 key 已按 `mcp_{server}_{tool}` 命名，无需按 server 分维度
- **关联文件**: `core/mcp_client.py:375`
- **标签**: #重构 #数据聚合

<!-- 模板：
### [BUG-000] 问题简述
- **状态**: 已修复 / 已知未修复 / 无法复现
- **日期**: YYYY-MM-DD
- **症状**: 用户/系统看到什么
- **根因**: 真正的底层原因
- **修复**: 如何修复的
- **教训**: 如何避免再次发生
- **关联文件**: 涉及的文件路径
- **标签**: #数据库 #并发 #空指针
-->

---

## 编码模式

<!-- 模板：
### [PAT-000] 模式简述
- **类型**: 模式 / 反模式 / 约定
- **日期**: YYYY-MM-DD
- **描述**: 这个模式是什么
- **原因**: 为什么采用这个模式
- **示例**: 代码示例
- **标签**: #错误处理 #命名 #测试
-->

---

## 领域知识

<!-- 模板：
### [CTX-000] 主题
- **日期**: YYYY-MM-DD
- **描述**: 业务/技术背景
- **影响**: 这个背景对开发的具体影响
- **标签**: #业务域 #第三方 #环境
-->

---

## 归档

超过 90 天且 access_count = 0 的记忆 → 移至 [archive/](archive/) 目录。

> 使用 `/remember` 浏览/编辑/删除记忆。运行 `/gc` 清理过期记忆。
