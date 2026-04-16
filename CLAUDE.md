# Plector Development Rules

> Read by Claude Code at session start.
> 
> See also: SOUL.md — Plector 的灵魂（LLM 元认知规则）

## 项目结构

```
plector/
├── core/          # 核心引擎（不依赖 skills/ tools/）
│   ├── mcp_client.py       # MCP Client（连接外部 MCP Server）
├── servers/       # MCP Server（纯 Python 实现）
│   └── filesystem_server.py
├── skills/        # 核心技能（≤15 个）
│   └── <name>/
│       ├── skill.json
│       └── implementation.py
├── tools/         # 工具函数（无限制）
│   └── <name>.py
├── channels/      # 接入渠道
│   ├── cli.py              # CLI 渠道
│   ├── websocket.py         # WebSocket 渠道 + REST API
│   └── dashboard.html       # Dashboard 页面
├── config/        # 配置文件
├── docs/
│   ├── specs/     # BRD, PRD, Design
│   ├── standards/ # Code Standard, Naming Convention, Skill Standard
│   └── reports/
│       └── dev/
├── tests/
├── scripts/       # validate_skills.py, check_skills.py
├── SOUL.md        # LLM 元认知规则（技能主动联动）
└── CLAUDE.md
```

## 命名

- 文件/目录：全小写，下划线分隔
- 类名：驼峰命名（`AgentLoop`）
- 函数：全小写，下划线分隔（`execute_skill`）
- 常量：全大写，下划线分隔（`MAX_ITERATIONS`）
- 事件：`<domain>.<action>`（`health.degraded`）

## 依赖方向

- `core/` → 不依赖 `skills/`、`tools/`
- `skills/` → 可依赖 `core/`，不依赖其他 `skills/`
- `tools/` → 不依赖 `skills/`、`core/`

## 技能 vs 工具

- 技能：出错影响系统稳定性，≤15 个，需要 `skill.json`
- 工具：出错不影响核心流程，无限制，用 `@tool` 装饰器

## 技能开发

- 目录：`skills/<name>/`，含 `skill.json` + `implementation.py`
- 类名：`SkillHandler`
- 方法名：与 `skill.json` 中 `tools` 的 `name` 一致
- 工具名称：`{skill_name}_{method_name}`（`_` 分隔）
- 参数定义：`tools[].inputSchema`（JSON Schema，需含 additionalProperties: false）
- 返回格式：`{"success": bool, "data": any, "error": str or None}`
- 事件：CloudEvents 格式，用 `get_event_bus()` 发布/订阅
- 错误：JSON-RPC 2.0 格式（error.code + error.message）
- 创建后：`python -m py_compile skills/<name>/implementation.py`
- 验证：`python scripts/validate_skills.py`

## 异步

- 阻塞调用必须用 `run_in_executor`
- 不要在 async 函数中用 `time.sleep()`

## 错误处理

- 技能/工具失败返回 `{"error": "..."}`，不抛异常
- 禁止裸 `except`

## LLM 元认知规则（重要）

遇到任务时，必须先思考：
```
"这个任务够复杂吗？"
```

**决策树：**

```
任务进来
    ↓
["这个任务够复杂吗？"]
    ↓
如果复杂（多角色/多阶段/跨领域）
    → 调用 context_refresher 分析复杂度
    → 调用 agency_orchestrator.compose_workflow 编排多角色
    → 从 external-skills/ 匹配合适角色
    → 多角色协作完成
    ↓
如果简单（单步/单领域/已知模式）
    → 直接执行
    ↓
注意：永远不要不调用任何工具就直接执行复杂任务
```

**触发词对应：**

| 触发词 | 技能 | 说明 |
|--------|------|------|
| "记住"、"回忆"、"偏好"、"之前聊过" | memory | 记忆管理 |
| "系统健康"、"CPU"、"内存"、"磁盘" | health_monitor | 健康检查 |
| "报错"、"出错了"、"错误" | error_knowledge | 错误记录 |
| "继续"、"有任何进展" | context_refresher | 上下文保鲜 |
| 复杂任务 | context_refresher + agency_orchestrator | 多角色协作 |
| "自我改进"、"系统升级"、"自动优化" | self_improver | Plector 自改进 |

## 推送前检查清单

- [ ] `python -m py_compile <file>.py` 无语法错误
- [ ] `python scripts/check_dependencies.py` 依赖方向正确
- [ ] `python scripts/check_function_length.py` 函数 ≤50 行
- [ ] `python scripts/validate_skills.py` skill.json 格式正确
- [ ] `ruff check` 无错误
- [ ] 无 `print()` 调试语句
- [ ] 所有异常都有处理
- [ ] 阻塞调用用 `run_in_executor`

推送格式：
```
<type>(<scope>): <subject>
```
- type: feat / fix / docs / refactor / test / chore
- 推送后：`git push`

## 验证命令

```bash
# 语法检查
python -m py_compile core/agent_loop.py

# 依赖方向
python scripts/check_dependencies.py

# 函数长度
python scripts/check_function_length.py

# 技能校验
python scripts/validate_skills.py

# 代码格式
ruff check core/ skills/ tools/ channels/

# 单元测试
pytest tests/ -v

# 全部检查（pre-commit）
pre-commit run --all-files

# 启动 WebSocket 渠道
python channels/websocket.py --port 8080

# 访问 Dashboard
# http://localhost:8080
```

## 详细规格

- 代码规格：`docs/standards/Code_Standard_Plector.md`
- 技能开发：`docs/standards/Skill_Development_Plector.md`
- 文档命名：`docs/standards/Naming_Convention_Plector.md`
- 技术设计：`docs/specs/Design_Plector_v1.2.md`
- 技术规格：`docs/standards/Technical_Spec_Plector.md`（如有）
