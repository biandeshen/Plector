# Plector 开发规范

> Claude Code 会话启动时自动读取。
> 当前版本: `v2.0.0` | 技能: 11个 | 工具: 59个 | 核心模块: 29个
> 详见 [SOUL.md](SOUL.md) — LLM 元认知规则

## 核心原则

- **务实**: 先验证再优化，不过度工程化
- **简洁**: 代码和决策追求最小化
- **高效**: 直接给出结果，不绕弯子
- **严谨**: 出错返回结构化错误，不抛异常

### 禁止做的事

- ❌ 自己直接写代码 / 写内容（复杂任务需多角色协作）
- ❌ 不调用任何工具就直接执行复杂任务
- ❌ 只用一个技能完成复杂任务

### 应该做的事

- ✅ 先分析任务复杂度
- ✅ 调用 `agency_orchestrator` 编排多角色
- ✅ 从 `external-skills/` 匹配合适角色
- ✅ 多个技能协作完成
- ✅ 核心原则：少写死代码，多用 YAML + LLM

## 项目结构

```
Plector/
├── core/           # 核心引擎（无 skills/ 依赖）
├── skills/         # 技能（≤15个）：<name>/{skill.json, implementation.py}
├── servers/        # MCP Server：filesystem, sqlite, http_filesystem
├── channels/       # 渠道：cli.py, websocket.py, chat.html, dashboard.html
├── frontend/       # Vue 3 前端
├── config/         # 配置：config.yaml, profiles/, alerts.yaml
├── docs/           # 规格文档、代码规范、状态报告
├── external-skills/# 外部技能库（174个AI角色）
├── scripts/        # validate_skills.py, check_*.py
└── tests/          # 单元测试
```

## 命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 文件/目录 | 全小写，下划线 | `vector_memory.py` |
| 类名 | 驼峰 | `AgentLoop` |
| 函数 | 下划线分隔 | `execute_skill()` |
| 常量 | 全大写 | `MAX_ITERATIONS` |
| 事件 | `<domain>.<action>` | `health.degraded` |

## 核心模块 (core/)

| 模块 | 用途 |
|------|------|
| agent_loop.py | ReAct 主循环引擎 |
| closure_engine.py | 闭环引擎（条件图执行） |
| event_bus.py / v2.py | 事件驱动（CloudEvents 1.0） |
| skill_registry.py / loader.py / handler.py | 技能注册与加载 |
| mcp_client.py | MCP 客户端（连接外部 Server） |
| vector_memory.py / v2.py | 向量记忆（语义搜索） |
| llm_client_*.py | LLM 后端（Ollama/OpenAI/Anthropic/MiniMax） |
| workflow_graph.py | 工作流编排 |
| context_builder.py | 上下文构建 |
| config_loader.py | 配置加载 |
| image_handler.py / backends.py | 图片处理（多后端） |

## 技能清单 (skills/)

| 技能 | 工具数 | 用途 |
|------|--------|------|
| agency_orchestrator | 7 | 多智能体 YAML 工作流（**含前端重构防退化审查**） |
| auto_developer | 6 | 一键自动开发流水线 |
| memory | 11 | 记忆管理（艾宾浩斯遗忘曲线） |
| code_writer | 3 | 代码读写（**修改时遵循防退化规则**） |
| context_refresher | 4 | 上下文保鲜 |
| file_utils | 5 | 文件操作 |
| error_knowledge | 2 | 错误知识库 |
| web_search | 2 | 网页搜索 |
| test_runner | 2 | 测试运行 |
| health_monitor | 1 | 健康检查 |
| self_improver | 3 | 系统自改进 |

## MCP Server (servers/)

| Server | 工具数 | 用途 |
|--------|--------|------|
| filesystem_server.py | 6 | 本地文件系统 |
| http_filesystem_server.py | 3 | HTTP 文件系统 |
| sqlite_server.py | 4 | SQLite 数据库 |
| init_memory_db.py | 0 | 记忆库初始化 |

## 依赖方向

```
core/ ──→ 不依赖 skills/、tools/
skills/ ──→ 可依赖 core/，不依赖其他 skills/
```

## 技能开发

```
skills/<name>/
├── skill.json        # MCP Tool 格式，含 inputSchema
└── implementation.py # SkillHandler 类，方法名=工具名
```

**工具名称**: `{skill_name}_{method_name}`
**返回格式**: `{"success": bool, "data": any, "error": str|null}`
**事件格式**: CloudEvents 1.0
**错误格式**: JSON-RPC 2.0

**错误回传增强**：
涉及前端/UI 修改失败时，`error` 字段必须包含：
- `modified_lines`: 本次修改行号范围
- `recent_commits`: 最近 3 次相关 Git 提交 Hash（供快速回滚定位）

## LLM 元认知

遇到任务先问："这个任务够复杂吗？"
遇到修改任务先问："这个修改会影响已有功能吗？"

| 复杂度 | 处理方式 |
|--------|----------|
| 简单（单步） | 直接执行 |
| 复杂（多角色/跨领域） | context_refresher → agency_orchestrator → 多角色协作 |
| **修改现有文件** | **必须先 git 分析 → 最小变更 → 自检验证** |

**触发词映射**：

| 触发词 | 技能 |
|--------|------|
| "记住"、"回忆"、"偏好" | memory |
| "健康"、"CPU"、"内存" | health_monitor |
| "报错"、"出错" | error_knowledge |
| "继续" | context_refresher |
| "自我改进"、"升级" | self_improver |

## 🔒 前端/UI 修改规范

> ⚠️ **防止"改坏已有功能"的强制规则**

### 修改前必做

1. **读取当前文件完整内容** — 不读不写
2. **分析 Git 历史** — `git diff` 或 `git log -p` 理解历史上下文
3. **识别"不可触碰"区域** — 历史沉淀的微妙平衡点

### 修改中禁止

- ❌ **不读取当前文件就直接修改**
- ❌ **重写整个文件**（除非用户明确要求"重写"）
- ❌ **删除已有功能**（即使看起来"不需要"）
- ❌ **为适配新功能而重构原有逻辑**

### 修改后必做

1. **对比修改前后结构** — DOM/组件/样式层叠
2. **检查样式冲突** — 是否有 CSS 覆盖问题
3. **输出变更说明** — "我修改了 XX 部分，保留 YY 功能"
4. **高风险标记** — 若无法确认视觉一致性，输出：
   ```
   ⚠️ 高风险修改：请人工复核视觉
   ```

### 前端修改决策表

| 场景 | 策略 |
|------|------|
| 修改单个元素样式 | 只改 CSS，不动 HTML/JS |
| 添加新功能 | 在已有代码后追加，不改已有代码 |
| 修复 bug | 只改出问题的那几行 |
| 修改组件逻辑 | 先读懂原逻辑，只改相关函数 |
| 重写页面/组件 | **需要用户明确说"重写"才执行** |

## 推送前检查

```bash
python -m py_compile <file>.py      # 语法
python scripts/validate_skills.py   # skill.json
ruff check core/ skills/ channels/ # 代码格式
pre-commit run --all-files          # 全部检查
```

**提交格式**: `<type>(<scope>): <subject>` — feat/fix/docs/refactor/test/chore

## 验证命令

```bash
# 语法检查
python -m py_compile core/agent_loop.py

# 依赖方向
python scripts/check_dependencies.py

# 技能校验
python scripts/validate_skills.py

# 代码格式
ruff check core/ skills/ channels/

# 单元测试
pytest tests/ -v

# 启动
python channels/cli.py --query "你好"     # CLI
python channels/websocket.py --port 8080  # Web
```

## 异步规范

- 阻塞调用用 `run_in_executor`
- 禁止 `time.sleep()`，用 `asyncio.sleep()`
- 禁止裸 `except`
- 技能/工具失败返回 `{"error": "..."}`，不抛异常

## 代码规范 (pyproject.toml)

- **Python**: ≥3.10
- **行长度**: 120 字符
- **ruff 规则**: E/W/F/I/N/UP/B/SIM/RUF
- **允许**: 中文变量/注释（忽略 RUF001/002/003）
- **忽略**: E501(行长) SIM108(三元) N812(大小写import)

## 详细规格

- 代码规范: `docs/standards/Code_Standard_Plector.md`
- 技能开发: `docs/standards/Skill_Development_Plector.md`
- 命名规范: `docs/standards/Naming_Convention_Plector.md`
- 技术设计: `docs/specs/Design_Plector_v1.2.md`
- MCP 协议: `docs/guides/MCP_Server_Guide.md`
