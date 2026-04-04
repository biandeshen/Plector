"""配置加载模块，支持环境变量替换"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def get_config_path() -> Path:
    """获取配置文件路径"""
    config_paths = [
        Path("config/config.yaml"),
        Path("config/config.local.yaml"),  # 本地覆盖配置（优先级高）
    ]
    for path in config_paths:
        if path.exists():
            return path
    return config_paths[0]


def load_config(config_path: Path = None) -> dict:
    """加载 YAML 配置，支持环境变量替换"""
    config_path = config_path or get_config_path()
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return _replace_env_vars(config)


def _replace_env_vars(data):
    """递归替换配置中的环境变量引用
    支持两种语法：
    - ${VAR}         如果变量不存在，返回原字符串
    - ${VAR:-default}  如果变量不存在，使用默认值
    """
    if isinstance(data, dict):
        return {k: _replace_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_env_vars(item) for item in data]
    elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_spec = data[2:-1]  # 去掉 ${ 和 }
        if ":-" in env_spec:
            # ${VAR:-default} 语法
            env_name, default_value = env_spec.split(":-", 1)
            return os.environ.get(env_name, default_value)
        else:
            # ${VAR} 语法
            return os.environ.get(env_spec, data)
    else:
        return data
