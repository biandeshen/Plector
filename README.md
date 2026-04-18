# Plector

事件驱动的 AI Agent 引擎，支持技能治理、闭环自愈和多 LLM 后端。

## 功能概览

- **ReAct 自主决策循环**: LLM 推理-行动-观察循环，自动调用工具完成任务
- **技能治理**: 健康分监控、依赖检查、自动淘汰
- **闭环引擎**: YAML 条件图驱动的事件响应和自愈流程
- **MCP 协议**: 通过 stdio 连接外部 MCP Server，扩展工具能力
- **多 LLM 后端**: Ollama / OpenAI / Anthropic
- **Chat SPA**: Vue 3 + TypeScript 现代化 Web 对话界面

## 项目结构

```
plector/
├── core/               # 核心引擎（不依赖 skills/ 和 tools/）
├── skills/             # 核心技能（<= 15 个）
├── tools/              # 工具函数（无状态、无治理）
├── channels/           # 接入渠道（CLI / WebSocket）
├── frontend/           # Vue 3 SPA 前端
├── servers/            # MCP Server
├── config/             # 配置文件
├── docs/               # 项目文档
│   ├── specs/          #   BRD / PRD / Design
│   ├── standards/      #   编码规范 / 技术规范 / 技能开发规范
│   ├── reports/        #   项目状态报告
│   └── guides/         #   部署指南
└── tests/              # 测试
```

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | >= 3.10 |
| Node.js | >= 20.x |
| npm | >= 10.x |

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 构建前端

```bash
cd frontend
npm install
npm run build
```

构建产物输出到 `frontend/dist/`，后端自动挂载。

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 LLM API Key 等配置
```

### 4. 启动服务

```bash
# CLI 模式
python channels/cli.py

# WebSocket + Web 界面
python channels/websocket.py
```

启动后访问:
- `http://localhost:8080/chat` - Chat SPA（Vue 3）
- `http://localhost:8080/chat-legacy` - 旧版界面（回退方案）
- `http://localhost:8080/dashboard` - 管理面板

## 前端开发

```bash
cd frontend
npm run dev          # 启动 Vite 开发服务器（localhost:5173）
npm run build        # 生产构建
npm run preview      # 预览构建产物
```

开发模式下 Vite 会自动代理 `/api` 和 `/ws` 请求到后端 `localhost:8080`。

### 前端技术栈

| 技术 | 用途 |
|------|------|
| Vue 3 + TypeScript | UI 框架 |
| Pinia | 状态管理 |
| Vite 6 | 构建工具 |
| marked + highlight.js | Markdown 渲染 + 代码高亮 |

## 测试

```bash
# 后端测试
python -m pytest tests/ -q

# 前端类型检查
cd frontend && npx vue-tsc -b
```

## 文档

| 文档 | 路径 |
|------|------|
| 产品需求 (PRD) | `docs/specs/PRD_Plector_v1.2.md` |
| 业务需求 (BRD) | `docs/specs/BRD_Plector_v1.1.md` |
| 技术设计 | `docs/specs/Design_Plector_v1.2.md` |
| 技术规范 | `docs/standards/Technical_Spec_Plector.md` |
| 编码规范 | `docs/standards/Code_Standard_Plector.md` |
| 技能开发规范 | `docs/standards/Skill_Development_Plector.md` |
| 部署指南 | `docs/guides/Deployment_Guide.md` |
| 项目状态 | `docs/reports/Project_Status_Plector_20260404.md` |

## 许可证

MIT
