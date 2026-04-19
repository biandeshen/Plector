# OpenClaw 深度分析

> 来源：openclaw 官方文档 + GitHub
> 研究日期：2026-04-19

---

## 一、项目定位

**OpenClaw** 是一个开源的本地优先 AI 助手框架，支持多渠道接入、多智能体协作和技能扩展。核心特点是通过工作区隔离实现多智能体部署。

### 核心特性
- **本地优先**：数据存储在本地设备
- **多智能体**：Gateway 托管多个独立 Agent
- **多渠道**：20+ 消息平台
- **技能系统**：基于 SKILL.md 的技能扩展
- **实时 Canvas**：可视化工作区

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                   OpenClaw Gateway                       │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Message Router (消息路由)                           ││
│  │  • Bindings 配置                                    ││
│  │  • 优先级路由                                       ││
│  │  • 会话解析                                         ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Multi-Agent Manager (多智能体管理)                  ││
│  │                                                      ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              ││
│  │  │ Agent 1 │  │ Agent 2 │  │ Agent N │              ││
│  │  │(工作区1) │  │(工作区2) │  │(工作区N) │              ││
│  │  └─────────┘  └─────────┘  └─────────┘              ││
│  │                                                      ││
│  │  • 独立会话                                         ││
│  │  • 独立状态                                         ││
│  │  • 独立技能                                         ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌─────────────────────────────────────────────────────┐│
│  │  Platform Adapters (20+ 平台适配器)                  ││
│  │  • WhatsApp / Telegram / Discord / Slack            ││
│  │  • Signal / iMessage / Matrix / Feishu              ││
│  │  • Teams / LINE / WeChat / QQ                       ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心概念

| 概念 | 说明 |
|------|------|
| **Gateway** | 统一的控制平面，管理会话、渠道、工具、事件 |
| **Agent** | 独立的 AI 助手，有自己的工作区和技能 |
| **Workspace** | Agent 的工作目录，包含配置和记忆 |
| **Binding** | 渠道到 Agent 的绑定规则 |
| **Session** | 单个用户与 Agent 的对话会话 |

---

## 三、多智能体架构

### 3.1 路由优先级

OpenClaw 采用**确定性路由**，遵循"最具体优先"规则：

```
优先级层级（从高到低）：

1. peer (精确匹配)
   └── 匹配：+1234567890 或 DM_abc123

2. parentPeer (线程继承)
   └── 例如：Slack thread 继承 channel

3. guildId + roles
   └── Discord 服务器 + 角色路由

4. guildId
   └── Discord 服务器级别

5. teamId
   └── Slack 团队级别

6. accountId
   └── 账户级别

7. channel (channel ID)
   └── 频道级别

8. (fallback)
   └── 默认 Agent
```

### 3.2 Binding 配置

```yaml
# openclaw.yaml
agents:
  defaults:
    # 默认技能（所有 Agent 共享）
    skills:
      - code_writer
      - web_search

  list:
    - id: general
      name: "通用助手"
      workspace: ~/.openclaw/workspaces/general
      skills:
        - code_writer
        - web_search
        - file_utils

    - id: developer
      name: "开发助手"
      workspace: ~/.openclaw/workspaces/developer
      skills:
        - code_writer
        - git_helper
        - docker_helper

bindings:
  # WhatsApp 单号路由
  - channel: whatsapp
    accountId: "+1234567890"
    agentId: general

  # Telegram 用户路由
  - channel: telegram
    peer: 987654321
    agentId: developer

  # Discord 服务器路由
  - channel: discord
    guildId: "123456789"
    agentId: general

  # Discord 角色路由
  - channel: discord
    guildId: "123456789"
    roles:
      - developer
    agentId: developer
```

### 3.3 工作区隔离

```
~/.openclaw/
├── workspaces/
│   ├── general/              # 通用助手工作区
│   │   ├── AGENTS.md        # Agent 配置
│   │   ├── SOUL.md          # 个性化
│   │   ├── USER.md          # 用户记忆
│   │   └── skills/          # 技能目录
│   │       └── my_skill/
│   │           └── SKILL.md
│   │
│   ├── developer/            # 开发助手工作区
│   │   ├── AGENTS.md
│   │   ├── SOUL.md
│   │   └── USER.md
│   │
│   └── data/                 # 数据目录
│       ├── sessions.db       # SQLite 会话
│       └── artifacts/        # 生成文件
│
├── skills/                   # 共享技能
│   ├── code_writer/
│   │   └── SKILL.md
│   └── web_search/
│       └── SKILL.md
│
└── auth/                     # 认证配置（按 Agent 隔离）
    ├── general/
    │   └── openai.key
    └── developer/
        └── anthropic.key
```

### 3.4 隔离原则

> **"Never reuse `agentDir` across agents (it causes auth/session collisions)."**

每个 Agent 必须有：
- **独立工作区**：配置文件、技能、记忆
- **独立状态目录**：认证信息、模型配置
- **独立会话存储**：会话键格式 `agent::{peer}`

---

## 四、技能系统

### 4.1 技能加载机制

```
┌─────────────────────────────────────────────────────────┐
│                 OpenClaw 技能加载流程                     │
│                                                         │
│  1. 扫描共享技能目录                                     │
│     ~/.openclaw/skills/<skill>/SKILL.md                │
│                                                         │
│  2. 扫描 Agent 工作区技能                               │
│     ~/.openclaw/workspaces/{agent}/skills/SKILL.md     │
│                                                         │
│  3. 按 Agent 允许列表过滤                               │
│     agents.defaults.skills (共享基线)                   │
│     agents.list[].skills (Agent 专属)                  │
│                                                         │
│  4. 技能内容注入提示词                                   │
│     ├── AGENTS.md (Agent 定义)                         │
│     ├── SOUL.md (个性化)                                │
│     ├── USER.md (用户记忆)                              │
│     └── skills/ (技能内容)                               │
└─────────────────────────────────────────────────────────┘
```

### 4.2 SKILL.md 格式

```markdown
# Skill Name

Brief description of what this skill does.

## Triggers

- trigger phrase 1
- trigger phrase 2

## Actions

### Action 1
Step-by-step instructions.

### Action 2
More instructions.

## Examples

User: example trigger
Assistant: expected response

## Notes

Additional context or caveats.
```

### 4.3 技能管理

| 操作 | 命令 | 说明 |
|------|------|------|
| 列出技能 | `/skills` | 显示所有可用技能 |
| 启用技能 | `/skill enable <name>` | 激活技能 |
| 禁用技能 | `/skill disable <name>` | 停用技能 |

---

## 五、配置系统

### 5.1 核心配置文件

```yaml
# openclaw.yaml
openclaw:
  version: "2.0"

agents:
  defaults:
    model: gpt-4o
    thinking: medium
    skills:
      - code_writer
      - file_utils

  list:
    - id: general
      name: "AI Assistant"
      workspace: ~/.openclaw/workspaces/general
      model: gpt-4o
      skills:
        - code_writer
        - web_search

    - id: developer
      name: "Developer Bot"
      workspace: ~/.openclaw/workspaces/developer
      model: claude-sonnet-4
      thinking: high

bindings:
  # 默认路由
  - channel: terminal
    agentId: general

  # 特定渠道
  - channel: telegram
    accountId: "${TELEGRAM_BOT_TOKEN}"
    agentId: general
```

### 5.2 Agent 配置文件

```markdown
# AGENTS.md - Agent 定义

## Identity
- Name: AI Assistant
- Role: Helpful general-purpose assistant
- Personality: Friendly, concise, informative

## Capabilities
- Code writing and review
- File operations
- Web search
- Problem solving

## Constraints
- Always verify critical information
- Ask for clarification when needed
- Provide sources for factual claims
```

```markdown
# SOUL.md - Agent 个性化

## Communication Style
- Be friendly but professional
- Use clear, simple language
- Provide examples when helpful

## Response Format
- Use bullet points for lists
- Include code blocks with syntax highlighting
- Summarize key points at the end
```

```markdown
# USER.md - 用户记忆

## User Information
- Name: [User Name]
- Preferences: [Preferences]
- Known Context: [Context]

## Recent Interactions
- [Summary of recent tasks]
```

---

## 六、命令系统

### 6.1 常用命令

| 命令 | 功能 |
|------|------|
| `/status` | 显示 Agent 状态 |
| `/new` | 开始新对话 |
| `/reset` | 重置当前会话 |
| `/compact` | 压缩上下文 |
| `/think <level>` | 设置思考级别 |
| `/verbose on\|off` | 切换详细输出 |
| `/trace on\|off` | 切换追踪 |
| `/usage off\|tokens\|full` | 用量显示 |
| `/restart` | 重启 Agent |
| `/activation mention\|always` | 激活方式 |

### 6.2 思考级别

```python
THINKING_LEVELS = {
    "off": 0,      # 无思考输出
    "low": 1,      # 简短思考
    "medium": 2,   # 中等思考
    "high": 3,    # 详细思考
}
```

---

## 七、与 Plector 的对比

### 7.1 架构差异

| 特性 | OpenClaw | Plector |
|------|----------|---------|
| **核心语言** | Node.js | Python |
| **智能体模式** | 多 Agent 隔离 | 单 Agent + 技能 |
| **工作流** | 命令式 | DAG YAML |
| **路由** | 绑定配置 | 技能分发 |
| **前端** | CLI + Canvas | Vue3 SPA |

### 7.2 Plector 可借鉴点

1. **多智能体架构**：OpenClaw 的工作区隔离值得参考
2. **配置系统**：AGENTS.md / SOUL.md / USER.md 分离
3. **路由机制**：优先级路由可以增强 agency_orchestrator
4. **命令系统**：斜杠命令提升交互体验

### 7.3 Plector 增强示例

```python
# 参考 OpenClaw 的工作区隔离
class PlectorWorkspace:
    """Plector 工作区隔离"""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.base_path = Path(f"~/.openclaw/workspaces/{workspace_id}")

        # Agent 配置
        self.agents_md = self.base_path / "AGENTS.md"

        # 个性化
        self.soul_md = self.base_path / "SOUL.md"

        # 用户记忆
        self.user_md = self.base_path / "USER.md"

        # 技能目录
        self.skills_dir = self.base_path / "skills"

        # 会话存储
        self.sessions_db = self.base_path / "data" / "sessions.db"

    async def load_config(self) -> AgentConfig:
        """加载 Agent 配置"""
        return AgentConfig(
            system_prompt=self.read_md(self.agents_md),
            personality=self.read_md(self.soul_md),
            memory=self.read_md(self.user_md),
            skills=self.discover_skills(),
        )


# 多智能体路由
class MultiAgentRouter:
    """参考 OpenClaw 的优先级路由"""

    async def route(self, message: Message) -> AgentWorkspace:
        """路由到对应的工作区"""

        # 1. peer 精确匹配
        binding = self.find_binding(peer=message.peer)
        if binding:
            return self.get_workspace(binding.agent_id)

        # 2. guild + roles
        binding = self.find_binding(
            guild=message.guild,
            roles=message.roles
        )
        if binding:
            return self.get_workspace(binding.agent_id)

        # 3. guild 级别
        binding = self.find_binding(guild=message.guild)
        if binding:
            return self.get_workspace(binding.agent_id)

        # 4. 默认
        return self.get_workspace("default")
```

---

## 八、参考资源

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [官方文档](https://docs.openclaw.ai/)
- [Multi-Agent 文档](https://docs.openclaw.ai/concepts/multi-agent)

#OpenClaw #多智能体 #工作区隔离 #技能系统
