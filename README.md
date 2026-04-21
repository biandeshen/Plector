# Plector

> 事件驱动的 AI Agent 引擎
>
> **当前版本**: `v2.0.0`
> **技能**: 11 个 | **工具**: 59 个 | **核心模块**: 29 个

---

## 📋 AI 协作规范

本项目为 Claude Code 配置了严格的工作流规范。在开始任何复杂任务前，请确保 Claude 已读取以下文件：

- **[CLAUDE.md](CLAUDE.md)** — 开发规范、技能清单、防退化规则
- **[SOUL.md](SOUL.md)** — 智能任务执行工作流、元认知规则
- **[PLAN_TEMPLATE.md](PLAN_TEMPLATE.md)** — 任务执行计划标准模板

> 对于复杂任务，Claude 将自动创建 `Plan.md` 并全程记录执行状态。

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
├── core/config_loader.py             #
├── core/content_filter.py            #
├── core/context_builder.py           #
├── core/error_handler.py             #
├── core/event_bus.py                 #
├── core/event_bus_v2.py              #
├── core/function_calling.py          #
├── core/governance.py                #
├── core/image_handler.py             #
├── core/llm_client_anthropic.py      #
├── core/llm_client_base.py           #
├── core/llm_client_minimax.py        #
├── core/llm_client_ollama.py         #
├── core/llm_client_openai.py         #
├── core/llm_client_v2.py             #
├── core/mcp_client.py                #
├── core/metrics.py                   #
├── core/middleware_chain.py          #
├── core/path_manager.py              #
├── core/rate_limiter.py              #
├── core/skill_handler.py             #
├── core/skill_loader.py              #
├── core/skill_registry.py            #
├── core/skill_sandbox.py             #
├── core/vector_memory.py             #
├── core/vector_memory_v2.py          #
├── core/workflow_graph.py            #
├── skills/                          # 11 个技能
│   ├── agency_orchestrator/    # Agency Orchestrator — 多智能体 YAML 工作流引擎，174 个 AI 角色，支持 DAG 并行执行、变量传递、条件分支、循环迭代、Resume 断点续跑。使用已有 AI 会员（Claude Max/GitHub Copilot/ChatGPT Plus）即可运行，无需 API key。 (7 tools)
│   ├── auto_developer/         # 一键自动开发流水线 — 从需求到代码的全自动流程。使用 agency-orchestrator 调度 174 个专家角色协作，Claude Code 执行代码开发。一句话描述需求，自动生成工作流并执行。 (6 tools)
│   ├── code_writer/            # 代码编写技能，支持写入、读取、修改代码文件 (3 tools)
│   ├── context_refresher/      # 防止长对话中 AI 遗忘初始目标，自动提取和注入 GSD 上下文 (4 tools)
│   ├── error_knowledge/        # 错误知识库技能 - 记录错误并分类分析，存储到本地知识库。当用户报告错误或遇到问题时使用。返回格式：{success, data, error} (2 tools)
│   ├── file_utils/             # 文件操作技能，支持列表、复制、移动、删除文件 (5 tools)
│   ├── health_monitor/         # 获取系统健康状态，包括 CPU、内存、磁盘使用率 (1 tools)
│   ├── memory/                 # 记忆管理技能，存储和查询对话历史、用户偏好、知识记忆，支持艾宾浩斯遗忘曲线和8种关联记忆模式。当用户提到"记住"、"回忆"、"偏好"、"之前聊过"时使用。 (11 tools)
│   ├── self_improver/          # Plector 自我改进技能 - 使用多角色协作方式完成系统升级和优化。当用户说「自我改进」、「系统升级」、「自动优化」时使用。返回格式：{success, data, error} (3 tools)
│   ├── test_runner/            # 测试运行技能，支持运行 pytest 并返回结果 (2 tools)
│   ├── web_search/             # 网页搜索技能，使用博查 API 搜索互联网内容（国内可用） (2 tools)
├── servers/                         # 4 个 MCP Server
│   └── filesystem_server.py    # filesystem (6 tools)
│   └── http_filesystem_server.py # http_filesystem (3 tools)
│   └── init_memory_db.py       # init_memory_db (0 tools)
│   └── sqlite_server.py        # sqlite (4 tools)
├── channels/                        # 5 个渠道
│   └── cli.py
│   └── websocket.py
│   └── chat.html
│   └── chat_legacy.html
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
| agency_orchestrator | run_workflow, validate_workflow, list_workflows, plan_workflow, compose_workflow, list_roles, get_role | Agency Orchestrator — 多智能体 YAML 工作流引擎，174 个 AI 角色，支持 DAG 并行执行、变量传递、条件分支、循环迭代、Resume 断点续跑。使用已有 AI 会员（Claude Max/GitHub Copilot/ChatGPT Plus）即可运行，无需 API key。 |
| auto_developer | develop, compose, run, plan, list_roles, list_workflows | 一键自动开发流水线 — 从需求到代码的全自动流程。使用 agency-orchestrator 调度 174 个专家角色协作，Claude Code 执行代码开发。一句话描述需求，自动生成工作流并执行。 |
| code_writer | write_code, read_code, modify_code | 代码编写技能，支持写入、读取、修改代码文件 |
| context_refresher | preserve, get_context, re_anchor, inject_context | 防止长对话中 AI 遗忘初始目标，自动提取和注入 GSD 上下文 |
| error_knowledge | store_error, classify_error | 错误知识库技能 - 记录错误并分类分析，存储到本地知识库。当用户报告错误或遇到问题时使用。返回格式：{success, data, error} |
| file_utils | list_files, copy_file, move_file, delete_file, read_file | 文件操作技能，支持列表、复制、移动、删除文件 |
| health_monitor | check_health | 获取系统健康状态，包括 CPU、内存、磁盘使用率 |
| memory | save_conversation, get_conversation_history, save_preference, get_preference, save_knowledge, search_knowledge, semantic_search, associative_search, check_memory_decay, reinforce_memory, memory_stats | 记忆管理技能，存储和查询对话历史、用户偏好、知识记忆，支持艾宾浩斯遗忘曲线和8种关联记忆模式。当用户提到"记住"、"回忆"、"偏好"、"之前聊过"时使用。 |
| self_improver | start_upgrade, get_status, stop_upgrade | Plector 自我改进技能 - 使用多角色协作方式完成系统升级和优化。当用户说「自我改进」、「系统升级」、「自动优化」时使用。返回格式：{success, data, error} |
| test_runner | run_tests, run_command | 测试运行技能，支持运行 pytest 并返回结果 |
| web_search | search, fetch_page | 网页搜索技能，使用博查 API 搜索互联网内容（国内可用） |
| MCP: filesystem | (远程工具) | MCP Server |
| MCP: http_filesystem | (远程工具) | MCP Server |
| MCP: init_memory_db | (远程工具) | MCP Server |
| MCP: sqlite | (远程工具) | MCP Server |
| **总计** | **59 个** | |

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
