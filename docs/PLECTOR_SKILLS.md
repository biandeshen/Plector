# Plector 技能清单

> Plector 系统内置技能，通过 Web UI（http://localhost:8081）调用。

---

## 项目结构

```
Plector/
├── core/                # 核心引擎
├── skills/              # Plector 技能
├── servers/             # MCP Server
├── channels/            # 渠道
├── frontend/            # Vue 3 前端
├── config/              # 配置
└── tests/               # 测试
```

---

## 技能列表

| 技能 | 工具数 | 用途 |
|------|--------|------|
| `agency_orchestrator` | 7 | 多智能体 YAML 工作流 |
| `auto_developer` | 6 | 一键自动开发流水线 |
| `memory` | 11 | 记忆管理（艾宾浩斯遗忘曲线） |
| `code_writer` | 3 | 代码读写 |
| `context_refresher` | 4 | 上下文保鲜 |
| `file_utils` | 5 | 文件操作 |
| `error_knowledge` | 2 | 错误知识库 |
| `web_search` | 2 | 网页搜索 |
| `test_runner` | 2 | 测试运行 |
| `health_monitor` | 1 | 健康检查 |
| `self_improver` | 3 | 系统自改进 |

---

## 触发词映射

| 触发词 | 技能 |
|--------|------|
| "记住"、"回忆" | `memory` |
| "健康"、"CPU" | `health_monitor` |
| "报错" | `error_knowledge` |
| "继续" | `context_refresher` |
| "自我改进" | `self_improver` |

---

## 验证命令

```bash
python -m py_compile core/agent_loop.py    # 语法检查
python scripts/check_dependencies.py         # 依赖方向
python scripts/validate_skills.py            # 技能校验
ruff check core/ skills/ channels/          # 代码格式
pytest tests/ -v                             # 单元测试
```

---

## 启动命令

```bash
python channels/cli.py --query "你好"      # CLI
python channels/websocket.py --port 8080    # Web
```
