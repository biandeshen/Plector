"""
LLM 客户端 - MiniMax 实现（OpenAI 兼容）
"""

from copy import deepcopy

from .llm_client_openai import OpenAIClient


class MiniMaxClient(OpenAIClient):
    """MiniMax LLM 客户端（继承 OpenAI 兼容实现）"""

    def __init__(self, config: dict):
        # MiniMax 使用不同的 provider key
        minimax_config = deepcopy(config)
        minimax_config["provider"] = "minimax"
        if "minimax" not in minimax_config:
            minimax_config["minimax"] = config.get("minimax", {})
        # 设置 base_url
        if "base_url" not in minimax_config.get("minimax", {}):
            minimax_config["minimax"]["base_url"] = "https://api.minimax.chat/v1"
        super().__init__(minimax_config, provider="minimax")
