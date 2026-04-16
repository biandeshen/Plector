# Plector 记忆系统设计

> 日期：2026-04-16
> 状态：设计文档

---

## 一、记忆系统架构

### 1.1 记忆分层

Plector 采用三层记忆架构：

```
短期记忆（Working Memory）
├── VectorMemory (ChromaDB)
│   ├── conversations collection — 对话历史
│   ├── knowledge collection — 知识库
│   └── preferences collection — 用户偏好
│
├── EventBus (内存)
│   └── 运行时事件流（发布/订阅，CloudEvents 格式）
│
└── SkillContext（技能上下文）
    └── context_refresher — GSD 保鲜机制

长期记忆（Persistent）
├── VectorMemory (ChromaDB)
│   └── 跨 session 持久化
│
└── Disk
    ├── logs/ — 操作日志、会话日志、失败归档
    └── memory/ — 每日工作日志、长期记忆

外部记忆（External）
├── Obsidian Vault — 项目文档、需求文档、会议记录
└── GitHub — 代码、文档版本控制
```

### 1.2 记忆流转

```
用户输入
    ↓
SkillHandler 执行技能
    ↓
EventBus 发布事件（skill.executed / skill.failed 等）
    ↓
VectorMemory 存储对话（conversations collection）
    ↓
context_refresher 触发保鲜（对话轮次 % N）
    ↓
提取 {goal, constraints, completed[], in_progress[]}
    ↓
存入 context_saver collection
    ↓
新消息注入 → 拼接 {保鲜上下文 + 最近 5 轮} 供 LLM 使用
```

---

## 二、核心组件

### 2.1 VectorMemory (core/vector_memory.py)

基于 ChromaDB 的向量存储：

```python
class VectorMemory:
    def __init__(self, persist_directory=None):
        self.client = ChromaClient(persist_directory)
        self.collections = {
            "conversations": ...,   # 对话历史
            "knowledge": ...,        # 知识库
            "preferences": ...,     # 用户偏好
            "context_saver": ...,    # GSD 保鲜上下文
        }

    def add(collection, data, metadata=None):
        """添加记忆"""

    def search(collection, query, top_k=5):
        """向量相似度搜索"""

    def get_context(collection, query, time_range=None, top_k=3):
        """带时间过滤的上下文获取"""

    def invalidate(collection=None, key=None):
        """使记忆失效/重载"""
```

**ID 生成**：MD5(user_id + session_id + 内容哈希)

**限制**：无 TTL，无自动过期

### 2.2 EventBus (core/event_bus.py / event_bus_v2.py)

```python
class EventBus:
    """异步事件总线，CloudEvents 1.0 格式"""

    def subscribe(event_type, handler):
        """订阅事件，支持 * 通配符"""

    def publish(event_type, data):
        """发布事件"""

    def unsubscribe(event_type, handler=None):
        """取消订阅"""
```

**问题**：
- 通配符 `*` 匹配有 bug（`"skill.*"` 会匹配自身）
- `create_task` fire-and-forget，异常静默丢失
- 无重试机制

### 2.3 context_refresher (skills/context_refresher/)

GSD 上下文保鲜技能：

```python
class ContextRefresher:
    async def preserve(conversation_history):
        """触发上下文保鲜"""
        # 1. 提取 goal / constraints / completed / in_progress
        # 2. 发布 context.preserved 事件
        # 3. 存入 context_saver collection

    async def re_anchor(new_goal, new_constraints=None):
        """重锚定（用户明确修改目标时"""
```

**触发时机**：对话轮次 % N（N=10）

### 2.4 Working Memory Files

Plain Markdown 文件存储：

```
~/.workbuddy/memory/
├── YYYY-MM-DD.md          # 每日工作日志（追加）
└── MEMORY.md              # 长期记忆（更新）
```

**写入规则**：
- 每日日志：每次substantive work后追加
- MEMORY.md：用户偏好、项目公约等持久事实

---

## 三、当前问题

| 问题 | 影响 | 状态 |
|------|------|------|
| 向量存储无 TTL/过期 | 记忆无限增长 | 待优化 |
| EventBus 通配符 bug | 事件订阅误匹配 | 已记录 |
| Fire-and-forget 异常丢失 | 事件处理静默失败 | 待修复 |
| context_refresher 触发时机固定 | 固定 %N 不够智能 | 待优化 |
| 无跨 session 记忆恢复 | 长任务重启丢失上下文 | 待优化 |

---

## 四、改进方向

### 4.1 优先级 P1

- EventBus 异常处理：await handler 替代 create_task
- 通配符匹配修复：使用 fnmatch

### 4.2 优先级 P2

- context_refresher 智能触发时机（基于任务复杂度）
- 跨 session 检查点恢复（DeerFlow 风格）

### 4.3 优先级 P3

- 向量存储 TTL/过期机制
- 记忆压缩（摘要替代完整历史）
