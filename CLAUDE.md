# Plector Development Rules

> Read by Claude Code at session start.

## 项目结构

```
plector/
├── core/          # 核心引擎（不依赖 skills/ tools/）
├── skills/        # 核心技能（≤15 个）
│   └── <name>/
│       ├── skill.json
│       └── implementation.py
├── tools/         # 工具函数（无限制）
│   └── <name>.py
├── channels/      # 接入渠道
├── config/        # 配置文件
├── docs/
│   ├── specs/     # BRD, PRD, Design
│   ├── standards/ # Code Standard, Naming Convention, Skill Standard
│   ├── reports/
│   └── dev/
├── tests/
├── scripts/       # validate_skills.py, check_skills.py
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
- 方法名：与 `skill.json` 中 `methods` 的 key 一致
- 返回格式：`{"success": bool, "data": any, "error": str or None}`
- 事件：用 `get_event_bus()` 发布/订阅
- 创建后：`python -m py_compile skills/<name>/implementation.py`
- 验证：`python scripts/validate_skills.py`

## 异步

- 阻塞调用必须用 `run_in_executor`
- 不要在 async 函数中用 `time.sleep()`

## 错误处理

- 技能/工具失败返回 `{"error": "..."}`，不抛异常
- 禁止裸 `except`

## 提交规范

```
<type>(<scope>): <subject>
```

- type: feat / fix / docs / refactor / test / chore
- scope: 模块名（`core`, `health_monitor`）
- 提交前：`python -m py_compile <file>.py`
- 提交后：`git push`

## 验证命令

```bash
python -m py_compile core/agent_loop.py
python -c "from core.agent_loop import AgentLoop; print('OK')"
python scripts/validate_skills.py
pytest tests/ -v
```

## 详细规范

- 代码规范：`docs/standards/Code_Standard_Plector.md`
- 技能开发：`docs/standards/Skill_Development_Plector.md`
- 文档命名：`docs/standards/Naming_Convention_Plector.md`
- 技术设计：`docs/specs/Design_Plector_v1.2.md`
