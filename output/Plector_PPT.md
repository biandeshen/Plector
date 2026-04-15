# Plector 项目介绍 PPT

> 事件驱动的 AI Agent 引擎
> 版本: v1.8.0 | 技能: 9个 | 工具: 49个 | 核心模块: 13个

---

## 第1页：封面

# Plector

## 事件驱动的 AI Agent 引擎

**技能治理 · 闭环自愈 · 自主决策**

- v1.8.0
- 事件驱动
- MCP 协议

---

## 第2页：议程

# 议程

1. 项目概述
2. 核心架构
3. 核心功能
4. 技术特性
5. 应用场景
6. 未来规划

---

## 第3页：什么是 Plector

# 什么是 Plector

一个**事件驱动**的 AI Agent 引擎

| 指标 | 数值 |
|------|------|
| 核心技能 | 9 |
| 集成工具 | 49 |
| 核心模块 | 13 |

支持 ReAct 自主决策 · 多 LLM 后端 · 闭环自愈

---

## 第4页：解决什么问题

# 解决什么问题

- ❌ AI Agent 缺乏结构化的任务规划能力
- ❌ 技能系统分散，难以统一管理
- ❌ 错误处理和自愈能力缺失
- ❌ 工具调用缺乏标准化

**Plector = 结构化决策 + 技能治理 + 闭环自愈**

---

## 第5页：目标用户

# 目标用户

### 🤖 开发者
构建 AI 应用的工程师

### 🏢 企业
需要自动化流程的组织

### 🔬 研究者
AI Agent 研究人员

### 🚀 创业者
快速构建 AI 原型

---

## 第6页：整体架构

# 整体架构

```
plector/
├── core/                       # 核心引擎（不依赖 skills/tools）
│   ├── agent_loop.py          # ReAct 循环
│   ├── event_bus.py           # 事件总线
│   ├── skill_registry.py      # 技能注册
│   ├── skill_handler.py       # 技能执行器
│   ├── closure_engine.py      # 闭环引擎
│   ├── context_builder.py     # 上下文构建
│   └── llm_client.py         # LLM 客户端
├── skills/                     # 核心技能（≤15个）
├── tools/                      # 工具函数
├── channels/                   # 接入渠道
└── config/                     # 配置文件
```

核心模块独立，技能和工具可插拔

---

## 第7页：核心模块

# 核心模块

| 模块 | 说明 |
|------|------|
| **Agent Loop** | ReAct 自主决策循环 |
| **Event Bus** | CloudEvents 1.0 事件总线 |
| **Skill Registry** | 插件化技能管理系统 |
| **Closure Engine** | 条件图执行与自愈 |
| **Context Builder** | 动态上下文构建 |
| **MCP Client** | MCP 协议集成 |

---

## 第8页：Agent Loop

# 核心功能：Agent Loop

## ReAct 自主决策循环

🤔 **思考** → 🔧 **执行** → 👁️ **观察** → 🔄 **迭代**

**Think → Act → Observe → Iterate**

### 特点
- 结构化任务规划
- 工具调用标准化
- 结果反馈闭环

---

## 第9页：Event Bus

# 核心功能：Event Bus

## 事件驱动的异步解耦

```json
{
  "specversion": "1.0",
  "type": "skill.completed",
  "source": "/skills/code_writer",
  "id": "evt-123",
  "data": {
    "skill": "code_writer",
    "result": "success"
  }
}
```

**特点**: 发布/订阅 | 异步通信 | 松耦合 | 可扩展

---

## 第10页：Skill Registry

# 核心功能：Skill Registry

## 插件化技能系统

| 指标 | 数值 |
|------|------|
| 核心技能 | 9 |
| 技能上限 | ≤15 |
| 标准化格式 | MCP |

```
skills/
├── memory/              # 记忆管理
├── code_writer/         # 代码编写
├── web_search/          # 网页搜索
├── file_utils/          # 文件操作
├── test_runner/         # 测试运行
└── ...
```

---

## 第11页：Closure Engine

# 核心功能：Closure Engine

## 条件图执行与闭环自愈

```yaml
loops:
  - name: "error_recovery"
    trigger: "skill.failed"
    conditions:
      - skill: "memory_save"
        max_retries: 3
        fallback: "skip_and_log"
    
    - name: "data_validation"
      trigger: "data.invalid"
      conditions:
        - action: "retry"
          attempts: 2
        - action: "alert"
```

**流程**: 错误检测 → 条件判断 → 自动修复 → 状态回滚

---

## 第12页：MCP 协议

# 核心功能：MCP 协议

## 连接外部 MCP Server

```
┌─────────────┐       MCP Protocol       ┌─────────────────┐
│   Plector   │  ←──────────────────→   │  External MCP   │
│  MCP Client │                         │     Server      │
└─────────────┘                         └─────────────────┘
```

**优势**: 引入现成工具 | 协议标准化 | 生态扩展

---

## 第13页：技术栈

# 技术栈

### 核心技术
- Python 3.10+
- asyncio
- CloudEvents
- MCP Protocol
- Pydantic

### LLM 支持
- OpenAI API
- Anthropic API
- Ollama

### 其他
- pytest
- FastAPI
- WebSocket

**核心代码量控制在 5000 行以内**

---

## 第14页：性能指标

# 性能指标

| 指标 | 数值 |
|------|------|
| 单元测试覆盖率 | 80%+ |
| 核心代码行数 | <5000 |
| 测试通过率 | 77/77 |

**Harness**: 7 项自动化检查，约柬代码质量

---

## 第15页：应用场景

# 应用场景

### 🤖 智能助手
构建企业级 AI 助手

### 🔄 流程自动化
复杂业务流程自动化

### 🛠️ 开发者工具
代码生成与审查

### 📊 数据处理
多源数据整合分析

---

## 第16页：快速开始

# 快速开始

```bash
# 克隆项目
git clone https://github.com/biandeshen/Plector.git
cd Plector

# 安装依赖
pip install -r requirements.txt

# 配置 LLM
export OPENAI_API_KEY="sk-xxx"

# 运行 CLI
python channels/cli.py --query "你好"

# 或运行 Web 服务
python channels/websocket.py --port 8080
```

---

## 第17页：未来规划

# 未来规划

- → Phase 3: 角色委派系统
- → 多 Agent 协作机制
- → 可视化流程编排
- → 云端部署支持
- → 更多 LLM 后端适配

---

## 第18页：总结

# 总结

### 核心价值

**事件驱动** + **技能治理** + **闭环自愈**

### Plector = 让 AI Agent 更可控、更可靠

---

## 第19页：Q&A

# Q&A

感谢聆听

**GitHub**: github.com/biandeshen/Plector

**欢迎 Star & Fork**

---

## 第20页：结束页

# 谢谢

**Plector v1.8.0**

- 事件驱动
- 技能治理
- 闭环自愈

---

## 演讲备注

### 第1页（封面）
- 停留 5 秒，让观众适应

### 第3页（什么是 Plector）
- 强调"事件驱动"这个核心概念
- 展示关键数据

### 第8页（Agent Loop）
- 这是 Plector 的核心创新点
- 可以举例说明实际工作流程

### 第11页（Closure Engine）
- 重点强调"自愈"能力
- 这是与其他框架的差异化优势

### 第16页（快速开始）
- 可以现场演示一个小例子

### 第19页（Q&A）
- 预留 10-15 分钟问答时间
