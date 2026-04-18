# Plector 部署指南

本文档介绍 Plector 的环境要求、配置方法、部署步骤、监控和故障排查。

## 目录

1. [环境要求](#环境要求)
2. [配置参考](#配置参考)
3. [部署步骤](#部署步骤)
4. [监控和日志](#监控和日志)
5. [故障排查](#故障排查)

---

## 环境要求

### Python 版本

- **最低版本**: Python 3.10+
- **推荐版本**: Python 3.11+

### 系统依赖

| 依赖 | 说明 | 安装方式 |
|------|------|----------|
| Python | 运行时（>= 3.10） | [python.org](https://python.org) |
| pip | 包管理器 | `python -m ensurepip` |
| uv | 高性能包管理器（推荐） | `pip install uv` |
| Node.js | 前端构建（>= 20.x） | [nodejs.org](https://nodejs.org) |
| npm | 前端包管理器（>= 10.x） | 随 Node.js 安装 |

### Python 包依赖

```bash
# 核心依赖
pip install pyyaml httpx

# 可选依赖
pip install ollama     # 本地 LLM
pip install anthropic  # Anthropic API
pip install openai     # OpenAI API
```

### LLM 后端选择

Plector 支持多种 LLM 后端：

| 后端 | 说明 | 适用场景 |
|------|------|----------|
| `ollama` | 本地免费运行 | 开发/测试 |
| `openai` | OpenAI API | 生产环境 |
| `anthropic` | Anthropic Claude | 生产环境 |

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 提供者 | `ollama` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |
| `MINIMAX_API_KEY` | MiniMax API Key | - |
| `GITHUB_TOKEN` | GitHub Token | - |
| `UVX_PATH` | uvx 路径 | `~/.local/bin/uvx` |
| `MCP_STDIO_TIMEOUT` | MCP stdio 超时(秒) | `30` |

---

## 配置参考

配置文件位于 `config/config.yaml`。

### 完整配置示例

```yaml
# LLM 配置
llm:
  provider: "${LLM_PROVIDER:-ollama}"
  max_iterations: 100

  # Ollama（本地免费）
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen3.5:0.8b"

  # OpenAI（付费）
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "${OPENAI_MODEL:-gpt-4o-mini}"
    base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"

  # Anthropic（付费）
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "${ANTHROPIC_MODEL:-claude-sonnet-4-20250514}"

# MCP Server 配置
mcp:
  servers:
    filesystem:
      enabled: true
      transport: "stdio"
      command: "python"
      args: ["servers/filesystem_server.py", "."]
      description: "文件系统操作"

    sqlite:
      enabled: true
      transport: "stdio"
      command: "python"
      args: ["servers/sqlite_server.py", "data/plector.db"]
      description: "SQLite 数据库操作"

    minimax:
      enabled: true
      transport: "stdio"
      command: "${UVX_PATH:-uvx}"
      args: ["minimax-coding-plan-mcp", "-y"]
      env:
        MINIMAX_API_KEY: "${MINIMAX_API_KEY}"
        MINIMAX_API_HOST: "https://api.minimaxi.com"
      description: "MiniMax AI 服务"
```

### MCP Server 配置字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | bool | 是否启用该 Server |
| `transport` | string | 传输方式：`stdio` 或 `http` |
| `command` | string | 可执行命令（stdio 模式） |
| `args` | list | 命令参数 |
| `env` | dict | 环境变量（支持 `${VAR}` 语法） |
| `url` | string | HTTP URL（http 模式） |
| `description` | string | Server 描述 |

### 环境变量引用

配置文件支持 `${VAR}` 和 `${VAR:-default}` 语法：

```yaml
env:
  API_KEY: "${API_KEY}"              # 必填
  OPTIONAL: "${OPTIONAL:-default}"   # 带默认值
```

---

## 部署步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd Plector
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
.\venv\Scripts\activate   # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt

# 或使用 uv（更快）
uv pip install -r requirements.txt
```

### 4. 构建前端 SPA

```bash
cd frontend
npm install
npm run build
cd ..
```

构建产物输出到 `frontend/dist/`，后端 `websocket.py` 自动挂载该目录为静态资源。

> 如果跳过此步骤，`/chat` 路由将无法提供 SPA 界面，但 `/chat-legacy` 旧版界面仍可用。

### 5. 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:0.8b

# 或使用 OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# MCP Server 配置
UVX_PATH=~/.local/bin/uvx
MINIMAX_API_KEY=your_key_here
```

### 6. 验证安装

```bash
# Python 语法检查
python -m py_compile core/agent_loop.py

# 验证配置文件
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# 验证 MCP Server
python servers/filesystem_server.py .

# 后端测试
python -m pytest tests/ -q
```

### 7. 启动应用

```bash
# 启动 WebSocket 渠道（默认端口 8080）
python channels/websocket.py

# 指定端口
python channels/websocket.py --port 9000
```

启动后可访问:

| URL | 说明 |
|-----|------|
| `http://localhost:8080/chat` | Chat SPA（Vue 3 主界面） |
| `http://localhost:8080/chat-legacy` | 旧版 Vanilla JS 界面（回退方案） |
| `http://localhost:8080/dashboard` | 管理面板 |

### 8. 前端开发模式（可选）

如需前端热重载开发：

```bash
# 终端 1: 启动后端
python channels/websocket.py

# 终端 2: 启动 Vite 开发服务器
cd frontend
npm run dev
```

Vite 开发服务器运行在 `localhost:5173`，自动代理 `/api` 和 `/ws` 到后端 `localhost:8080`。

---

## 监控和日志

### 日志配置

Plector 使用 Python 标准日志模块：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 关键日志级别

| 级别 | 用途 |
|------|------|
| `DEBUG` | 详细调试信息 |
| `INFO` | 一般信息（连接、工具注册） |
| `WARNING` | 警告（配置缺失、连接失败） |
| `ERROR` | 错误（异常、认证失败） |

### MCP Server 日志

连接成功时会输出：

```
INFO - MCP Server 'filesystem' 已连接（stdio）
INFO - 注册远程工具: mcp_filesystem_read_file
INFO - 注册远程工具: mcp_filesystem_write_file
```

### 健康检查

```bash
# 启动健康监控技能后
# 触发词："系统健康"、"CPU"、"内存"、"磁盘"
```

### 性能指标

| 指标 | 说明 |
|------|------|
| `max_iterations` | LLM 最大迭代次数 |
| `MCP_STDIO_TIMEOUT` | MCP stdio 超时时间 |

---

## 故障排查

### 常见问题

#### 1. MCP Server 连接失败

**症状**：
```
ERROR - MCP Server 'filesystem' 启动失败：命令 'python' 不存在
```

**解决**：
- 确认 Python 路径正确
- 使用绝对路径：`command: "/usr/bin/python3"`

#### 2. 环境变量未设置

**症状**：
```
ValueError: 环境变量 API_KEY 未设置
```

**解决**：
- 检查 `.env` 文件存在
- 确认环境变量已导出
- 使用 `${VAR:-default}` 提供默认值

#### 3. 工具调用超时

**症状**：
```
ConnectionError: MCP Server 'server' 无响应
```

**解决**：
- 增加超时：`export MCP_STDIO_TIMEOUT=60`
- 检查 Server 是否死锁
- 查看 Server 日志

#### 4. 路径访问被拒绝

**症状**：
```
PermissionError: 禁止操作受保护路径: C:\
```

**解决**：
- 检查 `FORBIDDEN_PATHS` 配置
- 使用允许范围内的路径
- 修改 Server 的根目录配置

#### 5. JSON-RPC 解析错误

**症状**：
```
JSON 解析失败
```

**解决**：
- 检查请求格式是否为有效 JSON
- 确认 JSON-RPC 2.0 格式正确
- 查看 Server stderr 输出

#### 6. LLM 连接失败

**症状**：
- `ollama` 后端：Connection refused to localhost:11434
- `openai` 后端：AuthenticationError
- `anthropic` 后端：AuthenticationError

**解决**：

**Ollama**：
```bash
# 启动 Ollama
ollama serve
# 拉取模型
ollama pull qwen3.5:0.8b
```

**OpenAI/Anthropic**：
```bash
# 设置 API Key
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python channels/websocket.py
```

### 验证命令

```bash
# 验证 Python 语法
python -m py_compile servers/filesystem_server.py

# 验证配置文件
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# 验证 MCP Server 通信
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | python servers/filesystem_server.py
```

### 获取帮助

- 查看 [MCP Server 开发指南](./MCP_Server_Guide.md)
- 查看 [技能开发指南](../standards/Skill_Development_Plector.md)
- 查看 [性能优化文档](../performance.md)

---

## 快速参考

```bash
# 启动
python channels/websocket.py --port 8080

# 环境变量
export LLM_PROVIDER=ollama
export MCP_STDIO_TIMEOUT=30

# 验证
python -m py_compile core/agent_loop.py
python scripts/validate_skills.py
```

---

## 相关文档

- [MCP Server 开发指南](./MCP_Server_Guide.md)
- [配置文件参考](./Configuration_Reference.md)
- [性能优化文档](../performance.md)
- [技能开发指南](../standards/Skill_Development_Plector.md)
