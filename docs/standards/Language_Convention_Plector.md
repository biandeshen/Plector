# Plector 语言约定规范

> 版本: v1.0.0 | 最后更新: 2026-04-28
>
> 本文档是 CLAUDE.md 第六节的详细扩展版。

---

## 一、总体原则

### 1.1 核心规则

| 场景 | 语言 | 示例 |
|------|------|------|
| 对话（与用户） | 中文 | "我来帮你修复这个 bug" |
| 文档（内部） | 中文 | `## EventBus 事件分发` |
| 文档（对外） | 中文 + 英文 | 项目介绍、API 文档 |
| 代码注释 | 中文 | `# 获取用户列表` |
| 代码本身 | 英文 | `def get_user_list():` |
| 对外 API | 英文 | `POST /api/users` |
| 技术术语 | 英文 | HTTP, API, JSON, XML |

### 1.2 术语对照

| 英文 | 中文 | 使用场景 |
|------|------|----------|
| Commit | 提交 | 代码管理 |
| Branch | 分支 | 版本控制 |
| Merge | 合并 | 分支操作 |
| Issue | 问题 | GitHub |
| Pull Request | PR | 代码审查 |
| Event | 事件 | EventBus |
| Skill | 技能 | Plector |
| Tool | 工具 | 函数调用 |

---

## 二、代码注释规范

### 2.1 注释原则

- **必要**：只注释复杂的逻辑
- **简洁**：不超过两行
- **准确**：描述意图，不描述代码

### 2.2 好/坏示例

```python
# ❌ 坏：描述代码而非意图
# 定义一个函数
def get_user(user_id):
    return db.query(user_id)

# ✅ 好：描述意图
# 根据用户 ID 获取用户信息，用于展示
def get_user(user_id):
    return db.query(user_id)
```

### 2.3 注释位置

```python
# ✅ 函数/类定义前的注释
class EventBus:
    """事件总线，负责事件的分发和监听"""
    pass

# ✅ 复杂逻辑前的注释
def process_event(event):
    # 对于高优先级事件，直接分发到 handler
    # 对于普通事件，加入队列异步处理
    if event.priority == HIGH:
        handler.process(event)
    else:
        queue.put(event)

# ✅ 代码块结束注释（复杂嵌套时）
if condition:
    while True:
        # 复杂的嵌套逻辑
        ...
    # while True 结束
```

### 2.4 TODO 注释

```python
# TODO: 优化性能，当前实现在大并发下有瓶颈
# TODO: (负责人) 修复已知内存泄漏问题
# FIXME: 特定场景下会返回错误结果
# HACK: 临时解决方案，需要后续重构
```

---

## 三、文档语言规范

### 3.1 内部文档

```markdown
## EventBus 事件分发机制

EventBus 是 Plector 的核心组件，负责：
1. 接收事件
2. 分发到对应处理器
3. 管理事件队列

### 使用示例

```python
bus = EventBus()
bus.emit('user.created', {'user_id': 123})
```
```

### 3.2 对外文档（API 文档）

```markdown
## REST API

### GET /api/users

获取用户列表。

**请求参数**：
- `page`: 页码（int）
- `page_size`: 每页数量（int）

**响应**：
```json
{
  "data": [...],
  "total": 100
}
```

**错误码**：
- `400`: 参数错误
- `401`: 未授权
- `500`: 服务器错误
```
```

### 3.3 命名规范

```markdown
# ✅ 正确：中文标题 + 英文术语
## 用户认证
## 技能管理
## MCP Server 配置

# ❌ 错误：全中文或全英文混用
## User Authentication（混用）
## 用户 (Users)（不必要的中英混用）
```

---

## 四、Git 提交消息

### 4.1 中文使用

```bash
# ✅ 正确：中文描述
git commit -m "fix: 修复 EventBus 事件丢失问题"

# ✅ 正确：英文 type + 中文描述
git commit -m "feat(skills): 添加记忆技能"

# ❌ 错误：全英文或混用
git commit -m "fix EventBus event loss bug"  # 全英文
git commit -m "fix: fix EventBus bug"  # 混用
```

### 4.2 详细说明

```bash
# ✅ 正确：详细说明使用中文
git commit -m "fix(EventBus): 修复并发场景下事件丢失问题

本次修复：
1. 修复了多线程同时 emit 时的事件丢失
2. 添加了事件队列锁机制
3. 增加了并发测试用例

影响范围：core/event_bus.py
相关问题：#123
"
```

---

## 五、代码命名规范

### 5.1 文件命名

```python
# ✅ 正确：蛇形命名
event_bus.py
vector_memory.py
skill_handler.py

# ❌ 错误：驼峰或混合
eventBus.py  # 驼峰
VectorMemory.py  # 大驼峰
```

### 5.2 函数/变量命名

```python
# ✅ 正确：蛇形命名
def get_user_list():
    user_list = []

# ❌ 错误：驼峰或中文
def getUserList():  # 驼峰
def 获取用户列表():  # 中文
```

### 5.3 类命名

```python
# ✅ 正确：大驼峰
class EventBus:
class VectorMemory:
class SkillHandler:

# ❌ 错误：蛇形
class event_bus:  # 蛇形
class EventBusHandler:  # 混合
```

### 5.4 常量命名

```python
# ✅ 正确：大写下划线
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_VERSION = "v2.0"

# ❌ 错误：小写或驼峰
maxRetryCount = 3  # 驼峰
default_timeout = 30  # 小写下划线
```

---

## 六、对话语言规范

### 6.1 对用户说话

```markdown
# ✅ 正确：中文 + 专业术语
我来帮你分析这个性能问题。从日志看，EventBus 的事件分发延迟比较高。

# ❌ 错误：中英混杂
这个 bug 是因为 EventBus 的 event dispatch 出了问题
```

### 6.2 解释技术概念

```markdown
# ✅ 正确：用中文解释英文概念
闭包（Closure）是指函数可以访问外部作用域的变量。
Lambda 表达式是一种匿名函数，可以作为参数传递。

# ❌ 错误：直接用英文
Closure 是指...
Lambda 是指...
```

### 6.3 代码块中的语言

```markdown
代码块中应保持英文（编程语言规范）：
- 变量名用英文
- 注释可以用中文
- 字符串内容可以用中文（如果是中文内容的话）
```

---

## 七、特殊情况

### 7.1 国际化场景

如果项目需要支持多语言，保持：
- 代码中的字符串使用英文 key
- 翻译文件使用对应语言

```python
# ✅ 正确
message = i18n.t('user.not_found')  # i18n 国际化
error_message = "用户不存在"  # 中文内容
```

### 7.2 技术文档中的术语

| 术语 | 说明 | 使用场景 |
|------|------|----------|
| API | Application Programming Interface | 技术文档 |
| SDK | Software Development Kit | 技术文档 |
| HTTP | HyperText Transfer Protocol | 技术文档 |
| JSON | JavaScript Object Notation | 技术文档 |
| REST | Representational State Transfer | 技术文档 |
| WebSocket | WebSocket 协议 | 技术文档 |

### 7.3 缩写规则

| 缩写 | 全称 | 使用场景 |
|------|------|----------|
| API | Application Programming Interface | 首次使用全称，后续可用缩写 |
| CLI | Command Line Interface | 技术文档 |
| IDE | Integrated Development Environment | 技术文档 |
| CI/CD | Continuous Integration/Deployment | 技术文档 |

---

## 八、检查清单

### 代码注释
- [ ] 复杂逻辑有中文注释
- [ ] 注释描述意图而非代码
- [ ] TODO/FIXME 有明确说明

### 文档
- [ ] 标题使用中文
- [ ] 技术术语正确使用
- [ ] 保持语言一致性

### Git 提交
- [ ] 提交消息使用中文
- [ ] type 使用英文（如 feat/fix）
- [ ] 详细说明使用中文

### 代码命名
- [ ] 文件名使用蛇形
- [ ] 函数名使用蛇形
- [ ] 类名使用大驼峰
- [ ] 常量使用大写下划线

---

## 九、版本历史

- v1.0.0 (2026-04-28)：初始版本
