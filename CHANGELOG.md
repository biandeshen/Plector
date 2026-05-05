# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- AgentLoop 拆分为 4 个专注模块（ImageRouter / MemoryLoader / ConversationStore）
- ReAct 循环集成 EventBus 事件发布（5 种 CloudEvents 事件）
- MCPClient 支持 config 文件路径直接加载

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

### Security

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

[Unreleased]: https://github.com/biandeshen/Plector/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/biandeshen/Plector/releases/tag/v2.0.0
[1.4.0]: https://github.com/biandeshen/Plector/releases/tag/v1.4.0
[1.3.0]: https://github.com/biandeshen/Plector/releases/tag/v1.3.0
[1.2.0]: https://github.com/biandeshen/Plector/releases/tag/v1.2.0
[1.1.0]: https://github.com/biandeshen/Plector/releases/tag/v1.1.0
[1.0.0]: https://github.com/biandeshen/Plector/releases/tag/v1.0.0
[0.1.0]: https://github.com/biandeshen/Plector/releases/tag/v0.1.0
