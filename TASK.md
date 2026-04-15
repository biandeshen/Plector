# Plector 自改进任务书

**时间**: 2026-04-16 01:04
**来源**: 项目领导

## 当前问题

你的自改进系统创建了以下**冗余模块**，违反了"复用优先"原则：

### 1. core/roles/ 目录（应删除）

**问题**：`external-skills/roles/` 已有 174 个 YAML 角色定义，覆盖所有常见角色。你又创建了 `core/roles/` 的 Python 类（base.py、engineer.py、operator.py、orchestrator.py、reviewer.py），这是重复实现。

**正确做法**：
- 只用 `external-skills/roles/` 里的 YAML 角色
- 通过 `agency_orchestrator` 的 `run_workflow` 工具来编排
- 不需要 `core/roles/` 目录

### 2. 应保留的核心模块

以下是你创建的、确实有价值的模块，**保留**：

- ✅ `core/event_bus_v2.py` — 内存优化 + 通配符修复
- ✅ `core/llm_client_v2.py` — 流式响应支持
- ✅ `core/skill_loader.py` — 热加载机制
- ✅ `core/skill_sandbox.py` — 沙箱基础实现
- ✅ `core/error_handler.py` — 统一错误处理
- ✅ `core/security/secrets_manager.py` — 密钥管理
- ✅ `core/image/` — image_handler 拆分
- ✅ `core/vector_memory_v2.py` — 向量存储优化
- ✅ `skills/context_refresher/` — GSD 上下文保鲜

### 3. 需评估的模块

以下模块属于 Phase 3-5 的内容，**评估是否当前必要**：

- `core/cli/` — CLI 命令系统
- `core/compat/` — v1 适配器
- `core/interfaces/` — 接口抽象层
- `core/observability/` — 可观测性（Phase 4）
- `core/performance/` — 性能监控（Phase 4）
- `core/protocols/` — 协议定义
- `core/telemetry/` — 遥测
- `core/config_manager.py` — 配置中心
- `core/plugin_system.py` — 插件系统
- `core/docs_generator.py` — 文档生成
- `core/role_switcher.py` — 角色切换器
- `skills/crewai_integration/` — CrewAI 整合（Phase 3）

## 执行要求

1. **删除** `core/roles/` 目录及其所有文件
2. **评估** 上述"需评估的模块"——如果当前阶段不需要，删除或标记为 TODO
3. **确保** 所有保留模块的测试通过
4. **验证** pytest 19/19 V1 核心测试通过

## 成功标准

- `core/roles/` 目录不存在
- V1 核心测试全部通过（event_bus、skill_registry、tool_registry）
- 无新增冗余模块
