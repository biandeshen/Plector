# DeerFlow 深度分析

> 来源：字节跳动 GitHub + 官方文档
> 研究日期：2026-04-19

---

## 一、项目定位

**DeerFlow** 是字节跳动开发的开源超级代理框架（Super Agent Harness），基于 LangGraph 和 LangChain 构建，具备编排子代理、记忆系统和沙箱环境的能力。

### 核心特性
- **LangGraph 工作流**：DAG 状态机执行
- **子代理并行**：最多 3 个子代理/轮次
- **中间件链**：9 个中间件顺序执行
- **多渠道支持**：Web、Telegram、Slack、飞书
- **沙箱执行**：本地、Docker、Kubernetes

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (Port 2026)                   │
│            统一反向代理 / 请求路由                        │
└─────────────────────────────────────────────────────────┘
        │                    │                    │
        ↓                    ↓                    ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ LangGraph Svr │    │  Gateway API  │    │   Frontend   │
│  (Port 2024)  │    │  (Port 8001)  │    │   (Next.js)  │
│               │    │               │    │               │
│ • Agent 执行   │    │ • 模型管理     │    │ • 对话 UI     │
│ • 线程管理    │    │ • MCP 集成    │    │ • 文件上传    │
│ • SSE 流式    │    │ • 技能管理    │    │ • 结果展示    │
└───────────────┘    │ • 记忆存储    │    └───────────────┘
                     │ • 工件管理    │
                     └───────────────┘
```

### 2.2 Lead Agent 组件

```python
# make_lead_agent(config) 创建的 Lead Agent
LeadAgent {
    model: DynamicModelSelection      # 动态模型选择
    middlewares: [                     # 中间件链
        ThreadDataMiddleware,          # 线程隔离目录
        UploadsMiddleware,             # 文件注入
        SandboxMiddleware,            # 沙箱获取
        SummarizationMiddleware,       # 上下文压缩
        TodoListMiddleware,            # 任务跟踪
        TitleMiddleware,               # 标题生成
        MemoryMiddleware,              # 记忆提取
        ViewImageMiddleware,           # 视觉注入
        ClarificationMiddleware        # 澄清拦截
    ]
    tools: [Sandbox, MCP, Community, Built-in]
    subagent_delegation: SubagentPool
    system_prompt: SkillsInjector + MemoryContext
}
```

---

## 三、中间件链详解

### 3.1 中间件执行顺序

```
┌─────────────────────────────────────────────────────────┐
│                  9 个中间件严格顺序执行                    │
│                                                         │
│  1. ThreadDataMiddleware                                │
│     └── 创建线程隔离目录 ~/deer-flow/threads/{thread_id}/ │
│                                                         │
│  2. UploadsMiddleware                                   │
│     └── 将上传文件注入对话上下文                          │
│                                                         │
│  3. SandboxMiddleware                                   │
│     └── 获取沙箱执行环境                                 │
│                                                         │
│  4. SummarizationMiddleware                             │
│     └── Token 接近限制时触发上下文压缩                    │
│                                                         │
│  5. TodoListMiddleware                                 │
│     └── 计划模式多步骤任务跟踪                           │
│                                                         │
│  6. TitleMiddleware                                     │
│     └── 首轮对话后自动生成标题                           │
│                                                         │
│  7. MemoryMiddleware                                   │
│     └── 异步记忆提取入队                                 │
│                                                         │
│  8. ViewImageMiddleware                                 │
│     └── 视觉模型图像数据注入                             │
│                                                         │
│  9. ClarificationMiddleware  ← 必须最后                   │
│     └── 拦截澄清请求                                     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 中间件实现示例

```python
class SandboxMiddleware:
    async def process(self, context: AgentContext, next_handler):
        """获取沙箱执行环境"""

        # 1. 分配沙箱资源
        sandbox = await self.sandbox_pool.acquire(
            timeout=timedelta(minutes=15)
        )

        try:
            # 2. 注入沙箱工具到上下文
            context.tools.append(sandbox.get_tools())

            # 3. 挂载虚拟路径
            context.mounts = {
                "/mnt/workspace": sandbox.workspace_path,
                "/mnt/uploads": sandbox.uploads_path,
                "/mnt/outputs": sandbox.outputs_path,
                "/mnt/skills": "deer-flow/skills/",
            }

            # 4. 执行后续处理
            result = await next_handler()

            return result

        finally:
            # 5. 释放沙箱
            await self.sandbox_pool.release(sandbox)


class SummarizationMiddleware:
    async def should_summarize(self, messages: list) -> bool:
        """判断是否需要压缩上下文"""
        total_tokens = estimate_tokens(messages)
        max_tokens = get_model_context_limit(self.model)

        return total_tokens > max_tokens * 0.8  # 80% 阈值

    async def summarize(self, messages: list) -> list:
        """使用 LLM 生成摘要"""
        prompt = f"""
        压缩以下对话历史，保留关键信息：

        {messages}

        输出简洁摘要，格式：
        - 核心话题：[主题]
        - 关键结论：[结论]
        - 待处理：[待办]
        """

        summary = await self.llm.complete(prompt)
        return [SystemMessage(content=summary)]
```

---

## 四、子代理系统

### 4.1 子代理架构

```
┌─────────────────────────────────────────────────────────┐
│                     主代理 (Lead Agent)                  │
│                                                         │
│  1. 接收用户请求                                         │
│  2. 分解任务为子任务                                     │
│  3. 调用 task() 工具派发子代理                           │
│  4. 收集子代理结果                                       │
│  5. 综合输出                                             │
│                                                         │
│         ┌─────────────┐                                │
│         │  task()     │                                │
│         │   工具      │                                │
│         └──────┬──────┘                                │
│                │                                        │
│     ┌─────────┼─────────┐                              │
│     ↓         ↓         ↓                              │
│ ┌───────┐ ┌───────┐ ┌───────┐                          │
│ │子代理1│ │子代理2│ │子代理3│  ← 最多3个并行             │
│ │(通用) │ │(Bash) │ │(搜索) │                          │
│ └───┬───┘ └───┬───┘ └───┬───┘                          │
│     │         │         │                              │
│     └─────────┴─────────┘                              │
│               ↓                                         │
│         结果收集 + SSE 上报                             │
└─────────────────────────────────────────────────────────┘
```

### 4.2 子代理执行流程

```python
class SubagentPool:
    def __init__(self, max_concurrent: int = 3, timeout: int = 900):
        self.max_concurrent = max_concurrent  # 每轮最多3个
        self.timeout = timeout  # 15分钟超时
        self.executors: dict[str, Future] = {}

    async def execute(self, task_config: TaskConfig) -> TaskResult:
        """执行子代理任务"""

        # 1. 创建执行器
        executor = self.create_executor(task_config)

        # 2. 提交到后台线程池
        future = self.thread_pool.submit(executor.run)
        self.executors[task_config.id] = future

        # 3. 轮询完成状态
        while not future.done():
            status = future.get_status()

            # SSE 上报进度
            await self.sse_manager.emit({
                "type": "subagent_progress",
                "task_id": task_config.id,
                "status": status,
            })

            await asyncio.sleep(1)

        # 4. 获取结果
        return future.result()


# 主代理中的 task() 工具
@tool
async def task(description: str, agent_type: str) -> str:
    """派发子代理任务"""

    task_config = TaskConfig(
        description=description,
        agent_type=agent_type,
        timeout=900,  # 15分钟
    )

    result = await subagent_pool.execute(task_config)
    return result.output
```

### 4.3 内置子代理类型

| 类型 | 工具集 | 用途 |
|------|--------|------|
| `general-purpose` | 全部工具 | 通用任务 |
| `bash` | shell | 命令执行 |

---

## 五、记忆系统

### 5.1 记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                    DeerFlow 记忆架构                      │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  MemoryMiddleware                                   ││
│  │  └── 对话结束时触发                                  ││
│  │  └── 异步处理，不阻塞主流程                          ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  LLM Extraction                                    ││
│  │  └── 分析对话内容                                   ││
│  │  └── 提取：上下文/事实/偏好                         ││
│  │  └── 生成置信度评分                                 ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  JSON Storage                                      ││
│  │  └── 存储路径：threads/{thread_id}/memory.json     ││
│  │  └── mtime 缓存失效                                ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Prompt Injection                                  ││
│  └── 从 memory.json 加载 top facts                    │
│      └── 注入系统提示词                                │
│      └── 格式：[事实] (置信度: xx%)                    │
│      └── 数量：top 10                                  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 记忆数据结构

```json
{
  "user_context": {
    "work": "软件开发",
    "goals": ["学习 AI", "完成项目"],
    "constraints": ["时间有限", "预算有限"]
  },
  "facts": [
    {
      "fact": "用户偏好使用 Python",
      "confidence": 0.95,
      "source": "conversation_20260315"
    },
    {
      "fact": "用户对 AI Agent 感兴趣",
      "confidence": 0.88,
      "source": "conversation_20260316"
    }
  ],
  "history": [
    "讨论了 LangGraph 架构",
    "询问了子代理机制"
  ]
}
```

### 5.3 记忆提取流程

```python
class MemoryExtractor:
    async def extract(self, conversation: list[Message]) -> MemoryData:
        """从对话中提取记忆"""

        extraction_prompt = f"""
        分析以下对话，提取用户信息：

        对话：
        {conversation}

        提取以下内容：
        1. 用户上下文（工作、目标、约束）
        2. 关键事实（用户陈述的事实，带置信度）
        3. 对话历史摘要

        输出 JSON 格式：
        """

        raw_json = await self.llm.complete_json(extraction_prompt)

        # 防抖：批量处理减少 LLM 调用
        return self.parse_and_store(raw_json)
```

---

## 六、技能系统

### 6.1 技能目录结构

```
skills/
├── public/                    # 内置技能
│   ├── code_review/
│   │   └── SKILL.md
│   ├── research/
│   │   └── SKILL.md
│   └── presentation/
│       └── SKILL.md
│
└── custom/                   # 用户技能
    └── my_skill/
        └── SKILL.md
```

### 6.2 技能加载与注入

```python
class SkillsInjector:
    def discover_skills(self, skills_dir: Path) -> list[Skill]:
        """递归发现技能"""
        skills = []

        for skill_dir in skills_dir.rglob("SKILL.md"):
            skill = self.parse_skill(skill_dir)
            skills.append(skill)

        return skills

    def inject_into_system_prompt(
        self,
        skills: list[Skill],
        user_query: str
    ) -> str:
        """将技能注入系统提示"""

        # 1. 根据用户查询筛选相关技能
        relevant_skills = self.filter_skills(skills, user_query)

        # 2. 格式化技能内容
        skill_content = "\n\n".join([
            f"# {s.name}\n{s.content}"
            for s in relevant_skills
        ])

        # 3. 构建系统提示
        return f"""
        你有以下技能可用：

        {skill_content}

        用户请求：{user_query}
        """
```

---

## 七、沙箱执行

### 7.1 沙箱架构

```python
class SandboxPool:
    """沙箱资源池"""

    def __init__(self, mode: str = "local"):
        self.mode = mode  # local, docker, kubernetes

    async def acquire(self, timeout: timedelta) -> Sandbox:
        """获取沙箱实例"""

        if self.mode == "local":
            return LocalSandbox()
        elif self.mode == "docker":
            return await DockerSandbox.pool.acquire(timeout)
        elif self.mode == "kubernetes":
            return await K8sSandbox.pool.acquire(timeout)

    async def release(self, sandbox: Sandbox):
        """释放沙箱回池"""
        await sandbox.cleanup()
        await self.pool.release(sandbox)
```

### 7.2 虚拟路径映射

```python
# 线程隔离目录结构
~/deer-flow/threads/{thread_id}/
├── workspace/     # /mnt/workspace
├── uploads/       # /mnt/uploads
└── outputs/       # /mnt/outputs

# 映射规则
/mnt/workspace → threads/{thread_id}/workspace
/mnt/uploads   → threads/{thread_id}/uploads
/mnt/outputs   → threads/{thread_id}/outputs
/mnt/skills    → deer-flow/skills/
```

---

## 八、Plector 集成建议

### 8.1 引入中间件机制

```python
# Plector AgentLoop 中间件化
class AgentMiddleware(ABC):
    async def process(self, ctx: AgentContext, next_handler):
        return await next_handler()

class AgentLoop:
    def __init__(self):
        self.middlewares: list[AgentMiddleware] = []

    def use(self, middleware: AgentMiddleware):
        self.middlewares.append(middleware)

    async def execute(self, ctx: AgentContext):
        async def chain(index: int) -> Response:
            if index >= len(self.middlewares):
                return await self._execute_agent(ctx)

            middleware = self.middlewares[index]
            return await middleware.process(ctx, lambda: chain(index + 1))

        return await chain(0)


# 使用示例
agent = AgentLoop()
agent.use(ThreadDataMiddleware())
agent.use(SummarizationMiddleware())
agent.use(MemoryMiddleware())
```

### 8.2 子代理池实现

```python
# Plector agency_orchestrator 增强
class SubagentPool:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

    async def run_parallel(self, tasks: list[Task]) -> list[Result]:
        """并行执行子代理任务"""

        futures = [
            self.executor.submit(self.run_task, task)
            for task in tasks[:self.max_concurrent]
        ]

        results = []
        for future in as_completed(futures):
            results.append(future.result())

        return results
```

---

## 九、参考资源

- [DeerFlow GitHub](https://github.com/bytedance/deer-flow)
- [官方文档](https://github.com/bytedance/deer-flow#readme)
- [深度解析文章](https://www.sitepoint.com/deerflow-deep-dive-managing-longrunning-autonomous-tasks/)

#DeerFlow #字节跳动 #LangGraph #中间件
