# Plector 深度技术分析报告

> 基于代码级分析的技术深化研究
> 分析日期：2026-04-19
> 代码分析范围：agent_loop.py、skill_handler.py、skill_loader.py、workflow_graph.py、mcp_client.py、vector_memory_v2.py、event_bus_v2.py、前端组件

---

## 一、核心代码架构深度分析

### 1.1 AgentLoop 执行引擎

#### 1.1.1 核心执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentLoop 执行流程                            │
│                                                                 │
│  run_streaming()                                                │
│       │                                                         │
│       ├── _analyze_task_complexity()  [复杂度分析]               │
│       │         └── 关键词检测 → 复杂/简单分类                      │
│       │                                                         │
│       ├── _handle_image_command()      [图片处理]                │
│       │         └── 图片识别 → 专用路径                            │
│       │                                                         │
│       ├── _build_messages()             [消息构建]               │
│       │         ├── _load_memory()      [向量记忆]                 │
│       │         └── system_prompt + memory_context                │
│       │                                                         │
│       └── for max_iterations:                                    │
│              │                                                   │
│              ├── _collect_stream_events()   [流式收集]            │
│              │         ├── buffer 级思考标签过滤                   │
│              │         ├── 工具调用缓冲                           │
│              │         └── 跨 chunk 标签分割处理                    │
│              │                                                   │
│              ├── 无工具调用 → 返回响应                             │
│              │                                                   │
│              └── 有工具调用                                       │
│                    ├── _execute_tool_calls()  [执行工具]          │
│                    │         └── 逐个执行 → toolDone 事件           │
│                    └── 循环继续                                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.1.2 流式思考标签处理（buffer 级增量过滤）

```python
# agent_loop.py:395-427
async def _collect_stream_events(self, messages: list[dict]):
    """收集流式事件，使用 buffer 级增量过滤解决跨 chunk 标签分割问题"""

    full_response = ""
    tool_calls_buffer = []
    raw_buffer = ""          # 累积原始 chunk
    last_yielded_len = 0     # 上次 yield 的长度

    async for event in self.llm.stream_chat(messages, self.tool_registry.get_tool_schemas()):

        if etype == "content":
            raw_buffer += event["content"]
            # 关键：整体过滤 raw_buffer，计算增量
            filtered_full = filter_think_tags(raw_buffer)
            new_content = filtered_full[last_yielded_len:]
            full_response = filtered_full

            if new_content:
                last_yielded_len = len(filtered_full)
                yield {"type": "chunk", "content": new_content}

        elif etype == "tool_call":
            # 工具调用时，提取思考内容
            thinking = self._extract_thinking_from_buffer(raw_buffer)
            self._upsert_tool_call(tool_calls_buffer, event["tool_call"], thinking)
            raw_buffer = ""          # 清空 buffer
            last_yielded_len = 0
```

**技术亮点**：

1. **Buffer 级过滤**：解决 `<think>` 标签被 SSE chunk 分割的问题
2. **增量 yield**：只返回过滤后的增量内容，避免重复
3. **思考提取**：工具调用前保留 LLM 的思考过程

#### 1.1.3 工具调用缓冲与思考保留

```python
# agent_loop.py:380-387
def _upsert_tool_call(self, buffer: list, tool_call: dict, thinking: str = "") -> None:
    """查找并更新或插入工具调用记录"""
    for i, existing_tc in enumerate(buffer):
        if existing_tc.get("id") == tool_call.get("id"):
            # 补充思考内容
            if thinking and not buffer[i].get("thinking"):
                buffer[i]["thinking"] = thinking
            return
    buffer.append({**tool_call, "thinking": thinking})
```

**设计优势**：

- 思考内容与工具调用关联
- 支持流式展示思考过程
- 前端可独立渲染思考文本

### 1.2 技能系统架构

#### 1.2.1 技能加载器（热更新）

```python
# skill_loader.py - 核心热更新机制
class SkillLoader:
    def __init__(self, base_path: str = "skills"):
        self._cache: dict[str, SkillInfo] = {}      # 技能缓存
        self._lock = asyncio.Lock()                  # 并发控制
        self._file_watcher_task: asyncio.Task | None = None
        self._watch_interval = 5.0                   # 轮询间隔

    async def _needs_reload(self, info: SkillInfo) -> bool:
        """检查技能是否需要重新加载"""
        if not info.is_loaded:
            return True
        new_hash = await self._calc_hash(info.path)
        return new_hash != info.file_hash

    async def _calc_hash(self, path: Path) -> str:
        """计算目录内容哈希（.py + skill.json）"""
        hasher = hashlib.sha256()
        for py_file in sorted(path.rglob("*.py")):
            with open(py_file, "rb") as f:
                hasher.update(f.read())
        # 包含 skill.json
        ...
        return hasher.hexdigest()[:16]
```

**改进空间**：

| 当前实现 | 改进方向 |
|---------|---------|
| 轮询检测（5秒） | 事件驱动（inotify/FSEvents） |
| 整体哈希 | 按文件增量更新 |
| 单锁并发 | 分段锁优化 |

#### 1.2.2 技能处理器（MCP 路由）

```python
# skill_handler.py:43-88
class SkillHandler:
    async def execute(self, skill_name: str, method: str, params: dict) -> dict:
        # 1. 获取技能
        skill = self.registry.get_skill(skill_name)

        # 2. 懒加载模块
        if skill["module"] is None:
            module_path = skill["path"] / "implementation.py"
            loop = asyncio.get_running_loop()
            skill["module"] = await loop.run_in_executor(
                None, _load_module_sync, skill_name, module_path
            )

        # 3. 调用处理方法
        instance = handler_class()
        func = getattr(instance, method, None)
        result = func(**params)
        if asyncio.iscoroutine(result):
            result = await result

        # 4. MCP 代理路由
        if isinstance(result, dict) and "_mcp_call" in result:
            return await self._handle_mcp_call(result)

        return {"result": result}
```

**MCP 路由机制**：

- 技能返回 `_mcp_call` 字典触发代理
- 复用 AgentLoop 已初始化的 MCPClient
- 避免重复建连

### 1.3 向量记忆系统（V2）

#### 1.3.1 艾宾浩斯遗忘曲线实现

```python
# vector_memory_v2.py - 记忆强度管理
DECAY_COEFFICIENTS = {
    5: 0.9,   # 5小时间隔 - 高衰减率
    10: 0.8,  # 10小时间隔
    30: 0.5,  # 30小时间隔
    50: 0.3,  # 50小时间隔 - 低衰减率
}

def _calculate_decay(self, last_accessed: float, repetition_interval: int) -> float:
    """指数衰减模型"""
    elapsed_hours = (time.time() - last_accessed) / 3600
    decay_coef = DECAY_COEFFICIENTS.get(repetition_interval, 0.5)
    # intensity = e^(-elapsed_hours / (decay_coef * 10))
    intensity = pow(2.71828, -elapsed_hours / (decay_coef * 10))
    return max(0.0, min(1.0, intensity))
```

**四层记忆强度**：

```
┌──────────────────────────────────────────┐
│  MemoryIntensity.ALIVE (≥0.8)           │
│  → 活跃记忆，最近访问，权重最高            │
├──────────────────────────────────────────┤
│  MemoryIntensity.NORMAL (0.5-0.8)        │
│  → 正常记忆，定期复习                     │
├──────────────────────────────────────────┤
│  MemoryIntensity.FADING (0.2-0.5)       │
│  → 衰退记忆，需要复习提醒                 │
├──────────────────────────────────────────┤
│  MemoryIntensity.FORGOTTEN (<0.2)      │
│  → 可被清除的遗忘记忆                    │
└──────────────────────────────────────────┘
```

#### 1.3.2 查询缓存优化

```python
# vector_memory_v2.py:140-175
async def search_batch(self, queries: list[str], top_k: int = 5, filters=None):
    """批量查询 + 缓存"""
    results = []
    for query in queries:
        # 1. 检查缓存
        cache_key = self._make_cache_key(query, top_k, filters)
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            results.append(cached)
            continue

        # 2. 执行查询
        result = await self.search(query, top_k, filters)

        # 3. 存入缓存
        await self._put_to_cache(cache_key, entries)
        results.append(entries)

    return results
```

**缓存策略**：

- TTL：5 分钟
- LRU 淘汰：最大 1000 条
- 缓存命中率统计

### 1.4 事件总线（V2）

#### 1.4.1 CloudEvents 格式

```python
# event_bus_v2.py
@dataclass
class Event:
    """CloudEvents 格式"""
    specversion: str = "1.0"
    id: str = ""
    source: str = "plector"
    type: str = ""
    time: str = ""
    data: dict = field(default_factory=dict)
```

#### 1.4.2 弱引用防泄漏

```python
# event_bus_v2.py:49-74
class WeakHandler:
    """防止 handler 内存泄漏"""
    __slots__ = ("_callback", "_is_async", "_ref")

    def __init__(self, handler: Callable):
        self._ref = weakref.ref(handler)  # 弱引用
        self._is_async = asyncio.iscoroutinefunction(handler)

    def __call__(self, *args, **kwargs):
        handler = self._ref()  # 获取引用
        if handler is not None:
            return handler(*args, **kwargs)
```

**关键优化**：

- `use_weak_ref=True` 默认启用
- 订阅者上限 100 个/类型
- 事件历史 1000 条

### 1.5 MCP Client 架构

#### 1.5.1 双传输支持

```python
# mcp_client.py:56-63
class MCPServer:
    async def connect(self):
        """支持 stdio 和 HTTP+SSE"""
        if self.transport == "stdio":
            await self._connect_stdio()
        elif self.transport == "http":
            await self._connect_http()
```

#### 1.5.2 连接池

```python
# mcp_client.py:312-338
class MCPClient:
    def __init__(self, config: dict):
        self._connection_pool: dict[str, list[MCPServer]] = {}
        self._pool_size = 3  # 每服务器连接数

    def _acquire_connection(self, server_name: str) -> MCPServer:
        """连接池获取"""
        if self._connection_pool[server_name]:
            return self._connection_pool[server_name].pop()
        # 懒创建
        server = MCPServer(server_name, self.server_config[server_name])
        return server
```

---

## 二、前端架构分析

### 2.1 Vue 3 SPA 结构

```
App.vue
├── AppHeader.vue           # 头部
├── ConversationSidebar.vue # 侧边栏
│   ├── SearchInput.vue    # 搜索
│   └── ConversationItem.vue
└── ChatMain.vue           # 主聊天区
    ├── WelcomeScreen.vue  # 欢迎页
    ├── MessageList.vue    # 消息列表
    │   ├── UserMessage.vue
    │   └── AssistantMessage.vue
    │       ├── ToolSummaryPanel.vue
    │       │   └── ToolCallCard.vue
    │       ├── MarkdownContent.vue
    │       └── StreamingCursor.vue
    └── MessageInput.vue   # 输入框
```

### 2.2 组件关键特性

#### 2.2.1 ToolCallCard 组件

```vue
<!-- ToolCallCard.vue -->
<template>
  <div class="tool-item">
    <div class="tool-item-header" @click="toggleExpand">
      <span class="step-number">{{ index + 1 }}</span>
      <span class="tool-item-name">{{ tool.name }}</span>
      <span class="tool-item-status" :class="tool.status">
        <span v-if="tool.status === 'running'" class="spinner"></span>
        {{ statusLabel }}
      </span>
    </div>
    <!-- 展开内容 -->
    <div class="tool-detail-content" :class="{ expanded: isExpanded }">
      <div v-if="cleanedThinking" class="tool-section thinking-section">
        <div class="section-label">思考</div>
        <div class="thinking-text">{{ cleanedThinking }}</div>
      </div>
      <div v-if="tool.arguments" class="tool-section args-section">
        <pre>{{ formattedArgs }}</pre>
      </div>
      <div v-if="tool.result" class="tool-section result-section">
        <pre>{{ truncatedResult }}</pre>
      </div>
    </div>
  </div>
</template>
```

**功能亮点**：

- 思考内容独立展示（斜体）
- 参数/结果 JSON 格式化
- 折叠/展开动画
- 执行状态指示器

#### 2.2.2 AssistantMessage 组件

```vue
<!-- AssistantMessage.vue -->
<script setup lang="ts">
const displayContent = computed(() => {
  let content = props.isStreaming
    ? props.streamBuffer
    : props.message?.content || ''

  // 过滤工具结果在文本中的重复
  if (toolCalls.value.length > 0) {
    const results = toolCalls.value.map((t) => t.result).filter(Boolean)
    content = filterToolContent(content, results)
  }
  return content
})
</script>
```

**处理流程**：

1. 流式内容 vs 静态内容
2. 工具结果去重
3. Markdown 渲染

---

## 三、深化技术改进方案

### 3.1 中间件架构增强

#### 3.1.1 当前状态

AgentLoop 当前是单链执行：

```python
# 当前流程
messages → LLM.stream() → tool_calls → execute → repeat
```

#### 3.1.2 中间件化改造

```python
# 目标：可插拔中间件链
class AgentMiddleware(ABC):
    async def process(
        self,
        ctx: AgentContext,
        next_handler: Callable
    ) -> dict:
        """前处理 → next_handler() → 后处理"""
        pass

class MiddlewareChain:
    def __init__(self):
        self._middlewares: list[AgentMiddleware] = []

    async def execute(self, ctx: AgentContext) -> dict:
        async def chain(idx: int) -> dict:
            if idx >= len(self._middlewares):
                return await self._execute_agent(ctx)
            mw = self._middlewares[idx]
            return await mw.process(ctx, lambda: chain(idx + 1))
        return await chain(0)

# 内置中间件
class MemoryMiddleware(AgentMiddleware):
    """记忆加载/提取"""
    async def process(self, ctx, next_handler) -> dict:
        ctx.memory = await self.load_memory(ctx.session_id)
        result = await next_handler()
        await self.extract_memory(ctx, result)
        return result

class SecurityMiddleware(AgentMiddleware):
    """输入/输出安全"""
    async def process(self, ctx, next_handler) -> dict:
        ctx.user_input = self.sanitize(ctx.user_input)
        result = await next_handler()
        result = self.validate_output(result)
        return result

class AuditMiddleware(AgentMiddleware):
    """审计日志"""
    async def process(self, ctx, next_handler) -> dict:
        await self.log_request(ctx)
        result = await next_handler()
        await self.log_response(ctx, result)
        return result
```

### 3.2 流式处理增强

#### 3.2.1 当前 buffer 级过滤 → 事件驱动

```python
# 当前：buffer 级过滤
async def _collect_stream_events(self, messages):
    raw_buffer = ""
    async for event in self.llm.stream():
        raw_buffer += event["content"]
        filtered = filter_think_tags(raw_buffer)
        yield {"type": "chunk", "content": filtered[len(last):]}
        last = len(filtered)

# 增强：事件驱动的流式处理
class StreamingPipeline:
    """流式处理管道"""

    def __init__(self):
        self._filters: list[ContentFilter] = []

    async def process(self, raw_chunks: AsyncIterator):
        """管道化处理"""
        chunks = raw_chunks

        # 1. 标签过滤
        chunks = self._pipe(chunks, self._filter_tags)

        # 2. Markdown 预处理
        chunks = self._pipe(chunks, self._preprocess_md)

        # 3. 代码高亮
        chunks = self._pipe(chunks, self._highlight_code)

        # 4. Yield 增量
        async for chunk in self._yield_deltas(chunks):
            yield chunk

    async def _filter_tags(self, chunk: str) -> str:
        """过滤思考标签"""
        return filter_think_tags(chunk)
```

#### 3.2.2 思考内容的结构化传递

```python
# 当前：思考作为工具调用的一部分
{
    "type": "toolExecuting",
    "tool": "search_memory",
    "thinking": "我需要先搜索相关信息..."
}

# 增强：独立的思考事件
{
    "type": "thinking",
    "content": "我需要先搜索相关信息...",
    "toolId": "call_abc123"
}

{
    "type": "toolExecuting",
    "tool": "search_memory",
    "toolId": "call_abc123"
}
```

### 3.3 记忆系统深化

#### 3.3.1 LLM 驱动的记忆提取

```python
# 当前：向量相似度搜索
results = await vm.search(
    query="最近的对话内容",
    collection="conversations",
    n_results=5,
    session_id=session_id,
)

# 增强：LLM 主动提取
class LLMExtractor:
    async def extract(self, conversation: list[Message]) -> MemoryData:
        """从对话中 LLM 提取关键信息"""
        prompt = f"""
        分析以下对话，提取：

        1. 用户上下文（工作领域、目标、约束）
        2. 具体事实（置信度 > 0.7）
        3. 用户偏好
        4. 实体关系

        对话：
        {conversation}
        """
        return await self.llm.complete_json(prompt)
```

#### 3.3.2 混合检索（FTS5 + Vector）

```python
# 增强：全文 + 向量混合检索
class HybridMemorySearch:
    async def search(self, query: str, user_id: str) -> list[dict]:
        # 1. FTS5 全文搜索
        fts_results = await self.fts.search(query, user_id, limit=10)

        # 2. 向量语义搜索
        vec_results = await self.vector.search(query, user_id, limit=10)

        # 3. BM25 + 余弦相似度融合
        fused = self._hybrid_fusion(fts_results, vec_results)

        return fused
```

### 3.4 技能系统增强

#### 3.4.1 技能版本与依赖

```python
# 增强：语义版本 + 依赖解析
class SkillInfo:
    name: str
    version: str              # semver: "1.2.3"
    dependencies: list[str]   # ["memory@^2.0", "code_writer@^1.0"]

    def satisfies(self, requirement: str) -> bool:
        """检查版本是否满足要求"""
        op, required = self._parse_requirement(requirement)
        return self._compare_versions(self.version, op, required)

class SkillResolver:
    """技能依赖解析"""
    def resolve(self, requirements: list[str]) -> list[Skill]:
        """拓扑排序 + 版本冲突检测"""
        pass
```

#### 3.4.2 技能沙箱隔离

```python
# 增强：技能执行沙箱
class SkillSandbox:
    """技能隔离执行"""

    def __init__(self):
        self._pool = ProcessPool(max_workers=4)

    async def execute(self, skill: Skill, method: str, params: dict) -> dict:
        """在独立进程中执行"""
        # 1. 资源限制
        resource_limit = {
            "memory_mb": 512,
            "cpu_percent": 50,
            "timeout_seconds": 30,
        }

        # 2. 文件系统隔离
        sandbox_path = self._create_temp_dir()
        os.chdir(sandbox_path)

        # 3. 执行
        result = await self._pool.run(
            skill.implementation,
            method,
            params,
            resource_limit
        )

        return result
```

### 3.5 前端组件增强

#### 3.5.1 思考内容的可视化

```vue
<!-- 增强：独立的思考气泡 -->
<template>
  <div class="message assistant">
    <!-- 思考气泡（先展示） -->
    <TransitionGroup name="thinking-fade">
      <div
        v-for="th in thinkingQueue"
        :key="th.id"
        class="thinking-bubble"
      >
        <span class="thinking-icon">🤔</span>
        <span class="thinking-text">{{ th.content }}</span>
      </div>
    </TransitionGroup>

    <!-- 工具调用 -->
    <ToolSummaryPanel v-if="toolCalls.length > 0" :tools="toolCalls" />

    <!-- 最终回复 -->
    <div class="bubble">
      <MarkdownContent :content="displayContent" />
    </div>
  </div>
</template>

<style>
.thinking-bubble {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 10px;
  background: linear-gradient(135deg, #f5f5f5, #e8e8e8);
  border-radius: 12px;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  animation: thinkingPulse 1s ease-in-out infinite;
}

.thinking-icon { font-size: 14px; }
.thinking-text { font-style: italic; }

@keyframes thinkingPulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}
</style>
```

#### 3.5.2 工具执行时间线

```vue
<!-- 增强：工具执行时间线视图 -->
<template>
  <div class="timeline">
    <div
      v-for="(step, idx) in executionSteps"
      :key="step.id"
      class="timeline-step"
      :class="step.status"
    >
      <div class="step-connector">
        <div class="step-dot"></div>
        <div v-if="idx < executionSteps.length - 1" class="step-line"></div>
      </div>
      <div class="step-content">
        <div class="step-header">
          <span class="step-index">{{ idx + 1 }}</span>
          <span class="step-name">{{ step.tool }}</span>
          <span class="step-time">{{ step.elapsed }}ms</span>
        </div>
        <div class="step-thought" v-if="step.thinking">
          {{ step.thinking }}
        </div>
      </div>
    </div>
  </div>
</template>
```

---

## 四、性能优化方案

### 4.1 后端优化

| 优化项 | 当前 | 目标 | 方案 |
|--------|------|------|------|
| 技能加载 | 文件哈希 | inotify/FSEvents | 事件驱动 |
| 记忆查询 | 纯向量 | 混合检索 | FTS5 + Vector |
| 工具调用 | 串行 | 并行执行 | asyncio.gather |
| WebSocket | 单连接 | 连接池 | HTTP/2 multiplexing |

### 4.2 前端优化

| 优化项 | 当前 | 目标 | 方案 |
|--------|------|------|------|
| Markdown | CDN渲染 | 本地渲染 | markdown-it |
| 代码高亮 | CDN | Web Worker | highlight.js worker |
| 虚拟滚动 | 无 | 虚拟列表 | vue-virtual-scroller |
| 思考动画 | 简单 | 骨架屏 | loading skeleton |

---

## 五、安全加固

### 5.1 输入清理

```python
class InputSanitizer:
    DANGEROUS_PATTERNS = [
        (r"os\.system\s*\(", "code_execution"),
        (r"subprocess\.", "code_execution"),
        (r"exec\s*\(", "code_execution"),
        # ... 注入检测
    ]

    def sanitize(self, content: str) -> SanitizedInput:
        violations = []
        for pattern, name in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content):
                violations.append(name)
        return SanitizedInput(
            cleaned=content,
            violations=violations,
            is_clean=len(violations) == 0
        )
```

### 5.2 RBAC 权限

```python
class RBAC:
    ROLE_PERMISSIONS = {
        "user": ["memory:read", "skill:list"],
        "developer": ["memory:*", "skill:*", "file:write"],
        "admin": ["*"],  # 全权限
    }

    async def check_tool(self, user_id: str, tool_name: str) -> bool:
        roles = self.user_roles.get(user_id, [])
        for role in roles:
            perms = self.ROLE_PERMISSIONS.get(role, [])
            if "*" in perms or f"tool:{tool_name}" in perms:
                return True
        return False
```

---

## 六、总结

### 6.1 架构优势

1. **ReAct 执行模式**：成熟的推理-行动循环
2. **buffer 级流式过滤**：解决跨 chunk 标签分割
3. **技能热更新**：文件哈希检测 + 懒加载
4. **向量记忆**：艾宾浩斯遗忘曲线
5. **事件总线**：CloudEvents 格式 + 弱引用防泄漏

### 6.2 改进方向

| 方向 | 优先级 | 改进点 |
|------|--------|--------|
| 中间件架构 | P0 | 可插拔中间件链 |
| LLM 记忆提取 | P1 | 主动抽取关键信息 |
| FTS5 混合检索 | P1 | 全文 + 向量融合 |
| 并行工具执行 | P1 | asyncio.gather |
| 技能沙箱隔离 | P2 | 进程级资源限制 |
| 思考可视化增强 | P2 | 独立气泡 + 时间线 |

### 6.3 实施建议

1. **Phase 1**：中间件框架（1周）
2. **Phase 2**：LLM 记忆提取（2周）
3. **Phase 3**：FTS5 混合检索（2周）
4. **Phase 4**：并行执行 + 沙箱（2周）
5. **Phase 5**：前端增强（持续）

---

#技术分析 #深度研究 #Plector #架构优化
