# Plector 技能与架构增强方案

> 来源：Hermes Agent / DeerFlow / OpenClaw 对比研究
> 制定日期：2026-04-19

---

## 一、从开源项目学到的关键经验

### 1.1 Hermes Agent 的启示

| 经验 | Plector 当前 | 增强方向 |
|------|-------------|---------|
| **FTS5 全文搜索** | SQLite 基础存储 | 引入全文索引 |
| **多终端后端** | 单一本地执行 | Docker/SSH 后端 |
| **多平台网关** | WebSocket 单一 | 抽象为多渠道网关 |
| **自改进机制** | 无 | 技能自动生成 |

### 1.2 DeerFlow 的启示

| 经验 | Plector 当前 | 增强方向 |
|------|-------------|---------|
| **中间件链** | 事件驱动 | 中间件架构 |
| **子代理池** | agency DAG | 并行子代理执行 |
| **记忆提取** | 手动保存 | LLM 自动抽取 |
| **上下文压缩** | 无 | Token 限制触发压缩 |

### 1.3 OpenClaw 的启示

| 经验 | Plector 当前 | 增强方向 |
|------|-------------|---------|
| **多智能体隔离** | 单 Agent | 工作区隔离 |
| **优先级路由** | 技能分发 | Binding 路由 |
| **配置分离** | skill.json | AGENTS/SOUL/USER |
| **命令系统** | 基础对话 | 斜杠命令 |

---

## 二、架构增强方案

### 2.1 目标架构

```
┌─────────────────────────────────────────────────────────┐
│                 Plector 增强后架构                       │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  渠道网关 (ChannelGateway)                          ││
│  │  • WebSocket (已有)                                ││
│  │  • 预留: Telegram/Discord 适配器                   ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  中间件链 (MiddlewareChain)                        ││
│  │  1. ThreadDataMiddleware (工作区隔离)              ││
│  │  2. MemoryMiddleware (记忆提取)                    ││
│  │  3. SummarizationMiddleware (上下文压缩)           ││
│  │  4. ToolValidationMiddleware (参数验证)            ││
│  │  5. LoggingMiddleware (审计日志)                   ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  多智能体支持 (MultiAgent)                          ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐          ││
│  │  │Agent 1 │  │Agent 2 │  │Agent N │          ││
│  │  │(工作区) │  │(工作区) │  │(工作区) │          ││
│  │  └─────────┘  └─────────┘  └─────────┘          ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  执行层                                            ││
│  │  • AgentLoop (主循环)                             ││
│  │  • SubagentPool (子代理池)                         ││
│  │  • agency_orchestrator (DAG 工作流)               ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  技能与工具层                                      ││
│  │  • skill_registry                                 ││
│  │  • mcp_client                                    ││
│  │  • tool_registry                                  ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 中间件架构实现

```python
# core/middleware.py
from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from dataclasses import dataclass

@dataclass
class AgentContext:
    """Agent 执行上下文"""
    session_id: str
    workspace_id: str
    messages: list[dict]
    tools: list[dict]
    memory: dict = {}
    metadata: dict = {}


class AgentMiddleware(ABC):
    """中间件基类"""

    @abstractmethod
    async def process(
        self,
        ctx: AgentContext,
        next_handler: Callable[[], Awaitable[dict]]
    ) -> dict:
        """处理上下文，可选择调用 next_handler"""
        pass


class MiddlewareChain:
    """中间件链"""

    def __init__(self):
        self.middlewares: list[AgentMiddleware] = []

    def use(self, middleware: AgentMiddleware):
        """注册中间件"""
        self.middlewares.append(middleware)

    async def execute(self, ctx: AgentContext) -> dict:
        """执行中间件链"""

        async def chain(index: int) -> dict:
            if index >= len(self.middlewares):
                return await self._execute_agent(ctx)

            middleware = self.middlewares[index]
            return await middleware.process(ctx, lambda: chain(index + 1))

        return await chain(0)

    async def _execute_agent(self, ctx: AgentContext) -> dict:
        """执行实际的 Agent 逻辑"""
        # AgentLoop 执行代码
        pass


# 内置中间件实现

class ThreadDataMiddleware(AgentMiddleware):
    """工作区隔离中间件"""

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 创建/加载工作区
        workspace = await self.workspace_manager.get(ctx.workspace_id)

        # 2. 注入工作区配置
        ctx.metadata["workspace"] = workspace

        # 3. 执行
        return await next_handler()


class MemoryMiddleware(AgentMiddleware):
    """记忆提取中间件"""

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 执行 Agent
        result = await next_handler()

        # 2. 对话结束，触发记忆提取
        if ctx.metadata.get("conversation_end"):
            await self.memory_extractor.extract(ctx)

        return result


class SummarizationMiddleware(AgentMiddleware):
    """上下文压缩中间件"""

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 检查 Token 限制
        if self._should_summarize(ctx):
            ctx.messages = await self._summarize(ctx.messages)

        return await next_handler()

    def _should_summarize(self, ctx: AgentContext) -> bool:
        tokens = estimate_tokens(ctx.messages)
        max_tokens = get_context_limit(ctx.metadata.get("model", "gpt-4o"))
        return tokens > max_tokens * 0.8
```

---

## 三、技能系统增强

### 3.1 混合技能格式

```python
# 保留 skill.json + 增加 SKILL.md 支持
class HybridSkillLoader:
    """混合技能加载器"""

    async def load_skill(self, skill_path: Path) -> Skill:
        skill_json = skill_path / "skill.json"
        skill_md = skill_path / "SKILL.md"

        metadata = {}
        if skill_json.exists():
            metadata = json.loads(skill_json.read_text())

        content = ""
        if skill_md.exists():
            content = skill_md.read_text()

        return Skill(
            name=metadata.get("name", skill_path.name),
            version=metadata.get("version", "1.0.0"),
            tier=metadata.get("tier", "tier_2_functional"),
            triggers=metadata.get("triggers", self._parse_triggers(content)),
            tools=self._parse_tools(metadata),
            content=content,  # SKILL.md 内容用于提示注入
            implementation=self._load_implementation(skill_path),
        )

    def _parse_triggers(self, content: str) -> list[str]:
        """从 SKILL.md 提取触发词"""
        match = re.search(r"## Triggers\n(.*?)(?:\n##|\Z)", content, re.DOTALL)
        if match:
            triggers_section = match.group(1)
            return re.findall(r"- (.+)", triggers_section)
        return []
```

### 3.2 技能热更新

```python
# core/skill_hot_reload.py
import asyncio
from pathlib import Path
from watchdog.observers import Observer

class SkillHotReload:
    """技能热更新"""

    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry
        self.observer = Observer()
        self.debounce_seconds = 1.0

    def start(self):
        """启动文件监控"""
        for skill_name, skill_data in self.registry.skills.items():
            skill_path = skill_data["path"]
            self.observer.schedule(
                self._create_handler(skill_name),
                str(skill_path),
                recursive=True
            )
        self.observer.start()

    def _create_handler(self, skill_name: str):
        """创建事件处理器"""
        async def on_changed(event):
            if event.is_directory:
                return

            # 防抖
            await asyncio.sleep(self.debounce_seconds)

            # 重新加载
            await self.registry.reload_skill(skill_name)
            logger.info(f"技能 {skill_name} 已热更新")

        return FileSystemEventHandler(on_modified=on_changed)
```

---

## 四、记忆系统增强

### 4.1 LLM 自动记忆提取

```python
# memory/llm_extractor.py
class LLMExtractor:
    """LLM 驱动的记忆提取"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def extract(self, conversation: list[Message], user_id: str) -> MemoryData:
        """从对话中提取记忆"""

        extraction_prompt = f"""
        分析以下对话，提取用户信息：

        对话：
        {self._format_conversation(conversation)}

        提取以下内容（JSON 格式）：

        {{
            "user_context": {{
                "work": "用户的工作领域",
                "goals": ["目标1", "目标2"],
                "constraints": ["约束1", "约束2"]
            }},
            "facts": [
                {{"fact": "事实描述", "confidence": 0.95}}
            ],
            "preferences": ["偏好1", "偏好2"]
        }}
        """

        raw_json = await self.llm.complete_json(extraction_prompt)

        memory_data = MemoryData.parse(raw_json)

        # 存储到数据库
        await self._store_memory(user_id, memory_data)

        return memory_data

    async def _store_memory(self, user_id: str, data: MemoryData):
        """存储记忆到数据库"""
        async with self.db.transaction():
            # 更新上下文
            await self.db.execute(
                """
                INSERT INTO user_context (user_id, work, goals, constraints)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE
                """,
                user_id, data.work, data.goals, data.constraints
            )

            # 添加新事实
            for fact in data.facts:
                await self.db.execute(
                    """
                    INSERT INTO facts (user_id, fact, confidence)
                    VALUES ($1, $2, $3)
                    """,
                    user_id, fact["fact"], fact["confidence"]
                )
```

### 4.2 FTS5 全文搜索

```python
# memory/fts_search.py
class FTSSearch:
    """SQLite FTS5 全文搜索"""

    def init_schema(self, db):
        """初始化 FTS5 表"""
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(
                content,
                topic,
                tags,
                session_id,
                content='memories',
                content_rowid='id'
            )
        """)

        # 触发器保持同步
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, topic, tags, session_id)
                VALUES (new.id, new.content, new.topic, new.tags, new.session_id);
            END
        """)

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """全文搜索"""
        return self.db.execute("""
            SELECT m.*, fts.rank, fts.bm25() as score
            FROM memories m
            JOIN memories_fts fts ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (query, limit)).fetchall()
```

---

## 五、多智能体支持

### 5.1 工作区隔离

```python
# core/workspace.py
class Workspace:
    """工作区隔离"""

    def __init__(self, workspace_id: str, base_path: Path):
        self.workspace_id = workspace_id
        self.base_path = base_path

        # 配置文件
        self.agents_md = base_path / "AGENTS.md"
        self.soul_md = base_path / "SOUL.md"
        self.user_md = base_path / "USER.md"

        # 技能目录
        self.skills_dir = base_path / "skills"

        # 会话存储
        self.sessions_db = base_path / "data" / "sessions.db"

    @classmethod
    def create(cls, workspace_id: str) -> "Workspace":
        """创建新工作区"""
        base_path = Path(f"~/.openclaw/workspaces/{workspace_id}").expanduser()

        # 创建目录结构
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / "skills").mkdir(exist_ok=True)
        (base_path / "data").mkdir(exist_ok=True)

        return cls(workspace_id, base_path)


class WorkspaceManager:
    """工作区管理器"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.cache: dict[str, Workspace] = {}

    async def get(self, workspace_id: str) -> Workspace:
        """获取工作区"""
        if workspace_id not in self.cache:
            path = self.base_path / workspace_id
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            self.cache[workspace_id] = Workspace(workspace_id, path)

        return self.cache[workspace_id]

    async def load_config(self, workspace: Workspace) -> AgentConfig:
        """加载工作区配置"""
        return AgentConfig(
            system_prompt=self._read_md(workspace.agents_md),
            personality=self._read_md(workspace.soul_md),
            memory=self._read_md(workspace.user_md),
            skills=self._discover_skills(workspace.skills_dir),
        )
```

### 5.2 优先级路由

```python
# core/router.py
class MultiAgentRouter:
    """多智能体优先级路由"""

    def __init__(self, bindings: list[Binding]):
        # 按优先级排序
        self.bindings = sorted(
            bindings,
            key=lambda b: self._priority(b),
            reverse=True  # 高优先级在前
        )

    def _priority(self, binding: Binding) -> int:
        """计算绑定优先级"""
        score = 0
        if binding.peer:
            score += 100  # peer 精确匹配
        if binding.parent_peer:
            score += 90   # 线程继承
        if binding.guild and binding.roles:
            score += 80   # guild + roles
        if binding.guild:
            score += 70   # guild 级别
        if binding.team:
            score += 60   # team 级别
        if binding.account:
            score += 50   # account 级别
        if binding.channel:
            score += 40   # channel 级别
        return score

    async def route(self, message: Message) -> str:
        """路由到对应的工作区"""
        for binding in self.bindings:
            if self._match(binding, message):
                return binding.workspace_id

        return "default"  # 回退到默认
```

---

## 六、执行计划

### Phase 1：基础设施（1-2周）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 中间件框架 | 实现 MiddlewareChain 基类 | P0 |
| 基础中间件 | ThreadData, Logging, ToolValidation | P0 |
| FTS5 搜索 | SQLite 全文索引 | P1 |
| 技能热更新 | 文件监控 + 防抖重载 | P1 |

### Phase 2：记忆增强（2-3周）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| LLM 记忆提取 | 自动抽取上下文和事实 | P1 |
| 上下文压缩 | Token 限制触发压缩 | P1 |
| 记忆注入 | 提示词注入 top facts | P2 |

### Phase 3：多智能体（3-4周）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 工作区隔离 | Workspace 类 | P2 |
| 优先级路由 | Binding 路由机制 | P2 |
| 多 Agent 支持 | 扩展 AgentLoop | P2 |

### Phase 4：渠道扩展（持续）

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 渠道抽象 | ChannelGateway 基类 | P2 |
| Telegram 适配器 | 消息网关支持 | P3 |
| Discord 适配器 | 消息网关支持 | P3 |

---

## 七、参考项目

| 项目 | 主要参考点 |
|------|-----------|
| Hermes Agent | FTS5、多终端后端、多平台网关 |
| DeerFlow | 中间件链、子代理池、LLM 记忆提取 |
| OpenClaw | 工作区隔离、优先级路由、配置分离 |
