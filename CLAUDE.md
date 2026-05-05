# Plector 开发规范

> Claude Code 会话启动时自动读取。
> 模板版本：v1.1.0 | 最后更新：2026-05-05

---

## 索引架构

> **工具规范 → ECC 内置 | 项目规范 → docs/ | 元认知 → SOUL.md | 功能规格 → docs/specs/**

| 规范类型 | 来源 | 说明 |
|----------|------|------|
| **工具规范** | ECC 内置 | 156+ Skills / 38 Agents，跨项目通用 |
| **元认知规则** | [SOUL.md](SOUL.md) | 复杂度评估、决策树、熔断机制 |
| **项目规范** | `docs/` 目录 | 项目专用文档 |
| **功能规格** | `docs/specs/` | 复杂功能的事前设计蓝图 |

---

## 工具规范（ECC 内置）

ECC 已提供丰富的内置 Skills 和 Agents，无需额外配置：

| 类别 | 示例 Skill | 说明 |
|------|-----------|------|
| 代码审查 | `requesting-code-review` | 自动审查代码变更 |
| 架构分析 | `requesting-architect` | 架构评审和建议 |
| 文档生成 | `document-generation` | 自动生成文档 |
| 测试 | `tdd-explain` | TDD 工作流 |
| 重构 | `refactoring-explain` | 安全重构指导 |

**使用方式**：在 Claude Code 中直接描述需求，AI 会调用合适的 Skill。

**规范约束**：通过 [SOUL.md](SOUL.md) 的复杂度评估规则自动分流。

---

## 项目特有规范

### 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.10+ |
| Web 框架 | FastAPI | >=0.110.0 |
| ASGI 服务器 | Uvicorn | >=0.29.0 |
| WebSocket | websockets | >=12.0 |
| LLM 后端 | Ollama / OpenAI / Anthropic | — |
| 向量存储 | ChromaDB | >=0.5.0 |
| 代码质量 | ruff + mypy + pre-commit | — |
| 测试 | pytest + pytest-asyncio | >=7.0 |

### 项目结构

```
Plector/
├── core/                  # 核心引擎（14 个模块）
│   ├── agent_loop.py      # ReAct 主循环
│   ├── llm_client.py      # 多 LLM 后端（Ollama/OpenAI/Anthropic）
│   ├── mcp_client.py      # MCP 协议客户端
│   ├── skill_registry.py  # 技能注册中心
│   ├── event_bus.py       # CloudEvents 1.0 事件总线
│   └── vector_memory.py   # 向量记忆系统
├── skills/                # 技能目录（7 个内置技能）
├── servers/               # MCP Server（4 个）
├── channels/              # 渠道（CLI / WebSocket / Dashboard）
├── config/                # 配置文件
├── docs/                  # 项目文档
│   ├── specs/             # 功能规格
│   ├── standards/         # 编码/命名/Skill/技术规范
│   ├── guides/            # 用户指南
│   └── api/               # API 文档
├── tests/                 # 测试
├── scripts/               # 工具脚本
└── .claude/               # Claude Code 配置
```

### 启动命令

```bash
# 安装依赖
python -m venv venv && source venv/bin/activate  # Linux/macOS
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt

# CLI 模式
python channels/cli.py --query "你好"

# WebSocket 模式
python channels/websocket.py --port 8080

# 运行测试
pytest tests/ -v

# 代码检查
ruff check . && mypy core/

# Pre-commit 全量检查
pre-commit run --all-files
```

### 编码规范

> 详细规范见 `docs/standards/` 目录

- **行长度**: 120 字符（ruff line-length=120）
- **导入排序**: isort，已知 first-party 包：`core`, `skills`, `tools`, `channels`
- **类型检查**: mypy，Python 3.10，忽略缺失的第三方 stub
- **命名**: PEP8 命名规范（ruff N 规则）
- **异步**: 所有异步函数必须有 timeout
- **错误处理**: 返回结构化错误，不抛裸异常
- **中文**: 项目中允许中文标点（已关闭 RUF001/RUF002/RUF003）

### 架构约束

> 详见 [SOUL.md](SOUL.md) 复杂度评估规则

- **依赖方向**: core/ 不依赖 skills/ 和 channels/
- **函数长度**: 单函数 ≤50 行（`.claude/scripts/check_function_length.py`）
- **MCP 协议**: 技能定义遵循 MCP Tool 格式（skill.json）
- **事件标准**: CloudEvents 1.0（event_bus.py）
- **外部引用**: 通用规范索引 `E:/笔记/Claude Code规范/DOCS_INDEX.md`

---

## 文档索引

| 内容 | 位置 |
|------|------|
| **元认知规则** | [SOUL.md](SOUL.md) |
| **复杂度评估** | [SOUL.md → 复杂度自动评估规则](SOUL.md) |
| **架构设计** | [docs/ARCHITECTURE_DESIGN.md](docs/ARCHITECTURE_DESIGN.md) |
| **技能系统** | [docs/PLECTOR_SKILLS.md](docs/PLECTOR_SKILLS.md) |
| **同步机制** | [docs/SYNCHRONIZATION_MECHANISM.md](docs/SYNCHRONIZATION_MECHANISM.md) |
| **功能规格** | `docs/specs/` 目录 |
| **规格模板** | [SPEC_Template.md](.claude/SPEC_Template.md) — 功能级设计蓝图模板 |
| **编码规范** | `docs/standards/` 目录 |
| **API 文档** | `docs/api/` 目录 |
| **项目文档总索引** | [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md) |

---

### Spec 优先原则

> 复杂功能开发前，AI 必须遵循：
> 1. 先检查 `docs/specs/` 是否有相关 Spec
> 2. 若无 → 参考 [SPEC_Template.md](.claude/SPEC_Template.md) 创建
> 3. Spec 定稿后再进入 SOUL.md 决策树执行

### 记忆系统

本项目使用 `.claude/memory/MEMORY.md` 管理项目记忆（单文件，内部分章节）：

| 章节 | 内容 |
|------|------|
| 索引表（文件顶部） | AI 启动时先读索引获取记忆概览 |
| 架构决策 (ADR) | 项目架构决策及原因 |
| Bug 模式 | Bug 模式与根因 |
| 编码模式 | 编码模式/约定 |
| 领域知识 | 项目背景/领域知识 |

**AI 行为规则：**
- 每次会话启动时先读 `.claude/memory/MEMORY.md` 顶部的索引表
- 修复复杂 Bug（排查 > 30 分钟）后，在对话末尾提议记录到 MEMORY.md 的「Bug 模式」章节
- 做出架构决策后，提议记录到 MEMORY.md 的「架构决策 (ADR)」章节（必须包含决策原因）
- `/commit`、`/fix`、`/review` 关键操作后，检查是否需要记录记忆
- 用户说"之前怎么修的/上次/我记得"时，自动搜索记忆库
- **禁止**在记忆中记录：密钥/Token/密码、内网IP、对人评价、未公开商业策略

**安全管理：**
- 共享记忆写入 `.claude/memory/MEMORY.md`（提交到 Git）
- 个人私密内容写入 `MEMORY.local.md`（gitignored，不提交）
- 记忆提交到 Git 前，pre-commit hook 会自动扫描密钥

---

## 版本历史

- `v1.1.0` (2026-05-05)：补充 Plector 项目特有规范 — 技术栈、项目结构、启动命令、编码规范、架构约束
- `v1.0.0` (2026-05-01)：初始化项目规范，基于 ECC + 双索引架构

---

*核心原则：工具规范由 ECC 提供，项目规范放在 `docs/`*
