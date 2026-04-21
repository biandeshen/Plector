# Plector 技能清单

> Plector 系统内置技能，通过 Web UI（http://localhost:8081）调用。
> 版本：v1.0.0 | 最后更新：2026-04-20

---

## 项目结构

```
Plector/
├── core/                # 核心引擎
│   ├── agent_loop.py    # ReAct 循环
│   ├── event_bus.py     # 事件总线
│   ├── skill_registry.py # 技能注册表
│   └── skill_handler.py  # 技能执行器
├── skills/              # Plector 技能
├── servers/             # MCP Server
├── channels/            # 渠道
├── frontend/            # Vue 3 前端
├── config/              # 配置
└── tests/               # 测试
```

---

## 技能列表

| 技能 | 工具数 | 用途 | 触发词 |
|------|--------|------|--------|
| `agency_orchestrator` | 7 | 多智能体 YAML 工作流 | "编排"、"工作流" |
| `auto_developer` | 6 | 一键自动开发流水线 | "自动开发"、"开发流水线" |
| `memory` | 11 | 记忆管理（艾宾浩斯遗忘曲线） | "记住"、"回忆" |
| `code_writer` | 3 | 代码读写 | "写代码"、"代码生成" |
| `context_refresher` | 4 | 上下文保鲜 | "继续"、"上下文" |
| `file_utils` | 5 | 文件操作 | "文件"、"读写文件" |
| `error_knowledge` | 2 | 错误知识库 | "报错"、"错误" |
| `web_search` | 2 | 网页搜索 | "搜索"、"查一下" |
| `test_runner` | 2 | 测试运行 | "测试"、"运行测试" |
| `health_monitor` | 1 | 健康检查 | "健康"、"CPU" |
| `self_improver` | 3 | 系统自改进 | "自我改进" |

---

## 技能 vs 工具（治理区别）

| 对比项 | 技能（Skill） | 工具（Tool） |
|--------|---------------|-------------|
| 数量限制 | ≤ 15 个 | 无限制 |
| 治理 | ✅ 健康分、淘汰 | ❌ |
| 事件 | ✅ 可发布/订阅 | ❌ |
| 元数据 | `skill.json`（必须） | 无 |
| 目录 | `skills/<name>/` | `tools/<name>.py` |

**判断标准**：出错是否影响系统稳定性或核心闭环。

---

## 触发词映射

| 触发词 | 技能 |
|--------|------|
| "记住"、"回忆" | `memory` |
| "健康"、"CPU" | `health_monitor` |
| "报错"、"错误" | `error_knowledge` |
| "继续"、"上下文" | `context_refresher` |
| "自我改进" | `self_improver` |
| "编排"、"工作流" | `agency_orchestrator` |
| "测试"、"运行测试" | `test_runner` |

---

## 技能开发规范

详见 `docs/standards/Skill_Development_Plector.md`

### 目录结构

```
skills/<skill_name>/
├── skill.json          # 元数据（必须）
├── implementation.py   # 实现代码（必须）
└── SKILL.md            # 技能描述（可选）
```

### skill.json 必需字段

```json
{
  "name": "<skill_name>",
  "description": "技能描述",
  "version": "1.0.0",
  "tier": "tier_2_functional",
  "dependencies": [],
  "events_produced": [],
  "events_consumed": [],
  "tools": [...]
}
```

---

## 验证命令

```bash
# 语法检查
python -m py_compile core/agent_loop.py

# 依赖方向检查
python scripts/check_dependencies.py

# 技能校验
python scripts/validate_skills.py

# 代码格式
ruff check core/ skills/ channels/

# 单元测试
pytest tests/ -v
```

---

## 启动命令

```bash
# CLI 模式
python channels/cli.py --query "你好"

# WebSocket 模式
python channels/websocket.py --port 8080
```

---

## 与 Claude Code Skill 的区别

| 对比项 | Plector 技能 | Claude Code Skill |
|--------|-------------|------------------|
| 调用方式 | Web UI / Agent Loop | Claude Code 自身 |
| 触发词 | 上述映射表 | Claude Code 内部 |
| 存储位置 | `skills/<name>/` | Claude Code 记忆 |
| 数量限制 | ≤ 15 个 | 无限制 |

---

*版本：v1.0.0 | 最后更新：2026-04-20*
