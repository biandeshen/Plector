# 配置文件参考

本文档索引 Plector 相关的所有配置文件。

## 核心配置

| 文件 | 说明 |
|------|------|
| `config/config.yaml` | 主配置文件（LLM、MCP、渠道设置） |
| `config/closed_loops.yaml` | 闭环配置 |
| `config/roles.yaml` | 角色配置 |
| `config/alerts.yaml` | 告警规则配置 |
| `config/logging_config.yaml` | 日志配置 |

## 配置示例

### config.yaml

```yaml
llm:
  provider: ollama  # ollama / openai / anthropic / minimax
  model: qwen2.5
  base_url: http://localhost:11434

mcp:
  servers:
    - name: filesystem
      command: python
      args: [servers/filesystem_server.py]

channels:
  websocket:
    host: 127.0.0.1
    port: 8080
```

### logging_config.yaml

```yaml
version: 1
disable_existing_loggers: false
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/plector.log
    maxBytes: 10485760
    backupCount: 5
    formatter: default
root:
  level: INFO
  handlers: [console, file]
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PLECTOR_DB_PATH` | SQLite 数据库路径 | `data/plector.db` |
| `PLECTOR_LOG_LEVEL` | 日志级别 | `INFO` |
