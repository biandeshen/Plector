# Plector 技能与 MCP 系统深度分析

> 分析日期：2026-04-19
> 数据来源：代码分析 + 联网调研

---

## 一、现有技能系统盘点

### 1.1 技能列表与分类

| 技能名称 | 版本 | 分层 | 核心功能 | 依赖 |
|---------|------|------|---------|------|
| `health_monitor` | 1.0.0 | tier_1_system | 系统健康检查（CPU/内存/磁盘） | 无 |
| `memory` | 2.0.0 | tier_1_system | 记忆管理（艾宾浩斯遗忘曲线、8种关联模式） | 无 |
| `context_refresher` | 1.0.0 | tier_1_system | GSD 上下文保鲜，防止长对话遗忘 | vector_memory |
| `code_writer` | 1.0.0 | tier_2_functional | 代码读写修改 | 无 |
| `file_utils` | 1.0.0 | tier_2_functional | 文件列表/复制/移动/删除 | 无 |
| `test_runner` | 1.0.0 | tier_2_functional | pytest测试执行/shell命令 | 无 |
| `web_search` | 1.0.0 | tier_2_functional | 博查API网页搜索+页面抓取 | 无 |
| `agency_orchestrator` | 1.1.0 | tier_2_functional | 多智能体YAML工作流引擎（174角色） | 无 |
| `error_knowledge` | 1.0.0 | tier_2_functional | 错误分类与知识库存储 | 无 |
| `auto_developer` | 1.0.0 | tier_3_advanced | 一键自动开发流水线 | agency_orchestrator |
| `self_improver` | 1.0.0 | tier_3_advanced | Plector自我改进系统 | agency_orchestrator |

### 1.2 技能分层架构

```
┌─────────────────────────────────────────────────────────┐
│  tier_3_advanced（高级编排层）                             │
│  ┌─────────────────┐  ┌──────────────────┐             │
│  │  auto_developer │  │  self_improver   │             │
│  │  (依赖agency)   │  │  (依赖agency)    │             │
│  └────────┬────────┘  └────────┬─────────┘             │
│           └──────────┬──────────┘                       │
│                      ▼                                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │  agency_orchestrator (174角色 DAG工作流引擎)        ││
│  │  支持：并行执行/变量传递/条件分支/循环/断点续跑       ││
│  └─────────────────────────────────────────────────────┘│
│                          │                               │
│  ┌──────────┬─────────────┼─────────────┬──────────────┐│
│  ▼          ▼             ▼             ▼              ▼│
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │tier_2  │ │file_utils │ │test_runner│ │web_search  │ │
│  │code_wr │ │(5工具)    │ │(2工具)    │ │(2工具)     │ │
│  │(3工具) │ └──────────┘ └──────────┘ └────────────┘ │
│  └────────┘                                            │
│  ┌──────────┐ ┌────────────┐                          │
│  │error_kno │ │context_ref │                          │
│  │wledge    │ │resher      │                          │
│  └──────────┘ └────────────┘                          │
│                          │                             │
│  ┌───────────────────────┼─────────────────────────────┐│
│  │  tier_1_system（系统基础层）                         ││
│  │  ┌──────────────┐  ┌──────────────┐                ││
│  │  │health_monitor│  │    memory    │                ││
│  │  │(1工具)       │  │(11工具)      │                ││
│  │  └──────────────┘  └──────────────┘                ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 二、MCP 核心架构分析

### 2.1 核心文件结构

```
core/
├── mcp_client.py      # MCP Client 主类（449行）
├── skill_registry.py  # 技能注册表（118行）
├── skill_handler.py   # 技能执行器（89行）
├── skill_loader.py    # 技能热加载器（227行）
├── skill_sandbox.py   # 技能沙箱隔离
└── tool_registry.py  # 工具注册表
```

### 2.2 MCP 通信架构

```python
# MCPClient 架构
class MCPClient:
    servers: dict[str, MCPServer]      # 已连接的服务器
    server_config: dict              # 配置中的服务器定义
    _connection_pool: dict           # 连接池
    _pool_size: int = 3               # 每服务器连接数

# 支持两种传输方式
class MCPServer:
    transport: "stdio" | "http"      # stdio 或 HTTP+SSE
```

### 2.3 MCP 协议支持

| 特性 | Plector 实现 | MCP 官方 |
|------|-------------|----------|
| 协议版本 | 2024-11-05 | 2025-06-18 |
| stdio 传输 | ✓ | ✓ |
| HTTP+SSE | ✓ | ✓ (推荐) |
| Streamable HTTP | 缺失 | ✓ 推荐 |
| 工具发现 | ✓ | ✓ |
| 资源暴露 | 缺失 | ✓ |
| Prompt 模板 | 缺失 | ✓ |
| 采样/回调 | 缺失 | ✓ |
| 结构化输出 | 缺失 | ✓ (Pydantic) |

---

## 三、开源项目对比研究

### 3.1 多智能体编排框架对比

| 框架 | 优势 | 劣势 | 适用场景 | Plector 对标 |
|------|------|------|---------|-------------|
| **CrewAI** | 角色直观、社区大(10万+)、A2A支持 | 框架绑定、生命周期限制 | 业务流程自动化 | agency_orchestrator |
| **LangGraph** | 持久化执行、容错、人机介入 | 学习曲线、紧耦合 | 生产环境工作流 | agent_loop |
| **AutoGen** | 对话丰富、.NET支持、无代码Studio | 微软维护放缓、集中式瓶颈 | 多方对话/辩论 | agency_orchestrator |
| **Temporal** | 持久化工作流、容错强 | 重量级、需要自托管 | 长时运行任务 | agent_loop |

**Plector 定位**：`agency_orchestrator` 类似简化版 CrewAI，`agent_loop` 借鉴 LangGraph 的 agent 执行模式。

### 3.2 AI Agent Memory 系统对比

| 系统 | 架构特点 | 存储方式 | 检索能力 | Plector 对标 |
|------|---------|---------|---------|-------------|
| **Mem0** | 三层记忆OS、生成式反思机制 | Vector+Graph+Episodic | 语义+关系+时序 | memory skill |
| **LangChain Memory** | 多种缓冲类型 | 简单缓冲 | 关键词 | memory skill |
| **AutoGPT Memory** | 长期记忆+短期记忆 | 向量存储 | 相似性 | memory skill |

**最佳实践**（来自 Mem0 架构）：

```
┌─────────────────────────────────────────────────┐
│  AI Agent Memory Architecture (OS类比)           │
│                                                 │
│  Main Context (RAM) ──► 上下文窗口（昂贵有限）    │
│        ↓                                        │
│  External Context (Disk) ──► 数据库（廉价无限）  │
│        ↓                                        │
│  Self-editing ──► 函数调用自动管理              │
│                                                 │
│  三层记忆：                                      │
│  • Sensory = 上下文窗口                          │
│  • Short-term = 会话历史                          │
│  • Long-term = 持久存储                          │
└─────────────────────────────────────────────────┘
```

### 3.3 MCP 官方 SDK 生态

| SDK | 语言 | 特点 | 状态 |
|-----|------|------|------|
| **Python SDK** | Python | FastMCP、丰富示例 | 活跃 |
| **TypeScript SDK** | TS/JS | 完整实现 | 活跃 |
| **Java SDK** | Java | 企业级支持 | 中等 |
| **Go SDK** | Go | 轻量级 | 一般 |

**Plector 当前**：使用原生实现，未集成官方 SDK。推荐逐步迁移到官方 SDK 以获得更好的互操作性。

---

## 四、集成方案建议

### 4.1 MCP 协议升级路径

**Phase 1：兼容增强**
```python
# 当前实现 → 增强互操作性
# 1. 添加 protocolVersion 检查
# 2. 支持新发现的工具元数据格式
# 3. 添加 sampling 回调支持

# mcp_client.py 增强
async def initialize(self, server: MCPServer):
    response = await server.send_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "roots": {"listChanged": True},
            "sampling": {},  # 新增：支持采样回调
            "elicitation": {},  # 新增：支持用户确认
        },
        "clientInfo": {"name": "Plector", "version": "1.0.0"},
    })
```

**Phase 2：官方 SDK 集成**
```python
# 考虑迁移到 FastMCP
from mcp.server.fastmcp import FastMCP

# Plector MCP Server 可以用 FastMCP 重写
mcp = FastMCP("Plector Tools")

@mcp.tool()
async def execute_skill(skill_name: str, params: dict) -> dict:
    """暴露 Plector 技能给外部 MCP Client"""
    return await skill_handler.execute(skill_name, params)
```

### 4.2 记忆系统增强方案

**当前 Plector memory skill 功能**：
- ✓ 对话历史存储
- ✓ 用户偏好管理
- ✓ 知识记忆（语义搜索）
- ✓ 8种关联记忆模式
- ✓ 艾宾浩斯遗忘曲线
- ✗ 生成式反思机制

**增强建议**：
```python
# 新增：生成式反思模块
class GenerativeReflection:
    """
    模拟 Mem0 的生成式反思机制
    定期从记忆流中生成高层次的抽象思考
    """

    def reflect(self, memory_stream: list) -> str:
        """
        输入：记忆流（如"用户吃了午饭"、"用户今天开会"）
        输出：抽象洞察（如"用户有固定的午餐习惯，通常在工作日"）
        """
        prompt = f"""
        基于以下记忆流，生成高层次的抽象洞察：
        {memory_stream}

        反思格式：
        - 识别出的模式
        - 用户偏好推断
        - 建议的后续行动
        """
        return llm.complete(prompt)

    def score_memory(self, memory: dict) -> MemoryScore:
        """
        三维度评分：
        - Recency（新鲜度）：最近访问的权重更高
        - Relevance（相关性）：与当前任务的语义相似度
        - Importance（重要性）：记忆被访问的频率
        """
        return MemoryScore(
            recency=self._calc_recency(memory),
            relevance=self._calc_relevance(memory),
            importance=self._calc_importance(memory)
        )
```

### 4.3 技能热加载增强

**当前实现**：基于文件哈希的热更新
**参考**：LangChain 的 LCEL（LangChain Expression Language）热加载机制

```python
# skill_loader.py 增强
class SkillLoader:
    """参考 LangChain 的热加载设计"""

    # 当前：文件哈希检测
    async def _needs_reload(self, info: SkillInfo) -> bool:
        new_hash = await self._calc_hash(info.path)
        return new_hash != info.file_hash

    # 建议：事件驱动 + 版本检测
    async def _watch_files(self):
        """使用 inotify/advisory lock 替代轮询"""
        # 1. 监听文件变化事件
        # 2. 支持版本锁定
        # 3. 支持技能依赖图重载
        pass

    # 建议：新增技能版本管理
    async def get_skill_version(self, skill_name: str) -> str:
        """获取技能版本，支持 semantic versioning"""
        pass

    async def install_skill_from_registry(self, name: str, version: str = "latest"):
        """从官方技能注册表安装"""
        pass
```

### 4.4 agency_orchestrator 增强建议

**当前**：支持 YAML 工作流 + 174 角色
**参考**：CrewAI 的 Agent 协作模式

```yaml
# 当前 Plector 工作流格式
name: pr-review
steps:
  - name: security_check
    role: security-engineer
  - name: code_review
    role: code-reviewer
    depends: [security_check]

# 建议：增加 CrewAI 风格的协作声明
name: crew-review
agents:
  - name: security_agent
    role: security-engineer
    goal: "Identify security vulnerabilities"
    backstory: "Expert in secure coding"
  - name: reviewer_agent
    role: code-reviewer
    goal: "Review code quality"
    backstory: "Senior developer with 10 years experience"

tasks:
  - name: security_task
    description: "Review PR for security issues"
    agent: security_agent
  - name: review_task
    description: "Review PR for code quality"
    agent: reviewer_agent
    depends_on: [security_task]

process: "hierarchical"  # 新增：sequential/parallel/hierarchical
```

---

## 五、开源项目推荐集成

### 5.1 推荐引入的外部项目

| 项目 | 用途 | 集成方式 | 优先级 |
|------|------|---------|--------|
| **Mem0** | 记忆系统增强 | pip 依赖 | P0 |
| **CrewAI** | 多智能体协作模式参考 | 参考实现 | P1 |
| **MCP Python SDK** | 协议标准化 | 迁移 | P1 |
| **Temporal Python SDK** | 工作流持久化 | 参考架构 | P2 |

### 5.2 MCP Server 生态集成

| MCP Server | 功能 | 配置方式 |
|------------|------|---------|
| **filesystem** | 安全的文件访问 | stdio |
| **github** | GitHub API 集成 | npx |
| **sqlite** | 数据库操作 | 直接运行 |
| **brave-search** | 网页搜索 | env: BRAVE_API_KEY |
| **puppeteer** | 浏览器自动化 | npx |

**Plector 集成示例**：
```yaml
# config/config.yaml
mcp:
  servers:
    filesystem:
      enabled: true
      transport: stdio
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/project/path"]

    github:
      enabled: true
      transport: stdio
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
```

---

## 六、实施路线图

### Phase 1：MCP 协议增强（1-2周）
1. 升级协议版本至最新
2. 添加 sampling/elicitation 支持
3. 集成官方 Python SDK
4. 添加 Streamable HTTP 传输

### Phase 2：记忆系统升级（2-3周）
1. 集成 Mem0 或实现生成式反思
2. 优化向量检索性能
3. 添加记忆可视化调试界面

### Phase 3：技能生态扩展（持续）
1. 发布 Plector 技能注册表
2. 支持从 GitHub 安装技能
3. 技能版本管理和依赖解析

---

## 七、参考资源

### 官方文档
- [[MCP 规范]]
- [[MCP Python SDK]]
- [[MCP Server 列表]]

### 开源项目
- [[CrewAI]]
- [[Mem0]]
- [[LangGraph]]
- [[AutoGen]]

### 相关文档
- [[84_AI助手_核心框架参考]]
- [[85_Claude_Code_自审查方案]]
- [[86_Claude_Code_联网能力方案]]

#AI-Agent #Plector #MCP #技能系统 #多智能体
