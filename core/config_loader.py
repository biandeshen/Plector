#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 统一处理配置文件中的环境变量替换

功能：
    1. 加载 .env 文件
    2. 加载 config.yaml
    3. 自动替换 ${VAR_NAME} 引用为真实值
    4. 检测硬编码密钥并警告

使用方式：
    from core.config_loader import load_config
    config = load_config()

Author: Plector
Version: 1.0.0
Created: 2026-04-05
"""

import os
import re
import logging
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 已知的敏感字段关键词
SENSITIVE_KEYWORDS = [
    "api_key", "apikey", "api-key",
    "secret", "password", "passwd", "pwd",
    "token", "access_token", "refresh_token",
    "private_key", "credential",
]


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    加载配置文件，自动替换环境变量引用

    参数：
        config_path: 配置文件路径

    返回：
        配置字典（环境变量已替换）

    示例：
        config.yaml:
            mcp_servers:
              minimax:
                env:
                  MINIMAX_API_KEY: "${MINIMAX_API_KEY}"

        .env:
            MINIMAX_API_KEY=sk-xxx

        使用：
            config = load_config()
            api_key = config["mcp_servers"]["minimax"]["env"]["MINIMAX_API_KEY"]
            # 结果: "sk-xxx"（不是 "${MINIMAX_API_KEY}"）
    """
    # 加载 .env
    load_dotenv()

    # 加载 config.yaml
    config_file = Path(config_path)
    if not config_file.exists():
        logger.error(f"配置文件不存在: {config_path}")
        return {}

    with open(config_file, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    # 递归替换环境变量
    resolved_config = _resolve_env_vars(raw_config)

    # 检测硬编码密钥
    _check_hardcoded_secrets(raw_config, config_path)

    return resolved_config


def _resolve_env_vars(obj: Any) -> Any:
    """递归替换配置中的环境变量引用"""
    if isinstance(obj, str):
        # 匹配 ${VAR_NAME} 格式
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            var_name = match.group(1)
            value = os.environ.get(var_name, "")
            if not value:
                logger.warning(f"环境变量未设置: {var_name}")
            return value

        return re.sub(pattern, replacer, obj)

    elif isinstance(obj, dict):
        return {key: _resolve_env_vars(value) for key, value in obj.items()}

    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]

    else:
        return obj


def _check_hardcoded_secrets(obj: Any, path: str = "", config_path: str = ""):
    """检测配置中的硬编码密钥"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # 检查是否是敏感字段
            is_sensitive = any(
                keyword in key.lower() for keyword in SENSITIVE_KEYWORDS
            )

            if is_sensitive and isinstance(value, str):
                # 如果是敏感字段但不是环境变量引用
                if not (value.startswith("${") and value.endswith("}")):
                    # 排除空值和示例值
                    if value and not value.startswith("your_") and value != "":
                        logger.warning(
                            f"⚠️  检测到硬编码密钥: {config_path} -> {current_path}\n"
                            f"   建议改为: {key}: \"${{{key.upper()}}}\"\n"
                            f"   并在 .env 中添加: {key.upper()}=你的真实密钥"
                        )

            _check_hardcoded_secrets(value, current_path, config_path)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_hardcoded_secrets(item, f"{path}[{i}]", config_path)


def get_env(key: str, default: str = "") -> str:
    """获取环境变量（快捷方式）"""
    load_dotenv()
    return os.environ.get(key, default)
