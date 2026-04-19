# Plector 功能联动融合方案

> 将已有功能与升级方案有机融合，实现智能体生态闭环
> 版本：2.1（融合版）
> 更新：2026-04-19

---

## 一、功能全景图

### 1.1 现有技能体系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Plector 技能生态系统                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Tier 1 - 系统基础层                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │   memory      │  │context_refre │  │health_monitor│          │   │
│  │  │   记忆系统     │  │    sher      │  │   健康监控    │          │   │
│  │  │ 8种关联模式    │  │  GSD保鲜    │  │  技能健康分   │          │   │
│  │  │ 艾宾浩斯遗忘   │  │  重锚定     │  │  循环检测    │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Tier 2 - 功能执行层                                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│   │
│  │  │code_writ│  │file_util│  │test_run │  │web_searc│  │error_kno││   │
│  │  │   er    │  │    s    │  │   ner    │  │   h     │  │ wledge  ││   │
│  │  │ 代码编写 │  │ 文件操作 │  │ 测试执行 │  │ 网页搜索 │  │ 错误知识 ││   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Tier 3 - 高级编排层                                │   │
│  │  ┌───────────────────────┐  ┌───────────────────────┐            │   │
│  │  │   agency_orchestrator  │  │     self_improver      │            │   │
│  │  │   多角色工作流引擎      │  │      自改进系统        │            │   │
│  │  │ 174角色 / YAML DAG     │  │  多角色协作 / 事件驱动  │            │   │
│  │  └───────────────────────┘  └───────────────────────┘            │   │
│  │                                    │                                 │   │
│  │  ┌───────────────────────────────────────────────────────┐        │   │
│  │  │                    auto_developer                      │        │   │
│  │  │                     一键开发流水线                      │        │   │
│  │  │        auto_develop.yaml → 174角色协作执行             │        │   │
│  │  └───────────────────────────────────────────────────────┘        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技能详情矩阵

| 技能 | 版本 | 工具数 | 核心能力 | 事件发布 | 事件订阅 |
|------|------|--------|---------|---------|---------|
| memory | 2.0.0 | 11 | 向量存储、8种关联、艾宾浩斯 | memory.stored, memory.retrieved, memory.decay_checked | - |
| context_refresher | 1.0.0 | 4 | GSD保鲜、重锚定、上下文注入 | - | - |
| health_monitor | 1.0.0 | 1 | 健康检查、循环检测 | - | - |
| error_knowledge | 1.0.0 | 3 | 错误存储、分类 | error.stored, error.classified | test.failed, skill.failed |
| code_writer | 1.0.0 | 3 | 代码读写修改 | - | - |
| file_utils | 1.0.0 | 5 | 文件操作 | - | - |
| test_runner | 1.0.0 | 2 | 测试执行、命令运行 | test.failed | - |
| web_search | 1.0.0 | 2 | 搜索、页面抓取 | - | - |
| agency_orchestrator | 1.1.0 | 7 | 工作流执行、角色管理 | workflow.executed, role.executed | task.multi_role, workflow.run_request |
| auto_developer | 1.0.0 | 6 | 一键开发、结果读取 | auto_develop.started | - |
| self_improver | 1.0.0 | 4 | 自改进、多角色协作 | self_improve.* | - |

---

## 二、功能联动设计

### 2.1 联动总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          功能联动矩阵                                          │
│                                                                             │
│         memory   context  health  error   code   test   web   agency  auto  │
│        ───────  ───────  ─────  ─────  ─────  ─────  ────  ──────  ─────   │
│ memory    ─        ✓       ✓      ✓       ✓      ✓      ✓      ✓       ✓    │
│ context   ✓        ─       ✓      ✓       ✓      ✓      ✓      ✓       ✓    │
│ health    ✓        ✓       ─      ✓       ✓      ✓      ✓      ✓       ✓    │
│ error     ✓        ✓       ✓      ─       ✓      ✓      ✓      ✓       ✓    │
│ code      ✓        ✓       ✓      ✓       ─      ✓      ✓      ✓       ✓    │
│ test      ✓        ✓       ✓      ✓       ✓      ─      ✓      ✓       ✓    │
│ web       ✓        ✓       ✓      ✓       ✓      ✓      ─      ✓       ✓    │
│ agency    ✓        ✓       ✓      ✓       ✓      ✓      ✓      ─       ✓    │
│ auto_dev  ✓        ✓       ✓      ✓       ✓      ✓      ✓      ✓       ─    │
│                                                                             │
│  说明：✓ 表示两个技能之间存在直接联动关系                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心联动链路

#### 链路 1：自改进闭环（最重要）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     自改进闭环链路                                            │
│                                                                             │
│  ┌─────────────┐                                                           │
│  │  error_kno │  捕获错误                                                  │
│  │  wledge    │  store_error() → error.failed                             │
│  └──────┬──────┘                                                           │
│         │ error.failed 事件                                                │
│         ▼                                                                   │
│  ┌─────────────┐                                                           │
│  │ self_improv │  触发自改进                                               │
│  │    er      │  start_upgrade() → 读取方案                                │
│  └──────┬──────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │            agency_orchestrator                     │                    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐          │                    │
│  │  │ 角色A    │  │ 角色B    │  │ 角色C    │          │                    │
│  │  │SystemAnal│  │CodeDevel│  │TechWrite│          │                    │
│  │  │  opyer  │  │  oper   │  │   r     │          │                    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘          │                    │
│  │       └────────────┼────────────┘                │                    │
│  │                    │                              │                    │
│  │              compose_workflow()                    │                    │
│  └────────────────────┼──────────────────────────────┘                    │
│                       │                                                       │
│         ┌─────────────┼─────────────┐                                       │
│         ▼             ▼             ▼                                       │
│  ┌─────────────┐ ┌─────────┐ ┌─────────────┐                                │
│  │ code_writer │ │test_run │ │  memory    │                                │
│  │  执行修改    │ │  ner   │ │ 记录经验   │                                │
│  └──────┬──────┘ └────┬────┘ └──────┬──────┘                                │
│         │ test.failed │             │                                       │
│         │ 事件         │             │                                       │
│         └──────────────┴─────────────┘                                       │
│                           │                                                   │
│                    验证通过 → 完成                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 链路 2：开发流水线

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     开发流水线链路                                            │
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   memory    │     │  auto_dev  │     │  agency     │                   │
│  │  加载经验   │────▶│  启动开发   │────▶│  多角色协作  │                   │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘                   │
│         ▲                   │                   │                            │
│         │                   ▼                   ▼                            │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │ context_ref │     │ code_writer │     │  test_run   │                   │
│  │  注入目标   │     │   执行编码   │────▶│    ner      │                   │
│  └─────────────┘     └──────┬──────┘     │   执行测试   │                   │
│                              │            └──────┬──────┘                   │
│                              │                   │                            │
│                              ▼                   ▼                            │
│                      ┌─────────────┐     ┌─────────────┐                   │
│                      │  file_util  │     │  error_kno  │                   │
│                      │   s         │     │  wledge     │                   │
│                      │  文件写入    │     │  错误分类   │                   │
│                      └─────────────┘     └─────────────┘                   │
│                                                                             │
│  health_monitor 贯穿全程：技能健康分监控                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 链路 3：智能记忆联动

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     智能记忆联动                                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         记忆系统                                       │  │
│  │                                                                       │  │
│  │   memory ─────────── context_refresher ─────────── self_improver     │  │
│  │   (存储)              (保鲜)                    (自改)                │  │
│  │      │                   │                        │                   │  │
│  │      │ 语义搜索          │ 上下文注入             │ 经验提取         │  │
│  │      ▼                   ▼                        ▼                   │  │
│  │   ┌─────────┐      ┌─────────┐            ┌─────────┐              │  │
│  │   │关联搜索  │      │GSD目标  │            │最佳实践 │              │  │
│  │   │8种模式  │      │保鲜     │            │记忆    │              │  │
│  │   └────┬────┘      └────┬────┘            └────┬────┘              │  │
│  │        │                 │                      │                   │  │
│  │        └────────┬────────┴──────────────────────┘                   │  │
│  │                 │                                                     │  │
│  │                 ▼                                                     │  │
│  │   ┌─────────────────────────────────────────┐                       │  │
│  │   │          联想式记忆引擎                   │                       │  │
│  │   │   概念关联 / 图谱构建 / 复习调度           │                       │  │
│  │   └─────────────────────────────────────────┘                       │  │
│  │                                                                       │  │
│  │   艾宾浩斯遗忘曲线：记忆衰减 → 复习提醒 → 强化                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、事件驱动架构

### 3.1 事件总线拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           事件总线 (EventBus)                              │
│                                                                             │
│  发布者 (Publisher)                                                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│  │ memory          │ │ error_knowledge │ │ self_improver   │             │
│  │ memory.stored   │ │ error.stored    │ │ self_improve.*  │             │
│  │ memory.retrieve │ │ error.classified│ │                 │             │
│  │ memory.decay   │ │                 │ │                 │             │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘             │
│           │                   │                   │                        │
│           └───────────────────┼───────────────────┘                        │
│                               │                                            │
│                         事件总线 (EventBus)                                 │
│                               │                                            │
│                               ▼                                            │
│  订阅者 (Subscriber)                                                          │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │
│  │ error_knowledge│ │ health_monitor  │ │ self_improver   │             │
│  │ test.failed    │ │ 循环检测        │ │ error.failed    │             │
│  │ skill.failed   │ │                 │ │ workflow.done   │             │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘             │
│                                                                             │
│  现有事件类型：                                                             │
│  • memory.stored / memory.retrieved / memory.decay_checked                 │
│  • error.stored / error.classified                                          │
│  • test.failed / skill.failed                                               │
│  • self_improve.upgrade.started / .completed / .stopped                   │
│  • self_improve.task.assigned / .test.failed / .phase.completed           │
│  • self_improve.agency.compose_started / .compose_completed / .compose_failed│
│  • auto_develop.started                                                    │
│  • workflow.executed / workflow.composed / role.executed                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 新增事件建议

```python
# 新增事件类型
NEW_EVENTS = {
    # 记忆相关
    "memory.extracted": {
        "description": "LLM 提取到新记忆",
        "data": {"memory_type", "content", "confidence"}
    },
    "memory.reinforced": {
        "description": "记忆被强化",
        "data": {"doc_id", "old_intensity", "new_intensity"}
    },
    "memory.review_reminder": {
        "description": "记忆复习提醒",
        "data": {"doc_ids", "reason"}
    },

    # 上下文相关
    "context.refreshed": {
        "description": "GSD 上下文已保鲜",
        "data": {"session_id", "goal_version", "completed_count"}
    },
    "context.re_anchored": {
        "description": "GSD 目标已重锚定",
        "data": {"session_id", "old_goal", "new_goal"}
    },

    # 开发相关
    "develop.started": {
        "description": "开发流程启动",
        "data": {"requirement", "workflow"}
    },
    "develop.completed": {
        "description": "开发流程完成",
        "data": {"result", "files_changed"}
    },
    "develop.failed": {
        "description": "开发流程失败",
        "data": {"error", "step"}
    },

    # 健康相关
    "health.degraded": {
        "description": "技能健康分下降",
        "data": {"skill", "old_score", "new_score"}
    },
    "health.cycle_detected": {
        "description": "检测到依赖循环",
        "data": {"skills", "cycle"}
    },
    "health.eliminated": {
        "description": "技能被淘汰",
        "data": {"skill", "reason", "score"}
    },

    # 工具相关
    "tool.executing": {
        "description": "工具开始执行",
        "data": {"tool", "arguments"}
    },
    "tool.executed": {
        "description": "工具执行完成",
        "data": {"tool", "result", "elapsed"}
    },
    "tool.failed": {
        "description": "工具执行失败",
        "data": {"tool", "error"}
    },
}
```

---

## 四、功能联动实现

### 4.1 记忆 ↔ 上下文保鲜联动

```python
# core/skill_chain/memory_context_chain.py
"""
记忆系统与上下文保鲜的深度联动
"""

class MemoryContextChain:
    """
    记忆与上下文保鲜联动链

    联动机制：
    1. memory.associative_search → 搜索结果注入 context
    2. context.inject_context → 上下文优先使用 memory 结果
    3. 记忆强度 → 上下文保鲜优先级
    """

    def __init__(self):
        self.memory = MemorySkill()
        self.context = ContextRefresher()
        self.vector_memory = VectorMemoryV2()

    async def smart_search_and_inject(
        self,
        query: str,
        session_id: str,
        modes: list[str] = None
    ) -> dict:
        """
        智能搜索并注入上下文

        1. 并行执行多种记忆搜索
        2. 融合结果
        3. 注入上下文保鲜
        """
        if modes is None:
            modes = ["semantic_similarity", "context_triggers"]

        # 1. 并行多模式记忆搜索
        tasks = []
        for mode in modes:
            tasks.append(self.memory.associative_search(
                query=query,
                mode=mode,
                limit=5
            ))

        results = await asyncio.gather(*tasks)

        # 2. 融合搜索结果
        fused_results = self._fuse_results(results)

        # 3. 提取关键记忆
        key_memories = self._extract_key_memories(fused_results)

        # 4. 注入上下文保鲜
        conversation_history = await self.memory.get_conversation_history(
            session_id=session_id,
            limit=20
        )

        await self.context.preserve(
            session_id=session_id,
            conversation_history=conversation_history,
            current_goal=key_memories.get("goal", "")
        )

        # 5. 强化被引用的记忆
        for doc_id in key_memories.get("reinforce_ids", []):
            await self.vector_memory.reinforce_memory(doc_id, "conversations")

        return {
            "success": True,
            "data": {
                "results": fused_results,
                "injected_context": key_memories,
                "reinforced_count": len(key_memories.get("reinforce_ids", []))
            }
        }

    def _fuse_results(self, results: list) -> list:
        """融合多种搜索结果"""
        seen = set()
        fused = []

        for result_set in results:
            for item in result_set.get("data", {}).get("results", []):
                key = item.get("id") or item.get("content", "")[:50]
                if key not in seen:
                    seen.add(key)
                    fused.append(item)

        return fused[:10]

    def _extract_key_memories(self, results: list) -> dict:
        """从记忆结果中提取关键信息用于上下文"""
        return {
            "goal": results[0].get("content", "")[:200] if results else "",
            "reinforce_ids": [r.get("id") for r in results[:3] if r.get("id")],
            "patterns": [r.get("match_type") for r in results[:5]],
        }
```

### 4.2 错误 ↔ 自改进 ↔ 工作流联动

```python
# core/skill_chain/error_self_improve_chain.py
"""
错误知识与自改进系统的深度联动
"""

class ErrorSelfImproveChain:
    """
    错误 → 自改进联动链

    联动机制：
    1. error_knowledge 捕获错误
    2. 发布 error.failed 事件
    3. self_improver 监听并触发自改进
    4. agency_orchestrator 执行修复工作流
    5. 测试验证修复结果
    """

    def __init__(self):
        self.error_knowledge = ErrorKnowledgeSkill()
        self.self_improver = SelfImproverSkill()
        self.agency = AgencyOrchestrator()
        self.test_runner = TestRunnerSkill()

    async def auto_fix_on_error(
        self,
        error: str,
        context: dict = None
    ) -> dict:
        """
        错误自动修复流程

        1. 存储错误并分类
        2. 生成修复工作流
        3. 执行工作流
        4. 验证修复
        """
        # 1. 存储错误
        error_result = await self.error_knowledge.store_error(error)
        error_id = error_result.get("data", {}).get("error_id")

        # 2. 分类错误
        classified = await self.error_knowledge.classify_error(error)
        category = classified.get("data", {}).get("category")

        # 3. 根据错误类型生成工作流
        workflow_desc = self._generate_workflow_description(error, category, context)

        # 4. 使用 agency_orchestrator 合成工作流
        try:
            compose_result = await self.agency.compose_workflow(
                description=workflow_desc,
                provider="claude-code"
            )
            workflow_path = compose_result.get("data", {}).get("workflow_path")

            # 5. 执行工作流
            run_result = await self.agency.run_workflow(
                path=workflow_path,
                inputs={
                    "error": error,
                    "error_id": error_id,
                    "category": category,
                    "context": context or {}
                },
                provider="claude-code"
            )

            # 6. 验证修复
            verification = await self._verify_fix(run_result)

            return {
                "success": True,
                "data": {
                    "error_id": error_id,
                    "category": category,
                    "workflow_path": workflow_path,
                    "result": run_result,
                    "verification": verification
                }
            }

        except Exception as e:
            return {
                "success": False,
                "data": {"error_id": error_id},
                "error": f"自动修复失败: {str(e)}"
            }

    def _generate_workflow_description(self, error: str, category: str, context: dict) -> str:
        """根据错误类型生成工作流描述"""
        templates = {
            "syntax_error": "修复语法错误：{error}\n角色：code-developer, test-engineer",
            "timeout": "解决超时问题：{error}\n角色：system-architect, performance-engineer",
            "permission": "修复权限问题：{error}\n角色：security-engineer, devops",
            "connection": "解决连接问题：{error}\n角色：backend-engineer, network-engineer",
            "unknown": "通用修复：{error}\n角色：code-developer, tester, tech-writer"
        }

        template = templates.get(category, templates["unknown"])
        return template.format(error=error)
```

### 4.3 开发流程全链路联动

```python
# core/skill_chain/develop_pipeline_chain.py
"""
开发流水线全链路联动
"""

class DevelopPipelineChain:
    """
    开发流水线全链路联动

    联动路径：
    memory → context → agency → code_writer
                                      ↓
                                file_utils
                                      ↓
                               test_runner → error_knowledge
                                      ↓
                                  memory (记录经验)
    """

    def __init__(self):
        self.memory = MemorySkill()
        self.context = ContextRefresher()
        self.agency = AgencyOrchestrator()
        self.code_writer = CodeWriterSkill()
        self.file_utils = FileUtilsSkill()
        self.test_runner = TestRunnerSkill()
        self.error_knowledge = ErrorKnowledgeSkill()

    async def full_develop_pipeline(
        self,
        requirement: str,
        project_dir: str = "."
    ) -> dict:
        """
        完整开发流水线

        阶段：
        1. 记忆加载 - 从 memory 加载相关经验
        2. 上下文注入 - context_refresher 注入目标
        3. 规划分解 - agency 多角色协作规划
        4. 代码实现 - code_writer + file_utils
        5. 测试验证 - test_runner
        6. 经验归档 - memory 记录经验
        """
        pipeline_result = {
            "stages": [],
            "success": True,
            "errors": []
        }

        try:
            # Stage 1: 记忆加载
            stage1 = await self._stage_memory_load(requirement)
            pipeline_result["stages"].append(stage1)

            # Stage 2: 上下文注入
            stage2 = await self._stage_context_inject(
                requirement,
                stage1.get("data", {}).get("memories", [])
            )
            pipeline_result["stages"].append(stage2)

            # Stage 3: 多角色规划
            stage3 = await self._stage_agency_plan(requirement)
            pipeline_result["stages"].append(stage3)

            # Stage 4: 代码实现
            stage4 = await self._stage_code_implement(
                stage3.get("data", {}).get("plan"),
                project_dir
            )
            pipeline_result["stages"].append(stage4)

            # Stage 5: 测试验证
            stage5 = await self._stage_test_verify(
                stage4.get("data", {}).get("files", []),
                project_dir
            )
            pipeline_result["stages"].append(stage5)

            # Stage 6: 经验归档
            stage6 = await self._stage_memory_archive(
                requirement,
                pipeline_result
            )
            pipeline_result["stages"].append(stage6)

        except Exception as e:
            pipeline_result["success"] = False
            pipeline_result["errors"].append(str(e))

        return pipeline_result

    async def _stage_memory_load(self, requirement: str) -> dict:
        """阶段1: 从记忆加载相关经验"""
        # 使用联想式记忆搜索
        results = await self.memory.associative_search(
            query=requirement,
            mode="semantic_similarity",
            limit=5
        )

        return {
            "stage": "memory_load",
            "success": True,
            "data": {
                "memories": results.get("data", {}).get("results", []),
                "count": len(results.get("data", {}).get("results", []))
            }
        }

    async def _stage_context_inject(self, requirement: str, memories: list) -> dict:
        """阶段2: 上下文保鲜注入"""
        # 创建模拟对话历史
        conversation_history = [
            {"role": "user", "content": requirement}
        ]

        # 注入上下文
        injected = await self.context.inject_context(
            session_id="develop",
            recent_turns=conversation_history
        )

        return {
            "stage": "context_inject",
            "success": True,
            "data": {
                "injected_context": injected,
                "goal": requirement
            }
        }

    async def _stage_agency_plan(self, requirement: str) -> dict:
        """阶段3: agency 多角色协作规划"""
        # 使用 agency_orchestrator 的规划能力
        workflow = await self.agency.compose_workflow(
            description=f"需求: {requirement}\n角色: system-architect, product-manager, tech-lead",
            provider="claude-code"
        )

        return {
            "stage": "agency_plan",
            "success": True,
            "data": {
                "plan": workflow,
                "workflow_path": workflow.get("data", {}).get("workflow_path")
            }
        }

    async def _stage_code_implement(self, plan: dict, project_dir: str) -> dict:
        """阶段4: 代码实现"""
        files_created = []

        # 执行计划中的代码任务
        # ... (调用 code_writer 和 file_utils)

        return {
            "stage": "code_implement",
            "success": True,
            "data": {
                "files": files_created,
                "count": len(files_created)
            }
        }

    async def _stage_test_verify(self, files: list, project_dir: str) -> dict:
        """阶段5: 测试验证"""
        test_result = await self.test_runner.run_tests(
            path=project_dir,
            pattern="test_*.py"
        )

        return {
            "stage": "test_verify",
            "success": test_result.get("success", False),
            "data": test_result
        }

    async def _stage_memory_archive(self, requirement: str, pipeline_result: dict) -> dict:
        """阶段6: 经验归档到记忆"""
        # 保存开发经验
        experience = f"""
        开发需求: {requirement}
        结果: {'成功' if pipeline_result['success'] else '失败'}
        阶段: {len(pipeline_result['stages'])}
        错误: {', '.join(pipeline_result.get('errors', []))}
        """

        await self.memory.save_knowledge(
            topic="开发经验",
            content=experience,
            source="develop_pipeline"
        )

        return {
            "stage": "memory_archive",
            "success": True,
            "data": {"archived": True}
        }
```

### 4.4 健康监控全链路联动

```python
# core/skill_chain/health_monitor_chain.py
"""
健康监控全链路联动
"""

class HealthMonitorChain:
    """
    健康监控全链路联动

    联动机制：
    1. health_monitor 监控所有技能健康分
    2. 技能健康分 → memory (记忆衰减)
    3. 循环检测 → self_improver (自修复)
    4. 健康分下降 → agency (健康优化工作流)
    """

    def __init__(self):
        self.health = HealthMonitorSkill()
        self.memory = MemorySkill()
        self.self_improver = SelfImproverSkill()
        self.agency = AgencyOrchestrator()
        self.governance = Governance()

    async def monitor_and_recover(self) -> dict:
        """
        监控并自动恢复

        流程：
        1. 检查系统健康
        2. 检测技能健康分
        3. 检测依赖循环
        4. 自动恢复
        """
        result = {
            "system_health": None,
            "skill_health": {},
            "cycles_detected": [],
            "recoveries": []
        }

        # 1. 系统健康检查
        result["system_health"] = await self.health.check_health()

        # 2. 技能健康分监控
        for skill_name in self.governance.health_scores:
            score = self.governance.get_health_score(skill_name)
            result["skill_health"][skill_name] = score

            # 3. 检测循环
            if self.governance.get_cycle_status(skill_name):
                result["cycles_detected"].append(skill_name)

            # 4. 技能健康分异常 → 记忆衰减类比
            if score < 0.5:
                await self._apply_decay_to_skill(skill_name, score)

            # 5. 技能完全失效 → 自改进
            if score < 0.3:
                recovery = await self._auto_recover_skill(skill_name)
                result["recoveries"].append(recovery)

        return result

    async def _apply_decay_to_skill(self, skill_name: str, score: float):
        """技能健康分低 → 类比记忆衰减"""
        # 发布记忆衰减事件
        bus = get_event_bus()
        await bus.publish(
            "health.degraded",
            {
                "skill": skill_name,
                "score": score,
                "action": "reduce_priority"
            },
            source="health_monitor"
        )

    async def _auto_recover_skill(self, skill_name: str) -> dict:
        """技能失效 → 自改进恢复"""
        recovery = await self.self_improver.start_upgrade(
            plan_file=f"docs/recovery/{skill_name}_recovery.md",
            phase="phase_1",
            max_iterations=10
        )

        return {
            "skill": skill_name,
            "recovery": recovery,
            "triggered_by": "health_check"
        }
```

---

## 五、中间件链集成

### 5.1 联动中间件

```python
# core/middleware/skill_chain_middleware.py
"""
技能联动中间件
"""

class SkillChainMiddleware(AgentMiddleware):
    """
    技能联动中间件

    功能：
    1. 检测技能调用链
    2. 触发联动逻辑
    3. 事件驱动编排
    """

    def __init__(self):
        self.chains = {
            "memory_context": MemoryContextChain(),
            "error_self_improve": ErrorSelfImproveChain(),
            "develop_pipeline": DevelopPipelineChain(),
            "health_monitor": HealthMonitorChain(),
        }

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 分析用户意图
        intent = self._analyze_intent(ctx.user_input)

        # 2. 检测需要的联动链
        chain = self._select_chain(intent)

        if chain:
            # 3. 执行联动链
            result = await chain.execute(ctx)
            ctx.metadata["chain_result"] = result

        # 4. 执行主流程
        return await next_handler()

    def _analyze_intent(self, user_input: str) -> str:
        """分析用户意图"""
        keywords = {
            "develop_pipeline": ["开发", "实现", "代码", "创建"],
            "error_self_improve": ["修复", "错误", "bug", "问题"],
            "memory_context": ["记住", "回忆", "之前", "偏好"],
            "health_monitor": ["健康", "监控", "状态"],
        }

        for chain_name, kws in keywords.items():
            if any(kw in user_input for kw in kws):
                return chain_name

        return "default"

    def _select_chain(self, intent: str):
        """选择联动链"""
        return self.chains.get(intent)
```

### 5.2 事件订阅中间件

```python
# core/middleware/event_subscription_middleware.py
"""
事件订阅中间件
"""

class EventSubscriptionMiddleware(AgentMiddleware):
    """
    事件订阅中间件

    功能：
    1. 注册技能事件监听
    2. 事件触发技能联动
    3. 发布执行结果事件
    """

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._handlers = {}

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 注册事件监听
        self._register_handlers(ctx.session_id)

        # 2. 执行主流程
        result = await next_handler()

        # 3. 发布完成事件
        await self._publish_completion(ctx, result)

        return result

    def _register_handlers(self, session_id: str):
        """注册事件处理器"""
        self.bus.subscribe(
            "test.failed",
            self._create_handler("test.failed", session_id)
        )
        self.bus.subscribe(
            "skill.failed",
            self._create_handler("skill.failed", session_id)
        )
```

---

## 六、向后兼容设计

### 6.1 现有功能保留清单

| 功能 | 保留方式 | 说明 |
|------|---------|------|
| memory skill.json | 完全保留 | 11个工具全部可用 |
| context_refresher | 完全保留 | GSD保鲜机制不变 |
| agency_orchestrator | 完全保留 | 174角色/工作流不变 |
| self_improver | 完全保留 | 自改进逻辑不变 |
| error_knowledge | 完全保留 | 错误分类不变 |
| 所有 MCP 工具 | 完全保留 | 通过 SkillHandler 代理 |

### 6.2 新旧接口桥接

```python
# core/bridge/legacy_skill_bridge.py
"""
新旧技能接口桥接
"""

class LegacySkillBridge:
    """
    保留现有技能接口，同时提供新的联动接口
    """

    def __init__(self):
        # 现有技能实例
        self.memory = MemorySkill()
        self.context = ContextRefresher()
        self.agency = AgencyOrchestrator()

        # 新联动链
        self.chain = MemoryContextChain()

    # ========== 保留原有接口 ==========

    async def memory_save(self, session_id: str, role: str, content: str):
        """原有接口：保存对话"""
        return await self.memory.save_conversation(session_id, role, content)

    async def context_inject(self, session_id: str, recent_turns: list):
        """原有接口：注入上下文"""
        return await self.context.inject_context(session_id, recent_turns)

    # ========== 新增联动接口 ==========

    async def smart_context_inject(self, query: str, session_id: str):
        """新接口：智能上下文注入（联动版）"""
        return await self.chain.smart_search_and_inject(query, session_id)
```

---

## 七、实施优先级

### 7.1 联动优先级矩阵

| 联动链 | 用户价值 | 技术难度 | 优先级 | 周期 |
|--------|---------|---------|--------|------|
| 记忆↔上下文保鲜 | 高 | 低 | P0 | 1周 |
| 错误↔自改进 | 高 | 中 | P0 | 2周 |
| 开发流水线 | 高 | 高 | P1 | 3周 |
| 健康监控 | 中 | 中 | P1 | 2周 |
| 中间件集成 | 高 | 高 | P1 | 2周 |

### 7.2 实施步骤

**Step 1: 记忆↔上下文保鲜联动（1周）**
1. 实现 MemoryContextChain
2. 新增 memory.extracted 事件
3. 测试联动流程

**Step 2: 错误↔自改进联动（2周）**
1. 实现 ErrorSelfImproveChain
2. 新增错误自动修复工作流
3. 测试错误自愈

**Step 3: 开发流水线联动（3周）**
1. 实现 DevelopPipelineChain
2. 6阶段完整流程
3. 测试端到端开发

**Step 4: 健康监控联动（2周）**
1. 实现 HealthMonitorChain
2. 技能健康分监控
3. 自动恢复机制

**Step 5: 中间件集成（2周）**
1. SkillChainMiddleware
2. EventSubscriptionMiddleware
3. 与 AgentLoop 集成

---

## 八、总结

### 8.1 核心价值

1. **功能复用**：所有现有技能完整保留，无废弃风险
2. **有机联动**：功能之间深度连接，形成 1+1>2 的效果
3. **事件驱动**：松耦合架构，通过事件总线解耦
4. **闭环自愈**：错误捕获 → 自改进 → 验证 → 经验归档

### 8.2 联动效果

| 场景 | 联动前 | 联动后 |
|------|--------|--------|
| 长对话目标遗忘 | 手动提醒 | 自动保鲜 |
| 错误修复 | 手动定位 | 自动修复闭环 |
| 开发经验 | 手动记录 | 自动归档 |
| 技能异常 | 手动发现 | 自动监控恢复 |

### 8.3 下一步

1. 实现 MemoryContextChain 作为第一个联动链
2. 与 AgentLoop 中间件架构集成
3. 持续迭代优化联动逻辑

---

#功能联动 #技能联动 #事件驱动 #自改进闭环 #Plector
