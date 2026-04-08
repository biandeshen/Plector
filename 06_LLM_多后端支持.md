---
tags: [Plector, 核心模块, 实现]
type: feature
created: 2026-04-08
---

# Plector LLM 多后端支持（Claude Code 可执行版）

> 本文档为增量更新，Plector 核心模块已全部完成。
> 本次更新：将 LLM 调用从硬编码 Ollama 改为可配置的多后端抽象层。
> 支持：Ollama / OpenAI / Anthropic，通过 config.yaml 切换。

---

## 第一步：创建 LLM 抽象层 `core/llm_client.py`

```python
import os
import json
import asyncio
from typing import List, Dict, Optional


class LLMClient:
    """LLM 客户端抽象层，支持多后端"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "qwen3:4b")
        self.provider_config = config.get(self.provider, {})

    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """发送聊天请求，返回统一格式：{"content": str, "tool_calls": list or None}"""
        if self.provider == "ollama":
            return await self._ollama_chat(messages, tools)
        elif self.provider == "openai":
            return await self._openai_chat(messages, tools)
        elif self.provider == "anthropic":
            return await self._anthropic_chat(messages, tools)
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    async def _ollama_chat(self, messages, tools):
        """Ollama 后端"""
        import ollama
        loop = asyncio.get_event_loop()
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await loop.run_in_executor(
            None, lambda: ollama.chat(**kwargs)
        )
        return {
            "content": response.get("message", {}).get("content", ""),
            "tool_calls": response.get("message", {}).get("tool_calls"),
        }

    async def _openai_chat(self, messages, tools):
        """OpenAI 后端"""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=self._get_env(self.provider_config.get("api_key")),
            base_url=self.provider_config.get("base_url"),
        )
        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in msg.tool_calls
            ]
        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
        }

    async def _anthropic_chat(self, messages, tools):
        """Anthropic 后端"""
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=self._get_env(self.provider_config.get("api_key")),
        )
        # Anthropic 不支持 system 在 messages 里，需要单独传
        system = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        kwargs = {
            "model": self.provider_config.get("model", self.model),
            "max_tokens": 4096,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools_for_anthropic(tools)

        response = await client.messages.create(**kwargs)
        content = ""
        tool_calls = None
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if not tool_calls:
                    tool_calls = []
                tool_calls.append({
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    }
                })
        return {
            "content": content,
            "tool_calls": tool_calls,
        }

    def _convert_tools_for_anthropic(self, tools):
        """将 OpenAI 格式的 tools 转换为 Anthropic 格式"""
        converted = []
        for tool in tools:
            converted.append({
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            })
        return converted

    def _get_env(self, value):
        """支持环境变量引用，如 ${OPENAI_API_KEY}"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.environ.get(env_name, "")
        return value
```

### 验证

```bash
python -c "from core.llm_client import LLMClient; print('OK')"
```

### 提交

```bash
git add core/llm_client.py
git commit -m "feat(core): 添加 LLM 抽象层，支持 Ollama / OpenAI / Anthropic"
```

---

## 第二步：修改 `core/agent_loop.py`

替换整个文件：

```python
import asyncio
import json
from .skill_registry import SkillRegistry
from .skill_handler import SkillHandler
from .function_calling import ToolRegistry
from .event_bus import get_event_bus
from .closure_engine import ClosureEngine
from .context_builder import ContextBuilder
from .llm_client import LLMClient


class AgentLoop:
    """自主决策循环，实现 ReAct 模式"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.skill_registry = SkillRegistry()
        self.skill_registry.scan()
        self.skill_handler = SkillHandler(self.skill_registry)
        self.tool_registry = ToolRegistry()
        self.event_bus = get_event_bus()
        self.context_builder = ContextBuilder(self.skill_registry)
        self.closure_engine = ClosureEngine(self.skill_handler)
        self.max_iterations = self.config.get("max_iterations", 10)
        self.llm = LLMClient(self.config.get("llm", {}))
        self._register_skills_as_tools()

    def _register_skills_as_tools(self):
        """将每个技能注册为工具"""
        for skill_name, skill_info in self.skill_registry.skills.items():
            for method_name, method_info in skill_info["meta"].get("methods", {}).items():
                tool_name = f"{skill_name}.{method_name}"
                self.tool_registry.register(
                    name=tool_name,
                    description=method_info.get("description", ""),
                    parameters=method_info.get("params", {}),
                    handler=self._create_skill_handler(skill_name, method_name)
                )

    def _create_skill_handler(self, skill_name, method_name):
        async def handler(**kwargs):
            return await self.skill_handler.execute(skill_name, method_name, kwargs)
        return handler

    async def run(self, user_input: str, session_id: str = None) -> str:
        """执行 Agent 循环"""
        system_prompt = self.context_builder.build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        for _ in range(self.max_iterations):
            response = await self.llm.chat(
                messages=messages,
                tools=self.tool_registry.get_tool_schemas()
            )
            if not response.get("tool_calls"):
                return response["content"]

            for tool_call in response["tool_calls"]:
                result = await self.tool_registry.execute(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": json.dumps(result)
                })

        return "达到最大迭代次数"
```

### 验证

```bash
python -c "from core.agent_loop import AgentLoop; print('OK')"
```

### 提交

```bash
git add core/agent_loop.py
git commit -m "refactor(core): AgentLoop 改用 LLMClient 抽象层，移除硬编码 Ollama"
```

---

## 第三步：更新 `config/config.yaml`

```yaml
llm:
  # 当前后端：ollama / openai / anthropic
  provider: "ollama"
  max_iterations: 10

  # Ollama 配置（本地免费）
  ollama:
    base_url: "http://localhost:11434"
    model: "qwen3:4b"

  # OpenAI 配置（付费）
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o-mini"
    base_url: "https://api.openai.com/v1"

  # Anthropic 配置（付费）
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-sonnet-4-20250514"
```

### 验证

```bash
python -c "
import yaml
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)
print(f'provider: {config[\"llm\"][\"provider\"]}')
print(f'model: {config[\"llm\"][\"ollama\"][\"model\"]}')
"
```

### 提交

```bash
git add config/config.yaml
git commit -m "feat(config): config.yaml 支持多 LLM 后端配置"
```

---

## 第四步：更新 `requirements.txt`

```txt
psutil>=5.9.0
pyyaml>=6.0
pytest>=7.0
pytest-asyncio>=0.21
pre-commit>=3.0
ollama>=0.1.0
openai>=1.0.0
anthropic>=0.20.0
```

### 验证

```bash
pip install -r requirements.txt
```

### 提交

```bash
git add requirements.txt
git commit -m "chore: 添加 openai 和 anthropic 依赖"
```

---

## 第五步：端到端测试

### 5.1 Ollama 测试（默认）

```bash
# 确认 Ollama 在运行
ollama list

# 测试对话
python channels/cli.py --query "你好"

# 测试技能调用
python channels/cli.py --query "系统健康吗"
```

### 5.2 OpenAI 测试（可选）

```bash
export OPENAI_API_KEY="sk-xxx"

# 临时切换（不改文件）
python -c "
import asyncio
from core.agent_loop import AgentLoop

async def test():
    config = {
        'max_iterations': 10,
        'llm': {
            'provider': 'openai',
            'openai': {
                'api_key': '\${OPENAI_API_KEY}',
                'model': 'gpt-4o-mini',
                'base_url': 'https://api.openai.com/v1',
            }
        }
    }
    agent = AgentLoop(config)
    response = await agent.run('你好')
    print(response)

asyncio.run(test())
"
```

### 5.3 Anthropic 测试（可选）

```bash
export ANTHROPIC_API_KEY="sk-ant-xxx"

python -c "
import asyncio
from core.agent_loop import AgentLoop

async def test():
    config = {
        'max_iterations': 10,
        'llm': {
            'provider': 'anthropic',
            'anthropic': {
                'api_key': '\${ANTHROPIC_API_KEY}',
                'model': 'claude-sonnet-4-20250514',
            }
        }
    }
    agent = AgentLoop(config)
    response = await agent.run('你好')
    print(response)

asyncio.run(test())
"
```

### 5.4 单元测试

```bash
pytest tests/ -v
```

### 5.5 Pre-commit 检查

```bash
pre-commit run --all-files
```

### 最终提交

```bash
git add -A
git commit -m "feat: 支持多 LLM 后端（Ollama / OpenAI / Anthropic）"
git push
```

---

## 切换 LLM 的方式

### 方式 1：修改 config.yaml（永久切换）

```yaml
llm:
  provider: "openai"  # 改这里
```

### 方式 2：代码中传入 config（临时切换）

```python
config = {
    "llm": {
        "provider": "anthropic",
        "anthropic": {"api_key": "${ANTHROPIC_API_KEY}", "model": "claude-sonnet-4-20250514"}
    }
}
agent = AgentLoop(config)
```

### 方式 3：环境变量（CI/CD 场景）

```bash
export PLECTOR_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-xxx
python channels/cli.py --query "你好"
```

> 注意：方式 3 需要在 LLMClient 中额外读取环境变量，当前未实现，可后续添加。

---

## 改动文件清单

| 文件 | 操作 |
|------|------|
| `core/llm_client.py` | 新建 |
| `core/agent_loop.py` | 修改（移除硬编码 ollama） |
| `config/config.yaml` | 修改（多后端配置） |
| `requirements.txt` | 修改（添加 openai / anthropic） |

---

## 后续可扩展

```
当前：3 个后端（Ollama / OpenAI / Anthropic）
未来可加：
  ├─ Google Gemini
  ├─ Azure OpenAI
  ├─ 本地 vLLM
  └─ 自定义 API
```

**从第一步开始执行，每步验证通过后再继续。**
```

---

这份文件只包含 LLM 多后端的 5 步增量更新。交给 Claude Code 执行。