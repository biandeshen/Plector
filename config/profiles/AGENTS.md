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
| 了解前端架构 | docs/specs/Design_Plector_v1.2.md (第 9 章) |
| 了解 API 协议 | docs/standards/Technical_Spec_Plector.md (第 8-9 章) |
| 部署指南 | docs/guides/Deployment_Guide.md |

## 硬性规则
1. core/ 不依赖 skills/ 和 tools/
2. 技能数量 <= 15
3. 函数不超过 50 行
4. 返回值格式: {"success", "data", "error"}

## 构建与测试命令

### 后端
```bash
python -m pytest tests/ -q         # 运行测试（104 个）
ruff check .                       # 代码格式检查
mypy .                             # 类型检查
```

### 前端
```bash
cd frontend
npm install                        # 安装依赖
npm run build                      # 生产构建（vue-tsc + vite build）
npm run dev                        # 开发服务器（localhost:5173）
```

## 前端目录结构
```
frontend/src/
├── types/            # TypeScript 接口定义
├── stores/           # Pinia 状态管理（connection.ts, chat.ts）
├── composables/      # 组合式函数（useThinkFilter, useMarkdown, useAutoResize）
├── services/         # API 客户端（api.ts）
├── components/       # Vue 组件（15 个）
│   ├── layout/       #   AppHeader
│   ├── chat/         #   AssistantMessage, MessageList, ChatMain 等
│   ├── tools/        #   ToolSummaryPanel, ToolCallCard
│   ├── input/        #   MessageInput
│   └── sidebar/      #   ConversationSidebar
└── styles/           # CSS（variables, base, animations, markdown）
```
