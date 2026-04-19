# Hermes Agent 深度分析

> 来源：NousResearch 官方文档 + GitHub
> 研究日期：2026-04-19

---

## 一、项目定位

**Hermes Agent** 是 NousResearch 开发的一个自改进 AI 助手，具备内置学习循环，能够从经验中创建技能并在持续使用中自我改进。

### 核心特性
- **自改进机制**：唯一内置学习循环的 Agent
- **跨会话记忆**：FTS5 全文搜索 + LLM 摘要
- **多平台接入**：18 个消息平台网关
- **多终端后端**：本地、Docker、SSH、Modal、Daytona
- **MCP 原生**：连接任何 MCP 服务器

---

## 二、架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent 架构                      │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │                    CLI / Gateway                    ││
│  │  • cli.py (命令行)                                  ││
│  │  • gateway/ (消息网关)                              ││
│  │  • acp/ (ACP适配器)                                 ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │              AIAgent (run_agent.py ~10700行)         ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────┐ ││
│  │  │ Prompt Builder│  │Provider Res. │  │ Tool Dis│ ││
│  │  └──────────────┘  └──────────────┘  └─────────┘ ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │                    Tools Registry                    ││
│  │  • 47+ 工具 / 19 工具集                             ││
│  │  • 自注册机制 (import时)                             ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │                 Memory System                        ││
│  │  • SQLite + FTS5                                    ││
│  │  • Plugin 可插拔架构                                ││
│  │  • 上下文压缩                                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### AIAgent 核心
- **run_agent.py**：约 10,700 行，包含所有核心逻辑
- **model_tools.py**：工具调用分发
- **hermes_state.py**：SQLite 会话状态

#### Prompt Builder
- 从多个来源组装系统提示
- 包括：personality、SOUL.md、记忆、技能、工具指南

#### Provider Resolution
- 运行时解析 (provider, model) → (api_mode, api_key, base_url)
- 支持 OpenRouter、NVIDIA NIM、OpenAI、Anthropic 等

---

## 三、技能系统

### 3.1 技能目录结构

```
skills/
├── built-in-skill/           # 内置技能
│   └── SKILL.md
├── optional-skill/            # 可选技能
│   └── SKILL.md
└── user-skill/               # 用户技能
    └── SKILL.md
```

### 3.2 SKILL.md 格式

```markdown
# Skill Name

## Description
简短描述技能功能

## Triggers
- 触发词列表

## Actions
### Action 1
执行步骤描述

## Examples
示例对话
```

### 3.3 技能管理命令

```
/skills list          # 列出所有技能
/skills enable xxx    # 启用技能
/skills disable xxx   # 禁用技能
/skills install xxx   # 从 Hub 安装
```

---

## 四、记忆系统

### 4.1 多层记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                    记忆层次结构                           │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  短期记忆 (Short-term)                             ││
│  │  • 当前会话上下文                                   ││
│  │  • SQLite 实时存储                                 ││
│  │  • Token 接近限制时自动压缩                        ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  长期记忆 (Long-term)                               ││
│  │  • 跨会话持久化                                     ││
│  │  • FTS5 全文索引                                   ││
│  │  • LLM 摘要压缩                                    ││
│  └─────────────────────────────────────────────────────┘│
│                          ↓                              │
│  ┌─────────────────────────────────────────────────────┐│
│  │  用户画像 (User Model)                              ││
│  │  • 跨会话偏好学习                                   ││
│  │  • 个性化记忆                                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 4.2 FTS5 搜索实现

```python
# hermes_state.py 中的 FTS5 表
CREATE VIRTUAL TABLE memories USING fts5(
    content,
    topic,
    session_id,
    timestamp,
    contentless_delete=True
);

# 全文搜索查询
SELECT * FROM memories
WHERE memories MATCH ?
ORDER BY rank;
```

### 4.3 上下文压缩

```python
# context_compressor.py
async def compress_context(messages: list, max_tokens: int):
    """使用 LLM 生成摘要压缩对话"""

    summary_prompt = f"""
    压缩以下对话历史，保留关键信息：

    {messages}

    输出格式：
    - 核心话题
    - 已完成的任务
    - 待解决的问题
    - 用户偏好
    """

    summary = await llm.complete(summary_prompt)
    return [SystemMessage(content=summary)]
```

---

## 五、工具系统

### 5.1 工具分类

| 类别 | 后端数 | 示例工具 |
|------|-------|---------|
| Terminal | 6 | bash, ssh, docker, modal, daytona, singularity |
| Browser | 5 | playwright, chrome, firefox, safari, edge |
| Web | 4 | search, fetch, scrape, crawl |
| MCP | 动态 | 任何 MCP 服务器 |
| File | 2 | filesystem, sftp |
| Vision | 1 | image analysis |

### 5.2 自注册机制

```python
# tools/registry.py
class ToolRegistry:
    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, name: str, tool: Tool):
        cls._tools[name] = tool

# tools/bash.py
class BashTool(Tool):
    def __init__(self):
        ToolRegistry.register("bash", self)  # import 时自动注册

    async def execute(self, command: str) -> str:
        return await run_bash(command)
```

---

## 六、多平台消息网关

### 6.1 支持的平台

| 平台 | 适配器 | 状态 |
|------|--------|------|
| Telegram | ✓ | 官方支持 |
| Discord | ✓ | 官方支持 |
| Slack | ✓ | 官方支持 |
| WhatsApp | ✓ | 官方支持 |
| Signal | ✓ | 官方支持 |
| Email | ✓ | 官方支持 |
| Matrix | ✓ | 官方支持 |
| SMS | ✓ | 官方支持 |

### 6.2 统一会话路由

```python
class Gateway:
    def __init__(self):
        self.platforms: dict[str, PlatformAdapter] = {}

    async def handle_message(self, platform: str, message: Message):
        # 1. 授权检查
        if not self.auth.check(message.sender):
            return

        # 2. 会话解析
        session = self.sessions.resolve(message)

        # 3. AIAgent 处理
        response = await self.agent.process(session, message)

        # 4. 回传到平台
        await self.platforms[platform].send(response)
```

---

## 七、终端后端

### 7.1 后端对比

| 后端 | 用途 | 隔离级别 | 资源消耗 |
|------|------|---------|---------|
| Local | 本地开发 | 无 | 低 |
| Docker | 生产隔离 | 高 | 中 |
| SSH | 远程执行 | 高 | 高 |
| Modal | 无服务器 | 高 | 按需 |
| Daytona | 云 IDE | 高 | 高 |
| Singularity | HPC | 高 | 高 |

### 7.2 统一执行接口

```python
class TerminalBackend(ABC):
    @abstractmethod
    async def execute(self, command: str, cwd: str) -> CommandResult:
        """执行命令"""
        pass

    @abstractmethod
    async def upload(self, source: Path, dest: str):
        """上传文件"""
        pass

    @abstractmethod
    async def download(self, source: str, dest: Path):
        """下载文件"""
        pass
```

---

## 八、自改进机制

### 8.1 学习循环

```
┌─────────────────────────────────────────────────────────┐
│                  Hermes 自改进流程                        │
│                                                         │
│  用户交互 ──► AIAgent 执行 ──► 结果评估 ──► 技能更新     │
│                     ↓              ↓                    │
│               成功 ─────────► 强化                       │
│                     ↓              ↓                    │
│               失败 ─────────► 反思                       │
│                     ↓                                   │
│               技能创建/修改                               │
│                     ↓                                   │
│              SKILL.md 自动生成                           │
└─────────────────────────────────────────────────────────┘
```

### 8.2 技能生成

```python
class SkillGenerator:
    async def generate_from_experience(
        self,
        task: str,
        actions: list[Action],
        outcome: str
    ) -> SKILL:
        """从经验生成新技能"""

        prompt = f"""
        基于以下经验生成技能：

        任务：{task}
        执行动作：{actions}
        结果：{outcome}

        生成 SKILL.md 格式的技能定义。
        """

        skill_md = await llm.complete(prompt)
        return SKILL.parse(skill_md)
```

---

## 九、Plector 集成建议

### 9.1 引入 FTS5 搜索

```python
# Plector 记忆系统增强
from core.db import get_db

def init_fts5(db):
    db.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(content, topic, tags, content=memories, content_rowid=id)
    ''')

def search_memories(query: str, limit: int = 10):
    db = get_db()
    return db.execute('''
        SELECT m.*, fts.rank
        FROM memories m
        JOIN memories_fts fts ON m.id = fts.rowid
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    ''', (query, limit)).fetchall()
```

### 9.2 参考技能文件格式

```markdown
# Plector Skill Template

## Metadata
- name: skill_name
- version: 1.0.0
- tier: tier_1_system
- triggers: ["触发词1", "触发词2"]

## Description
技能描述

## Tools
### tool_name
- description: 工具描述
- inputSchema: {...}

## Events
- produces: ["event.name"]
- consumes: ["event.name"]

## Implementation
技能实现说明
```

### 9.3 渠道网关抽象

```python
# Plector 渠道网关设计
class ChannelGateway:
    """
    参考 Hermes Gateway 设计
    支持多渠道统一接入
    """

    async def connect(self, channel: str, config: dict):
        adapter = self.adapters.get(channel)
        if not adapter:
            raise ValueError(f"不支持的渠道: {channel}")
        await adapter.connect(config)

    async def route(self, message: Message) -> Response:
        session = await self.session_manager.get_or_create(
            channel=message.channel,
            user=message.user_id
        )
        return await self.agent.process(session, message)
```

---

## 十、参考资源

- [Hermes Agent 官方文档](https://hermes-agent.nousresearch.com/)
- [GitHub 仓库](https://github.com/NousResearch/hermes-agent)
- [技能开发指南](https://developer.cloud.tencent.com/article/2655764)
- [Awesome Hermes Agent](https://github.com/0xNyk/awesome-hermes-agent)

#HermesAgent #NousResearch #自改进 #多平台
