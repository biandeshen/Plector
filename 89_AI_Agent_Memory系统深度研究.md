# AI Agent Memory 系统深度研究

> 来源：联网调研（Mem0 官方博客 + 学术论文）
> 更新：2026-04-19

---

## 一、为什么需要 Memory 系统

LLM 本身是**无状态的**：
- 每次请求都是独立的
- 不记得之前的对话
- 无法学习用户偏好

Memory 系统让 AI Agent 具备**认知能力**：
- 跨会话记忆
- 用户偏好学习
- 上下文关联

---

## 二、Memory 系统架构

### 2.1 OS 类比法

```
┌─────────────────────────────────────────────────────────┐
│  AI Agent Memory Architecture                            │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Main Context (RAM)                                 ││
│  │  • 上下文窗口                                        ││
│  │  • 昂贵、有限（128K token）                          ││
│  │  • 每次请求必需                                      ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  External Context (Disk)                           ││
│  │  • 数据库/向量存储                                   ││
│  │  • 廉价、无限                                       ││
│  │  • 需要时加载到上下文                                ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Self-editing (OS Operations)                      ││
│  │  • 写入：自动保存重要信息                            ││
│  │  • 读取：智能检索相关记忆                            ││
│  │  • 清理：遗忘无关信息                                ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 三层记忆模型

| 层级 | 人类对应 | AI 对应 | 特点 |
|------|---------|---------|------|
| **Sensory Memory** | 感官输入 | 上下文窗口 | 极短期，按请求生命周期 |
| **Short-term Memory** | 工作记忆 | 会话历史 | 单会话内，按轮次 |
| **Long-term Memory** | 情景记忆 | 持久存储 | 跨会话，可检索 |

---

## 三、Memory 类型详解

### 3.1 Vector Memory（语义记忆）

**原理**：将文本转为向量，通过相似度检索

```python
# Mem0 风格实现
class VectorMemory:
    def __init__(self, embedding_model="text-embedding-3-small"):
        self.embedder = OpenAIEmbeddings(model=embedding_model)
        self.vectorstore = Chroma()
    
    def add(self, text: str, metadata: dict):
        """添加记忆"""
        vector = self.embedder.embed_query(text)
        self.vectorstore.add_vectors([vector], [{"text": text, **metadata}])
    
    def search(self, query: str, top_k: int = 5) -> list:
        """语义检索"""
        query_vector = self.embedder.embed_query(query)
        results = self.vectorstore.similarity_search_by_vector(
            query_vector, k=top_k
        )
        return results
```

**应用场景**：
- 回答"之前聊过什么"
- 跨会话信息关联
- 知识问答

### 3.2 Graph Memory（关系记忆）

**原理**：存储实体和关系，形成知识图谱

```python
class GraphMemory:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
    
    def add_fact(self, subject: str, predicate: str, object_: str):
        """添加事实三元组"""
        self.graph.add_edge(subject, object_, relation=predicate)
    
    def query(self, subject: str, relation: str) -> list:
        """关系查询"""
        successors = list(self.graph.successors(subject))
        for s, o, data in self.graph.edges(subject, data=True):
            if data.get('relation') == relation:
                yield o
    
    def infer(self, subject: str, depth: int = 2) -> list:
        """多跳推理"""
        # 支持多层关系推理
        pass
```

**示例**：
```
用户: "我住在上海"
存储: User --[lives_in]--> Shanghai
      User --[city]--> Shanghai

用户: "上海有什么好吃的"
推理: 上海 --[near]--> 江苏/浙江（美食关联）
```

### 3.3 Episodic Memory（情景记忆）

**原理**：按时间顺序存储事件序列

```python
class EpisodicMemory:
    def __init__(self):
        self.episodes = []  # 按时间排序的序列
    
    def record(self, event: dict):
        """记录事件"""
        self.episodes.append({
            **event,
            "timestamp": time.time()
        })
    
    def get_recent(self, n: int = 10) -> list:
        """获取最近 N 个事件"""
        return self.episodes[-n:]
    
    def find_pattern(self, pattern: callable) -> list:
        """模式匹配"""
        return [e for e in self.episodes if pattern(e)]
```

---

## 四、Mem0 架构分析

### 4.1 核心特性

| 特性 | 说明 |
|------|------|
| **多层次** | Sensory + Short-term + Long-term |
| **生成式反思** | 定期生成抽象洞察 |
| **智能评分** | Recency + Relevance + Importance |
| **自动管理** | 冲突更新 + 遗忘衰减 |
| **偏好学习** | 用户个性化记忆 |

### 4.2 评分机制

```python
class MemoryScore:
    def __init__(self, memory: dict):
        self.recency = self._calc_recency(memory)
        self.relevance = self._calc_relevance(memory)
        self.importance = self._calc_importance(memory)
    
    @property
    def total(self) -> float:
        """综合评分"""
        # 可调整权重
        return 0.4 * self.recency + 0.3 * self.relevance + 0.3 * self.importance
    
    def _calc_recency(self, memory: dict) -> float:
        """新鲜度：越近的记忆分数越高"""
        hours_since = (time.time() - memory["last_accessed"]) / 3600
        return 1.0 / (1.0 + hours_since / 24)  # 24小时半衰期
    
    def _calc_relevance(self, memory: dict) -> float:
        """相关性：与当前任务的语义相似度"""
        query_embedding = self.embedder.embed_query(self.current_task)
        memory_embedding = memory["embedding"]
        return cosine_similarity(query_embedding, memory_embedding)
    
    def _calc_importance(self, memory: dict) -> float:
        """重要性：被访问频率"""
        return min(memory["access_count"] / 10, 1.0)
```

### 4.3 反思机制

```python
class Reflection:
    """生成式反思：从记忆流中提取洞察"""
    
    def reflect(self, memory_stream: list[dict]) -> str:
        """
        输入：记忆流
        输出：抽象洞察
        """
        prompt = f"""
        基于以下记忆流，生成高层次的抽象洞察：

        记忆流：
        {self._format_memories(memory_stream)}

        请按以下格式输出：
        1. 识别出的模式（用户行为规律）
        2. 用户偏好推断
        3. 潜在意图分析
        4. 建议的后续行动
        """
        
        response = llm.complete(prompt)
        return self._parse_reflection(response)
    
    def _format_memories(self, memories: list) -> str:
        return "\n".join([
            f"- {m['content']} (时间: {m.get('timestamp')})"
            for m in memories
        ])
```

---

## 五、Plector Memory Skill 现状

### 5.1 已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 对话历史存储 | ✓ | save_conversation / get_conversation_history |
| 用户偏好 | ✓ | save_preference / get_preference |
| 知识记忆 | ✓ | save_knowledge / search_knowledge |
| 语义搜索 | ✓ | semantic_search |
| 8种关联模式 | ✓ | associative_search |
| 艾宾浩斯遗忘 | ✓ | check_memory_decay |
| 记忆强化 | ✓ | reinforce_memory |

### 5.2 缺失功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 生成式反思 | P1 | 定期生成抽象洞察 |
| 关系图谱 | P2 | 实体关系存储 |
| 情景记忆 | P2 | 时间序列事件 |
| 偏好推断 | P1 | 从行为中学习偏好 |

### 5.3 增强建议

```python
# 新增：GraphMemory 集成
class PlectorMemoryEnhancement:
    """Plector 记忆系统增强"""
    
    def __init__(self):
        self.episodic = EpisodicMemory()      # 情景记忆
        self.graph = GraphMemory()              # 关系图谱
        self.vector = VectorMemory()            # 向量存储
    
    def record(self, event_type: str, content: str, **metadata):
        """统一记录接口"""
        record = {
            "type": event_type,
            "content": content,
            **metadata,
            "timestamp": time.time()
        }
        
        # 自动分发到各存储
        self.episodic.record(record)
        self.vector.add(content, metadata)
        
        # 尝试提取实体关系
        entities = self._extract_entities(content)
        for entity in entities:
            self.graph.add_fact(entity["subject"], entity["predicate"], entity["object"])
    
    def retrieve(self, query: str, modes: list = ["vector", "graph", "episodic"]) -> dict:
        """多模态检索"""
        results = {}
        
        if "vector" in modes:
            results["vector"] = self.vector.search(query)
        
        if "graph" in modes:
            results["graph"] = self._graph_reasoning(query)
        
        if "episodic" in modes:
            results["episodic"] = self.episodic.get_recent(10)
        
        return self._fuse_results(results)
```

---

## 六、记忆管理策略

### 6.1 遗忘曲线

```python
class EbbinghausForgetting:
    """艾宾浩斯遗忘曲线实现"""
    
    # 复习间隔（小时）
    INTERVALS = [0.25, 1, 24, 48, 168, 336, 720]  # 15分钟、1小时、1天、2天、7天、14天、30天
    
    def should_review(self, memory: dict) -> bool:
        """判断是否需要复习"""
        intervals = self.INTERVALS
        repetitions = memory.get("repetitions", 0)
        
        if repetitions >= len(intervals):
            return False
        
        next_review = memory.get("last_review", memory.get("created_at", 0)) + intervals[repetitions] * 3600
        
        return time.time() >= next_review
    
    def get_next_review_time(self, memory: dict) -> datetime:
        """获取下次复习时间"""
        repetitions = memory.get("repetitions", 0)
        intervals = self.INTERVALS
        
        if repetitions >= len(intervals):
            # 达到最大间隔，不再提醒
            return None
        
        next_interval = intervals[repetitions] * 3600
        return datetime.fromtimestamp(memory.get("last_review", time.time()) + next_interval)
```

### 6.2 冲突处理

```python
class ConflictResolver:
    """记忆冲突解决"""
    
    def resolve(self, old_memory: dict, new_memory: dict) -> dict:
        """
        解决记忆冲突
        例如：用户说"我住在北京"后又改口"我住在上海"
        """
        # 策略1：时间戳优先
        if new_memory["timestamp"] > old_memory["timestamp"]:
            return new_memory
        
        # 策略2：置信度优先
        if new_memory.get("confidence", 0.5) > old_memory.get("confidence", 0.5):
            return new_memory
        
        # 策略3：保留两者，标记冲突
        return {
            **old_memory,
            "conflicting": True,
            "conflicts_with": new_memory["id"]
        }
```

---

## 七、参考资源

### 官方项目
- [Mem0](https://mem0.ai/) - AI Memory Layer
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [Mem0 论文](https://arxiv.org/pdf/2504.19413)

### 相关框架
- [LangChain Memory](https://python.langchain.com/docs/modules/memory/)
- [LlamaIndex Memory](https://docs.llamaindex.ai/en/latest/examples/memory/MemoryDemo/)
- [AutoGPT Memory](https://github.com/Significant-Gravitas/AutoGPT/tree/master/autogpts/autogpt/autogpt/memory)

### 技术文章
- [AI Agent Memory 2025 综述](https://mem0.ai/blog/what-is-ai-agent-memory)
- [RAG vs Memory 对比](https://mem0.ai/blog/rag-vs-ai-memory)
- [上下文窗口对比 2025](https://aiagentmemory.org/articles/context-window-llm-comparison-2025/)

#Memory #AI-Agent #Mem0 #RAG #向量数据库
