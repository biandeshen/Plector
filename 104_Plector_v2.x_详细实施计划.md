# Plector v2.x 详细实施计划

> 基于深度技术分析和竞品对比研究的分阶段实施指南
> 版本：2.0
> 更新：2026-04-19

---

## 一、实施路线图概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Plector v2.x 实施路线图                               │
│                                                                             │
│  Q1 (4-6月)                    Q2 (7-9月)                    Q3 (10-12月)   │
│  ┌─────────────────┐           ┌─────────────────┐           ┌──────────────┐│
│  │ Phase 1         │           │ Phase 3         │           │ Phase 5      ││
│  │ 中间件框架       │           │ 多智能体支持     │           │ 渠道扩展      ││
│  │ 1. 中间件基类    │           │ 1. 工作区隔离    │           │ 1. Telegram  ││
│  │ 2. 基础中间件    │           │ 2. 优先级路由   │           │ 2. Discord   ││
│  │ 3. 技能沙箱     │           │ 3. 子代理池     │           │ 3. Webhook   ││
│  └────────┬────────┘           └────────┬────────┘           └──────┬───────┘│
│           │                             │                            │       │
│  ┌────────┴────────┐           ┌───────┴────────┐           ┌──────┴───────┐│
│  │ Phase 2         │           │ Phase 4         │           │ Phase 6       ││
│  │ 记忆系统增强     │           │ 安全加固        │           │ 前端增强      ││
│  │ 1. LLM 提取    │           │ 1. RBAC/ABAC   │           │ 1. 虚拟滚动  ││
│  │ 2. FTS5 搜索   │           │ 2. 输入输出验证 │           │ 2. 思考气泡  ││
│  │ 3. 上下文压缩  │           │ 3. 审计日志     │           │ 3. 代码增强  ││
│  └─────────────────┘           │ 4. 沙箱执行    │           └──────────────┘│
│                                └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘

预计总工期：9 个月（可并行推进）
```

---

## 二、Phase 1：中间件框架（4-6 周）

### 2.1 目标

建立可插拔的中间件架构，为后续功能扩展奠定基础。

### 2.2 任务分解

#### 任务 1.1：中间件框架实现（2 周）

| 子任务 | 说明 | 代码位置 | 工作量 |
|--------|------|---------|--------|
| 定义 AgentContext | 执行上下文数据结构 | `core/agent_context.py` | 1天 |
| 实现 MiddlewareChain | 中间件链管理器 | `core/middleware_chain.py` | 2天 |
| 实现 AgentMiddleware | 抽象基类 | `core/middleware.py` | 1天 |
| 集成到 AgentLoop | 替换现有流程 | `core/agent_loop.py` | 3天 |
| 单元测试 | 中间件链测试 | `tests/test_middleware.py` | 2天 |

```python
# core/agent_context.py
from pydantic import BaseModel
from typing import Optional

class AgentContext(BaseModel):
    """Agent 执行上下文"""
    session_id: str
    workspace_id: str = "default"
    user_id: Optional[str] = None
    messages: list[dict] = []
    tools: list[dict] = []
    memory: dict = {}
    metadata: dict = {}

    # 中间件可添加的字段
    system_prompt: str = ""
    security_context: dict = {}
    audit_context: dict = {}
```

#### 任务 1.2：基础中间件实现（2 周）

| 中间件 | 说明 | 优先级 |
|--------|------|--------|
| ThreadDataMiddleware | 工作区隔离 | P0 |
| LoggingMiddleware | 请求/响应日志 | P0 |
| SecurityMiddleware | 输入验证 | P1 |
| MemoryMiddleware | 记忆加载/提取 | P1 |

```python
# core/middleware/security.py
class SecurityMiddleware(AgentMiddleware):
    """安全检查中间件"""

    def __init__(self, sanitizer: InputSanitizer):
        self.sanitizer = sanitizer

    async def process(self, ctx: AgentContext, next_handler) -> dict:
        # 1. 检查用户输入
        for msg in ctx.messages:
            if msg.get("role") == "user":
                sanitized = self.sanitizer.sanitize(msg["content"])
                if not sanitized.is_clean:
                    ctx.metadata["security_warning"] = sanitized.violations

        # 2. 执行 Agent
        result = await next_handler()

        # 3. 验证输出
        if result.get("code"):
            validation = await code_validator.validate(result["code"])
            if not validation.passed:
                result["security_blocked"] = True

        return result
```

#### 任务 1.3：技能沙箱隔离（2 周）

| 子任务 | 说明 | 技术方案 |
|--------|------|---------|
| 进程池管理 | 技能隔离执行 | `multiprocessing.Pool` |
| 资源限制 | CPU/内存/超时 | `resource.setrlimit` |
| 文件系统隔离 | 临时目录隔离 | `tempfile.mkdtemp` |

```python
# core/skill_sandbox.py
import multiprocessing as mp
import resource

class SkillSandbox:
    """技能执行沙箱"""

    def __init__(self, max_workers: int = 4):
        self.pool = mp.Pool(max_workers)

    def execute(self, skill_module: str, method: str, params: dict) -> dict:
        """在独立进程中执行技能"""
        return self.pool.apply_async(
            _execute_in_process,
            args=(skill_module, method, params),
            kwds={"resource_limit": self.resource_limit}
        ).get(timeout=30)

def _execute_in_process(skill_module, method, params, resource_limit):
    # 设置资源限制
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))  # 5秒CPU
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))  # 512MB内存

    # 创建临时工作目录
    work_dir = tempfile.mkdtemp()

    # 执行技能
    try:
        return skill.execute(work_dir)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
```

### 2.3 验收标准

- 中间件链可正常执行
- 响应时间增加 < 5%
- 所有基础中间件单元测试通过
- 技能沙箱可隔离执行

---

## 三、Phase 2：记忆系统增强（6-8 周）

### 3.1 目标

实现 LLM 驱动的记忆提取和 FTS5 全文搜索。

### 3.2 任务分解

#### 任务 2.1：LLM 记忆提取（3 周）

| 子任务 | 说明 | 代码位置 |
|--------|------|---------|
| LLMExtractor | LLM 驱动的记忆提取 | `memory/llm_extractor.py` |
| MemoryMiddleware | 集成到中间件链 | `core/middleware/memory.py` |
| 记忆存储 | 提取结果存储 | `memory/store.py` |

```python
# memory/llm_extractor.py
class LLMExtractor:
    """LLM 驱动的记忆提取"""

    async def extract(self, conversation: list[Message], user_id: str) -> MemoryData:
        """
        从对话中提取关键记忆信息
        """
        prompt = f"""
        分析以下对话，提取用户的关键信息：

        对话：
        {self._format_conversation(conversation)}

        提取格式（JSON）：
        {{
            "user_context": {{
                "work": "工作领域",
                "goals": ["目标1", "目标2"],
                "constraints": ["约束1"]
            }},
            "facts": [
                {{"fact": "事实", "confidence": 0.95, "category": "fact"}}
            ],
            "preferences": [
                {{"preference": "偏好", "confidence": 0.85}}
            ]
        }}
        """
        return await self.llm.complete_json(prompt)
```

#### 任务 2.2：FTS5 全文搜索（2 周）

| 子任务 | 说明 | 代码位置 |
|--------|------|---------|
| FTSSchema | FTS5 表设计 | `memory/schema.py` |
| FTSSearch | 全文搜索实现 | `memory/fts_search.py` |
| HybridSearch | 混合检索 | `memory/hybrid_search.py` |

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
                user_id,
                content='memories',
                content_rowid='id'
            )
        """)

        # 触发器保持同步
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_fts_insert
            AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, topic, tags, user_id)
                VALUES (new.id, new.content, new.topic, new.tags, new.user_id);
            END
        """)

    def search(self, query: str, user_id: str = None, limit: int = 10) -> list[dict]:
        """全文搜索"""
        sql = """
            SELECT m.*, bm25() as score
            FROM memories m
            JOIN memories_fts fts ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
        """
        params = [query]
        if user_id:
            sql += " AND m.user_id = ?"
            params.append(user_id)
        sql += " ORDER BY score LIMIT ?"
        params.append(limit)
        return self.db.execute(sql, params).fetchall()
```

#### 任务 2.3：上下文压缩（1-2 周）

| 子任务 | 说明 | 技术方案 |
|--------|------|---------|
| Token 估算 | 计算消息 token 数 | tiktoken |
| 压缩触发 | 80% 阈值检测 | `SummarizationMiddleware` |
| 历史摘要 | LLM 生成摘要 | 保留关键信息 |

### 3.3 验收标准

- 记忆提取准确率 > 80%
- FTS5 搜索延迟 < 100ms
- 混合检索融合正确

---

## 四、Phase 3：多智能体支持（8-10 周）

### 4.1 目标

实现工作区隔离、优先级路由和子代理池。

### 4.2 任务分解

#### 任务 3.1：工作区隔离（3 周）

```python
# core/workspace.py
@dataclass
class Workspace:
    """工作区隔离"""
    workspace_id: str
    base_path: Path
    config: WorkspaceConfig

    # 配置文件
    agents_md: Path      # AGENTS.md - Agent 定义
    soul_md: Path        # SOUL.md - 性格配置
    user_md: Path        # USER.md - 用户记忆

    # 目录
    skills_dir: Path     # 技能目录
    data_dir: Path       # 数据目录

    @classmethod
    def create(cls, workspace_id: str) -> "Workspace":
        """创建新工作区"""
        base_path = Path(f"~/.plector/workspaces/{workspace_id}")
        base_path.mkdir(parents=True, exist_ok=True)
        # 创建默认配置
        ...

class WorkspaceManager:
    """工作区管理器"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.cache: dict[str, Workspace] = {}

    async def get(self, workspace_id: str) -> Workspace:
        """获取工作区"""
        if workspace_id not in self.cache:
            self.cache[workspace_id] = await self._load(workspace_id)
        return self.cache[workspace_id]
```

#### 任务 3.2：优先级路由（2-3 周）

```python
# core/router.py
class MultiAgentRouter:
    """多智能体优先级路由"""

    def _priority(self, binding: Binding) -> int:
        """计算绑定优先级"""
        score = 0
        if binding.peer: score += 100       # peer 精确匹配
        if binding.parent_peer: score += 90  # 线程继承
        if binding.guild and binding.roles: score += 80  # guild + roles
        if binding.guild: score += 70       # guild 级别
        if binding.team: score += 60         # team 级别
        if binding.account: score += 50      # account 级别
        if binding.channel: score += 40     # channel 级别
        return score

    async def route(self, message: Message) -> str:
        """路由到对应的工作区"""
        for binding in self.bindings:
            if self._match(binding, message):
                return binding.workspace_id
        return "default"
```

#### 任务 3.3：子代理池（3-4 周）

```python
# core/subagent_pool.py
class SubagentPool:
    """子代理并发池"""

    def __init__(self, max_agents: int = 5):
        self.max_agents = max_agents
        self.active: dict[str, AgentLoop] = {}
        self.queue: asyncio.Queue = asyncio.Queue()

    async def acquire(self, task_id: str) -> AgentLoop:
        """获取子代理"""
        if len(self.active) < self.max_agents:
            agent = AgentLoop()
            self.active[task_id] = agent
            return agent

        # 等待可用代理
        return await asyncio.wait_for(
            self.queue.get(),
            timeout=60.0
        )

    async def release(self, task_id: str):
        """释放子代理"""
        if task_id in self.active:
            del self.active[task_id]
        self.queue.task_done()
```

### 4.3 验收标准

- 工作区切换延迟 < 100ms
- 路由规则可配置、生效
- 支持 5+ 并发子代理

---

## 五、Phase 4：安全加固（6-8 周）

### 5.1 目标

实现零信任安全架构，满足企业级安全要求。

### 5.2 任务分解

#### 任务 4.1：RBAC/ABAC 实现（2-3 周）

```python
# security/rbac.py
class RBAC:
    """基于角色的访问控制"""

    ROLE_PERMISSIONS = {
        "user": {
            "memory:read", "skill:list", "file:read"
        },
        "developer": {
            "memory:*", "skill:*", "file:*", "tool:execute"
        },
        "admin": {"*"}  # 全权限
    }

    async def check_permission(
        self,
        subject: str,
        permission: str,
        resource: str = None
    ) -> bool:
        """检查权限"""
        roles = self.user_roles.get(subject, [])
        for role in roles:
            perms = self.ROLE_PERMISSIONS.get(role, set())
            if "*" in perms:
                return True
            if f"{permission}" in perms:
                if resource:
                    return await self.check_resource_policy(subject, permission, resource)
                return True
        return False
```

#### 任务 4.2：输入/输出验证（1-2 周）

```python
# security/input_sanitizer.py
class InputSanitizer:
    """输入清理器"""

    DANGEROUS_PATTERNS = [
        (r"os\.system\s*\(", "code_execution"),
        (r"exec\s*\(", "code_execution"),
        (r"eval\s*\(", "code_execution"),
        (r"ignore\s+(previous|all)\s+instructions", "prompt_injection"),
        (r"\.\.\/", "path_traversal"),
    ]

    def sanitize(self, content: str) -> SanitizedInput:
        """清理输入"""
        violations = []
        for pattern, name in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append({"type": name, "pattern": pattern})

        return SanitizedInput(
            cleaned=content,
            violations=violations,
            is_clean=len(violations) == 0
        )
```

#### 任务 4.3：审计日志（2 周）

```python
# security/audit_logger.py
class AuditLogger:
    """审计日志记录器"""

    async def log(self, event: AuditEvent):
        """记录审计事件"""
        await self.db.insert("audit_logs", {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type.value,
            "subject_id": event.subject_id,
            "action": event.action,
            "resource": event.resource,
            "result": event.result,
            "metadata": json.dumps(event.metadata)
        })

        # 高风险事件告警
        if self._should_alert(event):
            await self._send_alert(event)
```

#### 任务 4.4：沙箱执行（1-2 周）

```python
# security/sandbox.py
class SandboxExecutor:
    """沙箱执行器"""

    def __init__(self):
        self.docker_pool = DockerPool(max_size=5)

    async def execute(self, code: str, language: str) -> dict:
        """在沙箱中执行代码"""
        sandbox = await self.docker_pool.acquire()

        try:
            # 网络隔离
            sandbox.disable_network()

            # 资源限制
            sandbox.set_limits(cpu=50, memory="256m", timeout=30)

            # 执行
            return await sandbox.run(code, language)
        finally:
            await self.docker_pool.release(sandbox)
```

### 5.3 验收标准

- 所有高危操作都有权限检查
- 审计日志完整率 100%
- 通过安全扫描（无高危漏洞）

---

## 六、Phase 5：渠道扩展（6-8 周）

### 6.1 目标

抽象渠道层，支持多平台接入。

### 6.2 任务分解

#### 任务 5.1：ChannelGateway（2 周）

```python
# channels/gateway.py
class ChannelGateway:
    """渠道网关"""

    def __init__(self):
        self.channels: dict[str, ChannelAdapter] = {}

    def register(self, name: str, adapter: ChannelAdapter):
        """注册渠道适配器"""
        self.channels[name] = adapter

    async def connect(self, channel_name: str, config: dict):
        """连接渠道"""
        adapter = self.channels.get(channel_name)
        if not adapter:
            raise ValueError(f"Unknown channel: {channel_name}")
        await adapter.connect(config)

    async def send(self, channel_name: str, message: Message) -> Response:
        """发送消息"""
        adapter = self.channels.get(channel_name)
        return await adapter.send(message)
```

#### 任务 5.2：Telegram 适配器（2 周）

```python
# channels/telegram_adapter.py
class TelegramAdapter(ChannelAdapter):
    """Telegram 渠道适配器"""

    async def connect(self, config: dict):
        self.bot = Bot(token=config["token"])
        await self.bot.delete_webhook()

        # 启动轮询
        self.polling = asyncio.create_task(self._poll_updates())

    async def send(self, message: Message) -> Response:
        """发送消息"""
        await self.bot.send_message(
            chat_id=message.chat_id,
            text=message.text,
            parse_mode="Markdown"
        )
```

#### 任务 5.3：Discord 适配器（2-3 周）

```python
# channels/discord_adapter.py
class DiscordAdapter(ChannelAdapter):
    """Discord 渠道适配器"""

    async def connect(self, config: dict):
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_message(message):
            # 转发到 Agent
            response = await self.gateway.process(
                self._message_to_event(message)
            )
            # 发送回复
            await message.reply(response.text)
```

### 6.3 验收标准

- 新渠道接入工作量 < 1 天
- 消息延迟 < 500ms
- 支持消息格式转换

---

## 七、Phase 6：前端增强（持续）

### 7.1 目标

提升用户体验，增强可视化能力。

### 7.2 任务分解

#### 任务 6.1：虚拟滚动（2 周）

```vue
<!-- components/chat/VirtualMessageList.vue -->
<template>
  <VirtualScroller
    :items="messages"
    :item-size="estimatedItemSize"
    key-field="id"
  >
    <template #default="{ item }">
      <MessageItem :message="item" />
    </template>
  </VirtualScroller>
</template>

<script setup lang="ts">
import { VirtualScroller } from 'vue-virtual-scroller'
</script>
```

#### 任务 6.2：思考气泡动画（2 周）

```vue
<!-- components/chat/ThinkingBubble.vue -->
<template>
  <TransitionGroup name="thinking" tag="div" class="thinking-container">
    <div
      v-for="th in thinkingQueue"
      :key="th.id"
      class="thinking-bubble"
    >
      <span class="thinking-icon">🤔</span>
      <div class="thinking-content">
        <span class="thinking-text">{{ th.content }}</span>
        <span class="thinking-tool" v-if="th.toolName">
          → {{ th.toolName }}
        </span>
      </div>
    </div>
  </TransitionGroup>
</template>

<style scoped>
.thinking-enter-active { animation: thinkingIn 0.3s ease; }
.thinking-leave-active { animation: thinkingOut 0.2s ease; }
@keyframes thinkingIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

#### 任务 6.3：代码块增强（2 周）

```vue
<!-- components/markdown/CodeBlock.vue -->
<template>
  <div class="code-block">
    <div class="code-header">
      <span class="code-lang">{{ language }}</span>
      <button class="copy-btn" @click="copyCode">
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>
    <pre><code v-highlight="code" :class="`language-${language}`"></code></pre>
  </div>
</template>
```

### 7.3 验收标准

- 虚拟滚动支持 1000+ 消息
- 思考气泡动画流畅
- 代码块复制功能正常

---

## 八、技术债务清理

### 8.1 代码质量

| 债务项 | 当前 | 目标 | 方案 | 优先级 |
|--------|------|------|------|--------|
| MCP 协议版本 | 2024-11-05 | 2025-06-18 | 升级协议实现 | P1 |
| 类型注解 | 部分 | 完整 | 添加类型标注 | P2 |
| 单元测试 | < 40% | > 80% | 补充测试 | P2 |
| 异常处理 | 不一致 | 统一 | 使用 ErrorHandler | P2 |
| 日志规范 | 分散 | 统一 | 结构化日志 | P3 |

### 8.2 性能优化

| 问题 | 影响 | 方案 | 优先级 |
|------|------|------|--------|
| 技能扫描启动慢 | 首响延迟 | 懒加载 + 缓存 | P1 |
| 记忆查询无索引 | 大数据慢 | 添加索引 | P1 |
| WebSocket 重连 | 用户体验 | 连接池 + 重试 | P2 |
| 并发限制缺失 | 资源耗尽 | 限流器 | P2 |

---

## 九、风险与应对

### 9.1 技术风险

| 风险 | 影响 | 概率 | 应对 |
|------|------|------|------|
| FTS5 性能瓶颈 | 高 | 中 | 预估数据量，预留扩展 |
| LLM 提取成本 | 中 | 中 | 添加频率限制，缓存 |
| 多工作区内存 | 中 | 低 | LRU 缓存和卸装 |
| 向后兼容性 | 高 | 低 | 保留 skill.json |

### 9.2 项目风险

| 风险 | 影响 | 概率 | 应对 |
|------|------|------|------|
| 范围蔓延 | 中 | 高 | 严格变更管理 |
| 资源不足 | 高 | 中 | 优先级排序 |
| 技术选型 | 中 | 低 | POC 验证 |

---

## 十、参考文档

| 文档 | 说明 |
|------|------|
| 87_Plector_技能与MCP系统深度分析.md | 技能和 MCP 系统分析 |
| 93_Plector与同类开源Agent项目对比.md | 竞品对比研究 |
| 97_Plector技能与架构增强方案.md | 增强方案 |
| 99_LangGraph架构深度研究.md | LangGraph 架构参考 |
| 101_AI_Agent安全最佳实践研究.md | 安全最佳实践 |
| 102_Plector未来升级改造演进方案.md | 综合升级方案 |
| 103_Plector深度技术分析报告.md | 技术深度分析 |

---

## 十一、总结

本实施计划基于对 Plector 当前架构的深度分析和对标竞品的全面研究，提出了分 6 个阶段的升级改造路线图。

**核心原则**：

1. **渐进式演进**：保持向后兼容，逐步替换核心组件
2. **中间件优先**：中间件架构是其他功能的基础，优先完成
3. **安全贯穿**：安全问题在各阶段都有涉及，不是单独阶段
4. **可测试**：每个任务都有明确的验收标准

**实施优先级**：

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 中间件框架 | 基础架构，其他功能的基石 |
| P0 | 安全加固 | 必须满足的合规要求 |
| P1 | 记忆系统增强 | 核心能力提升 |
| P1 | 多智能体支持 | 差异化竞争 |
| P2 | 渠道扩展 | 业务扩展 |
| P2 | 前端增强 | 用户体验 |

---

#实施计划 #Plector #v2.x #分阶段
