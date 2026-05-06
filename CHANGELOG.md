# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-05-07

### Fixed
- **安全加固 Iter1**: skill_handler 3 层路径验证（symlink/is_relative_to/".." 拒止）、mcp_client 命令注入黑名单、llm_client Anthropic tool_use id 容错
- **架构优化 Iter2**: function_calling deepcopy 隔离、agent_loop 注入护栏+TTL 清理、mcp_client SSE 指数退避重连
- **mypy 清零**: 修复 14 个预存类型错误，core/ 全模块 strict 模式通过
- **pytest Windows 兼容性**: 绕过 asyncio 事件循环提前关闭 capture tmpfile 的问题
- **MiniMax 测试规范化**: print→assert，无服务器时 3 error→3 skipped

### Added
- **测试覆盖 Iter3**: 22 个新测试（路径攻击 5 / 循环检测 3 / 深拷贝 2 / TypeError 2 / TTL 2 / 复杂度 7 / 注入护栏 1）
- **共享 pytest fixtures**: conftest.py 5 个复用 fixture（tool_registry/basic_config/mock_skill_registry/mock_llm_client/agent_loop）

### Changed
- **文档同步**: CLAUDE.md/README.md/PLECTOR_SKILLS.md/DOCS_INDEX.md 等 7 文件同步到实际代码现状（37 模块/9 技能/34 工具）
- vector_memory 容量上限、closure_engine 循环检测回归测试

---

## [2.2.0] - 2026-05-05

### Added
- Phase 2 安全修复: 11 项 Critical/High 漏洞修复（test_runner shell=True、code_writer 路径遍历、skill_handler 动态加载、sqlite_server DDL 限制等）
- Phase 3 测试验证: 976 测试通过，pre-commit 全绿
- Phase 4 架构解释: 6 个核心模块深度分析文档
- Phase 5 重构方案: 3 迭代执行计划

### Changed
- **测试覆盖大幅提升**: Phase 2 测试补全（568+386 个用例），16 个核心模块全覆盖
- 核心模块数 32→37（image/ 子包拆分）
- 技能数 7→9（新集成 agency_orchestrator + context_refresher）

### Fixed
- 4 项 ship-review 阻断问题 (F1-F4)
- 7 模块 mypy 类型错误
- 4 项中风险 + 4 项低风险代码审查问题
- 10 项 Agent 审查阻断问题

---

## [2.1.0] - 2026-04-30

### Added
- AgentLoop 拆分为 4 个专注模块（ImageRouter / MemoryLoader / ConversationStore）
- ReAct 循环集成 EventBus 事件发布（5 种 CloudEvents 事件）
- MCPClient 支持 config 文件路径直接加载
- 代码健康修复: 清理依赖、启用 lint、类型现代化

### Changed
- AgentLoop 从 267 行降至 175 行，dependencies 11→4
- MCPManager 合并到 MCPClient（消除双连接路径）
- ConversationStore 使用线程本地连接池 + WAL 模式
- MemoryLoader 使用 VectorMemory 单例缓存
- timeout / sse_timeout / max_tokens 可配置

### Removed
- **core/mcp_manager.py** — 功能合并到 MCPClient

### Fixed
- get_all_tools() 外层循环导致工具重复输出
- test_minimax_search.py manager.clients→servers 引用遗漏

---

## [2.0.0] - 2026-04-28

### Added

- **Documentation Index System** - New `docs/DOCS_INDEX.md` for unified document navigation
- **CLAUDE.md v5.0.0** - Refactored to focus on behavioral constraints, delegating detailed index to DOCS_INDEX
- **Multi-Agent Review** - Five-role agent system (Architect, PM, Security, Growth, Ops) for strategic decisions
- **Security Enhancements** - OTel elevated to P0 priority, SecurityMiddleware implementation
- **Memory System v2.1.1** - Dynamic memory ecosystem with 8 recall modes, Ebbinghaus decay, retrieval reinforcement

### Changed

- **Positioning** - Repositioned from "self-evolution" to "enterprise-ready governance and integration"
- **Scope Reduction** - 174 roles → 5-10 (v2.x), 9 middleware → 3-4 core middleware
- **OTel as P0** - OpenTelemetry observability elevated to release-blocking priority
- **PRD v1.6** - Integrated five-role review conclusions, scope reduction, quantified metrics

### Fixed

- Skill hot-reload sometimes failing
- MCP reconnection mechanism

### Security

- Immutable audit log with WORM storage
- Hash chain for tamper evidence
- Input validation via SecurityMiddleware

---

## [1.4.0] - 2026-04-21

### Added

- Skill hot-reload mechanism (file hash detection)
- Skill format specification (SKILL.md standard)
- Competitive analysis documentation

### Changed

- Agency orchestrator optimization
- Memory system enhancements

---

## [1.3.0] - 2026-04-14

### Added

- Agency orchestrator with 174 predefined roles
- DAG parallel execution support
- MCP native integration
- YAML declarative workflow

### Changed

- Event bus stability improvements

---

## [1.2.0] - 2026-04-07

### Added

- WebSocket channel support
- Vue3 SPA dashboard
- Real-time bidirectional communication

---

## [1.1.0] - 2026-03-31

### Added

- MCP Client
- HTTP+SSE transport
- Multi-LLM backend support

---

## [1.0.0] - 2026-03-24

### Added

- Core agent engine
- CLI interface
- 11 core skills
- 59 tool functions
- ReAct decision loop
- Event-driven closure engine
- Skill registration system

---

## [0.1.0] - 2026-03-17

### Added

- Initial prototype
- Basic agent loop implementation
- Skill system skeleton

---

[Unreleased]: https://github.com/biandeshen/Plector/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/biandeshen/Plector/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/biandeshen/Plector/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/biandeshen/Plector/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/biandeshen/Plector/releases/tag/v2.0.0
[1.4.0]: https://github.com/biandeshen/Plector/releases/tag/v1.4.0
[1.3.0]: https://github.com/biandeshen/Plector/releases/tag/v1.3.0
[1.2.0]: https://github.com/biandeshen/Plector/releases/tag/v1.2.0
[1.1.0]: https://github.com/biandeshen/Plector/releases/tag/v1.1.0
[1.0.0]: https://github.com/biandeshen/Plector/releases/tag/v1.0.0
[0.1.0]: https://github.com/biandeshen/Plector/releases/tag/v0.1.0
