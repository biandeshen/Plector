# Plector

> 事件驱动的 AI Agent 引擎
>
> **当前版本**: `v1.7.0`
> **技能**: 7 个 | **工具**: 36 个 | **核心模块**: 12 个

---

## 快速开始

```bash
# 克隆
git clone https://github.com/biandeshen/Plector.git
cd Plector

# 安装依赖
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 配置 LLM（三选一）
ollama pull qwen3:4b && ollama serve          # Ollama（本地）
export OPENAI_API_KEY="sk-xxx"               # OpenAI
export ANTHROPIC_API_KEY="sk-ant-xxx"        # Anthropic

# 运行
python channels/cli.py --query "你好"         # CLI 模式
python channels/websocket.py --port 8080      # Web 模式
```

---

## 核心能力

- **自主决策**: ReAct 循环，LLM 推理 → 调用工具 → 观察 → 迭代
- **多 LLM 后端**: Ollama / OpenAI / Anthropic
- **技能系统**: 插件化技能，MCP 格式定义
- **事件驱动**: CloudEvents 1.0，组件异步解耦
- **MCP 协议**: 连接外部 MCP Server，引入现成工具
- **闭环引擎**: 条件图执行，支持自动修复
- **Harness**: 7 项自动化检查，约束代码质量

---

## 项目结构

```
Plector/
├── core/agent_loop.py                # 
├── core/closure_engine.py            # 
├── core/config_loader.py             # 配置加载模块，支持环境变量替换
├── core/context_builder.py           # 
├── core/event_bus.py                 # 
├── core/function_calling.py          # 
├── core/governance.py                # 
├── core/llm_client.py                # 
├── core/mcp_client.py                # 
├── core/skill_handler.py             # 
├── core/skill_registry.py            # 
├── core/vector_memory.py             # 
├── skills/                          # 7 个技能
│   ├── code_writer/            # 代码编写技能，支持写入、读取、修改代码文件 (3 tools)
│   ├── error_knowledge/        # 记录错误并分类，存储到本地知识库 (2 tools)
│   ├── file_utils/             # 文件操作技能，支持列表、复制、移动、删除文件 (5 tools)
│   ├── health_monitor/         # 获取系统健康状态，包括 CPU、内存、磁盘使用率 (1 tools)
│   ├── memory/                 # 记忆管理技能，存储和查询对话历史、用户偏好、知识记忆。当用户提到"记住"、"回忆"、"偏好"、"之前聊过"时使用。 (8 tools)
│   ├── test_runner/            # 测试运行技能，支持运行 pytest 并返回结果 (2 tools)
│   ├── web_search/             # 网页搜索技能，使用博查 API 搜索互联网内容（国内可用） (2 tools)
├── servers/                         # 4 个 MCP Server
│   └── filesystem_server.py    # filesystem (6 tools)
│   └── http_filesystem_server.py # http_filesystem (3 tools)
│   └── init_memory_db.py       # init_memory_db (0 tools)
│   └── sqlite_server.py        # sqlite (4 tools)
├── channels/                        # 3 个渠道
│   └── cli.py
│   └── websocket.py
│   └── dashboard.html
├── config/                         # 配置
├── docs/                           # 文档
├── scripts/                        # 检查脚本
├── tests/                          # 单元测试
├── CLAUDE.md                       # Claude Code 规范
└── README.md
```

---

## 技能清单

| 技能 | 工具 | 用途 |
|------|------|------|
| code_writer | write_code, read_code, modify_code | 代码编写技能，支持写入、读取、修改代码文件 |
| error_knowledge | store_error, classify_error | 记录错误并分类，存储到本地知识库 |
| file_utils | list_files, copy_file, move_file, delete_file, read_file | 文件操作技能，支持列表、复制、移动、删除文件 |
| health_monitor | check_health | 获取系统健康状态，包括 CPU、内存、磁盘使用率 |
| memory | save_conversation, get_conversation_history, save_preference, get_preference, save_knowledge, search_knowledge, semantic_search, memory_stats | 记忆管理技能，存储和查询对话历史、用户偏好、知识记忆。当用户提到"记住"、"回忆"、"偏好"、"之前聊过"时使用。 |
| test_runner | run_tests, run_command | 测试运行技能，支持运行 pytest 并返回结果 |
| web_search | search, fetch_page | 网页搜索技能，使用博查 API 搜索互联网内容（国内可用） |
| MCP: filesystem | (远程工具) | MCP Server |
| MCP: http_filesystem | (远程工具) | MCP Server |
| MCP: init_memory_db | (远程工具) | MCP Server |
| MCP: sqlite | (远程工具) | MCP Server |
| **总计** | **36 个** | |

---

## 标准对齐

| 标准 | 组件 | 状态 |
|------|------|------|
| MCP Tool 格式 | skill.json | ✅ |
| OpenAI Function Calling | function_calling.py | ✅ |
| CloudEvents 1.0 | event_bus.py | ✅ |
| JSON-RPC 2.0 | function_calling.py + mcp_client.py | ✅ |
| MCP Protocol | mcp_client.py | ✅ |

---

## Harness（代码质量保障）

| 检查项 | 说明 |
|--------|------|
| 依赖方向 | core/ 不依赖 skills/ tools/ |
| 函数长度 | 单函数 ≤50 行 |
| 技能语法 | Python 语法检查 |
| skill.json 格式 | MCP Tool 格式校验 |
| ruff 代码格式 | PEP8 + 最佳实践 |
| mypy 类型检查 | 静态类型检查 |
| pre-commit | Git 提交前自动检查 |

```bash
pre-commit run --all-files  # 运行全部检查
```

---

## 渠道

| 渠道 | 启动方式 | 访问 |
|------|---------|------|
| CLI | `python channels/cli.py --query "你好"` | 终端 |
| WebSocket | `python channels/websocket.py` | http://localhost:8080 |

---

## 文档

| 文档 | 说明 |
|------|------|
| CLAUDE.md | Claude Code 开发规范 |
| docs/specs/ | 需求文档（BRD / PRD / Design） |
| docs/standards/ | 规范文档（Code / Naming / Skill / Technical） |
| docs/reports/ | 状态报告 |

---

## License

MIT
