# AGENTS.md

## 项目简介

Plector - 事件驱动的 AI Agent 引擎，支持技能治理和闭环自愈。

## 快速导航

| 你想做什么 | 去哪里看 |
|-----------|----------|
| 了解系统架构 | docs/specs/Design_Plector_v1.2.md |
| 了解编码规范 | docs/standards/Code_Standard_Plector.md |
| 了解技能开发 | docs/standards/Skill_Development_Plector.md |
| 了解闭环配置 | config/closed_loops.yaml |

## 硬性规则

1. core/ 不依赖 skills/ 和 tools/
2. 技能数量 ≤ 15
3. 函数不超过 50 行
4. 返回值格式: {"success", "data", "error"}
