"""
LLM 客户端基类
===============
定义统一接口和公共方法
"""

import os
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from .metrics import get_metrics_collector


class LLMClientBase(ABC):
    """LLM 客户端基类"""

    def __init__(self, config: dict):
        self.provider = config.get("provider", "unknown")
        self.model = config.get("model", "default")
        self.provider_config = config.get(self.provider, {})
        self._clients: dict[str, Any] = {}

    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """发送聊天请求"""

    @abstractmethod
    async def stream_chat(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[dict]:
        """流式聊天"""

    def _get_env(self, value: str | None) -> str:
        """支持 ${ENV_VAR} 格式的环境变量引用"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            return os.environ.get(value[2:-1], "")
        return value or ""

    def _split_system(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """分离 system 消息"""
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        return "\n\n".join(system_parts) if system_parts else "", user_messages

    def _record_metrics(self, messages: list[dict], duration: float):
        """记录指标"""
        metrics = get_metrics_collector()
        metrics.inc_llm_request()
        metrics.record_llm_latency(duration)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_tokens = int(total_chars / 4)
        if estimated_tokens > 0:
            metrics.inc_tokens(estimated_tokens)

    @staticmethod
    def _strip_thinking(text: str) -> tuple[str, str]:
        """过滤思考内容，返回 (过滤文本, 思考内容)"""
        thinking_parts = []

        # 格式1: ﹏﹟...﹟﹏
        think_blocks = re.findall(r"﹏﹟([\s\S]*?)﹟﹏", text)
        for block in think_blocks:
            if block.strip():
                thinking_parts.append(block.strip())

        # 格式2: 【思考】...【/思考】或<think>...</think>
        thinking_blocks = re.findall(
            r"(?:【思考】|<thinking>|<think>)(.*?)(?:【/思考】|</thinking>|</think>)",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for block in thinking_blocks:
            if block.strip():
                thinking_parts.append(block.strip())

        # 格式3: 不完整的思考块
        incomplete_blocks = re.findall(r"﹏﹟[^\n]*", text, flags=re.MULTILINE)
        for block in incomplete_blocks:
            content = block.replace("﹏﹟", "").strip()
            if content:
                thinking_parts.append(content)

        # 格式4: 不完整的 <think> 开标签
        incomplete_think = re.findall(r"<think>([\s\S]*)$", text, flags=re.IGNORECASE)
        for block in incomplete_think:
            if block.strip():
                thinking_parts.append(block.strip())

        # 构建过滤后的文本（移除思考内容）
        filtered_text = text
        for pattern, block in think_blocks:
            filtered_text = filtered_text.replace(pattern, "")
        for pattern in thinking_blocks:
            filtered_text = filtered_text.replace(pattern, "")
        for block in incomplete_blocks:
            filtered_text = filtered_text.replace(block, "")

        return filtered_text.strip(), "\n".join(thinking_parts)
