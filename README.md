# Plector

自主决策 Agent 系统，支持多 LLM 后端（Ollama / OpenAI / Anthropic）。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写你的 API Key：

```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your_api_key_here
ANTHROPIC_API_KEY=sk-your_anthropic_key_here
```

**安全提示**：
- `.env` 文件已加入 `.gitignore`，不会被提交到 Git
- 请勿将 `.env` 文件分享给他人

### 3. 运行

```python
from core.agent_loop import AgentLoop

agent = AgentLoop()
result = await agent.run("帮我分析一下系统健康状态")
print(result)
```

## 配置说明

### LLM 后端选择

编辑 `config/config.yaml`：

```yaml
llm:
  provider: "openai"  # ollama / openai / anthropic
  max_iterations: 10
```

### 环境变量列表

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_PROVIDER` | LLM 后端选择 | `ollama` |
| `OPENAI_API_KEY` | OpenAI API Key | 无 |
| `ANTHROPIC_API_KEY` | Anthropic API Key | 无 |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama 模型 | `qwen3:4b` |

## 项目结构

```
plector/
├── core/          # 核心引擎
├── skills/        # 核心技能
├── tools/         # 工具函数
├── config/        # 配置文件
├── tests/         # 单元测试
└── docs/          # 文档
```

## 开发规范

详见 `CLAUDE.md` 和 `docs/standards/`。

## 验证命令

```bash
python -m py_compile core/agent_loop.py
python scripts/validate_skills.py
pytest tests/ -v
```
