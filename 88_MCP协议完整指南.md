# MCP 协议完整指南

> 来源：联网调研 + 官方文档
> 更新：2026-04-19

---

## 一、MCP 概述

**Model Context Protocol (MCP)** 是 Anthropic 推出的开源协议，用于标准化 AI 应用与外部工具/数据的连接。

### 核心价值
- **标准化**：统一的工具发现、调用、结果返回格式
- **互操作**：任何 MCP Client 可调用任何 MCP Server
- **可扩展**：Server 可动态暴露新工具

---

## 二、协议架构

### 2.1 核心概念

| 概念 | 说明 | 类比 |
|------|------|------|
| **Server** | 暴露工具和资源的 MCP 服务 | API |
| **Client** | 连接 Server 并调用工具 | API Consumer |
| **Resources** | 暴露给 AI 的数据（只读） | GET endpoints |
| **Tools** | AI 可调用的操作 | POST endpoints |
| **Prompts** | 可复用的提示模板 | 模板库 |
| **Sampling** | Server 请求 LLM 采样 | 回调 |
| **Elicitation** | 请求用户确认 | 交互确认 |

### 2.2 传输方式

```python
# 1. STDIO（本地进程）
# 最常用，适合本地 MCP Server
{
    "command": "python",
    "args": ["-m", "mcp_server"],
    "env": {"API_KEY": "xxx"}
}

# 2. HTTP + SSE（服务器推送）
# 适合远程 Server
{
    "url": "https://api.example.com/mcp/sse",
    "headers": {"Authorization": "Bearer xxx"}
}

# 3. Streamable HTTP（推荐）
# 最新方式，支持双向流
{
    "url": "https://api.example.com/mcp/stream"
}
```

---

## 三、Python SDK 快速入门

### 3.1 安装

```bash
pip install mcp
# 或使用 uv
uv add mcp
```

### 3.2 创建 MCP Server

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

# 定义工具
@mcp.tool()
def add(a: int, b: int) -> int:
    """两个数相加"""
    return a + b

@mcp.tool()
def get_weather(city: str) -> dict:
    """获取城市天气"""
    return {"city": city, "temp": 22, "condition": "sunny"}

# 定义资源
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """问候语资源"""
    return f"Hello, {name}!"

# 启动服务
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

### 3.3 结构化输出

```python
from pydantic import BaseModel

class WeatherData(BaseModel):
    temperature: float
    humidity: int
    condition: str
    wind_speed: float

@mcp.tool()
def get_weather(city: str) -> WeatherData:
    """返回结构化天气数据"""
    return WeatherData(
        temperature=22.5,
        humidity=65,
        condition="partly cloudy",
        wind_speed=12.5
    )

# Pydantic 模型会被自动序列化为 JSON
```

### 3.4 进度报告

```python
@mcp.tool()
async def long_running_task(task_id: str, ctx: Context) -> str:
    """长时任务，支持进度报告"""
    await ctx.info(f"Starting task: {task_id}")
    
    steps = ["准备", "执行", "验证", "完成"]
    for i, step in enumerate(steps):
        # 报告进度
        await ctx.report_progress(
            progress=i + 1,
            total=len(steps),
            message=f"当前: {step}"
        )
        await asyncio.sleep(1)
    
    return f"Task {task_id} completed"
```

### 3.5 用户交互

```python
@mcp.tool()
async def confirm_action(action: str, ctx: Context) -> str:
    """请求用户确认"""
    response = await ctx.elicit(
        message=f"确认执行: {action}?",
        accept_labels=["确认", "取消"],
    )
    
    if response["action"] == "确认":
        return f"已执行: {action}"
    else:
        return "已取消"
```

---

## 四、Claude Code MCP 集成

### 4.1 配置方式

**用户级配置**：`~/.claude.json`
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

**项目级配置（推荐）**：`.claude/mcp.json`
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./src"]
    }
  }
}
```

### 4.2 常用 MCP Server

| Server | 命令 | 环境变量 |
|--------|------|---------|
| GitHub | `npx -y @modelcontextprotocol/server-github` | GITHUB_PERSONAL_ACCESS_TOKEN |
| Filesystem | `npx -y @modelcontextprotocol/server-filesystem [path]` | - |
| Brave Search | `npx -y @modelcontextprotocol/server-brave-search` | BRAVE_API_KEY |
| SQLite | 直接运行二进制 | DATABASE_PATH |
| Puppeteer | `npx -y @modelcontextprotocol/server-puppeteer` | - |

---

## 五、最佳实践

### 5.1 工具设计原则

1. **原子性**：每个工具做一件事
2. **幂等性**：多次调用结果一致
3. **可观测**：添加日志和进度报告
4. **错误处理**：使用 `isError: true` 标记失败

### 5.2 性能优化

```python
# 使用连接池
mcp = FastMCP("Server", 
    dependencies=["httpx"],  # 复用依赖
)

# 添加缓存
@mcp.tool()
@cache(ttl=300)  # 5分钟缓存
def get_exchange_rate(from_: str, to: str) -> float:
    ...
```

### 5.3 生产部署

```python
# 使用 Streamable HTTP
mcp.run(
    transport="streamable-http",
    port=3000,
    # 推荐配置
    stateless_http=True,  # 无状态，适合 Serverless
    json_response=True,   # JSON 响应格式
)

# 或使用 uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=3000)
```

---

## 六、官方资源

- [MCP 规范](https://modelcontextprotocol.io/specification/2025-06-18)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Server 示例](https://github.com/modelcontextprotocol/servers)
- [官方注册表](https://registry.modelcontextprotocol.io)

---

## 七、Plector 集成建议

### 当前状态
- Plector 使用原生实现，未集成官方 SDK
- 协议版本：2024-11-05（旧版）
- 缺少：Sampling、Prompts、Resources

### 升级路径
1. 集成 MCP Python SDK
2. 暴露 Plector 技能为 MCP Server
3. 支持官方推荐的新特性

```python
# Plector 技能暴露为 MCP Server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Plector Skills")

@mcp.tool()
async def execute_skill(skill_name: str, params: dict) -> dict:
    """执行 Plector 技能"""
    return await skill_handler.execute(skill_name, params)

@mcp.resource("skill://{name}/schema")
def get_skill_schema(name: str) -> dict:
    """暴露技能 schema"""
    return registry.get_skill(name)["meta"]
```

#MCP #Claude-Code #AI-Agent #协议标准
