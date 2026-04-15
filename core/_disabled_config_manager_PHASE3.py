"""统一配置管理器

职责：集中管理所有配置，支持多环境、多源配置合并
遵循规则：函数不超过 50 行
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ConfigSource:
    """配置源"""
    name: str
    data: Dict[str, Any]
    priority: int = 0  # 数值越大优先级越高


class ConfigManager:
    """统一配置管理器
    
    支持多源配置合并：
    1. 默认配置 (内置)
    2. 配置文件 (yaml/toml/json)
    3. 环境变量
    4. 运行时覆盖
    """
    
    def __init__(self):
        self._sources: list[ConfigSource] = []
        self._cache: Dict[str, Any] = {}
        self._cache_valid = False
    
    # ========== 公开 API ==========
    
    def load_file(self, path: str | Path, priority: int = 10) -> None:
        """加载配置文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        data = self._load_file_content(path)
        self.add_source(path.name, data, priority)
    
    def load_env(self, prefix: str = "PLECTOR_", priority: int = 20) -> None:
        """从环境变量加载配置"""
        data = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                data[config_key] = self._parse_env_value(value)
        
        self.add_source("env", data, priority)
    
    def add_source(self, name: str, data: Dict[str, Any], priority: int = 0) -> None:
        """添加配置源"""
        source = ConfigSource(name=name, data=data, priority=priority)
        self._sources.append(source)
        self._invalidate_cache()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔，如 "database.host"
            default: 默认值
            
        Returns:
            配置值
        """
        if not self._cache_valid:
            self._rebuild_cache()
        
        return self._cache.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """运行时设置配置"""
        self.add_source("runtime", {key: value}, priority=100)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置区块"""
        prefix = section + "."
        result = {}
        
        if not self._cache_valid:
            self._rebuild_cache()
        
        for key, value in self._cache.items():
            if key.startswith(prefix):
                result[key[len(prefix):]] = value
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """导出完整配置"""
        if not self._cache_valid:
            self._rebuild_cache()
        return self._cache.copy()
    
    # ========== 内部方法 ==========
    
    def _load_file_content(self, path: Path) -> Dict[str, Any]:
        """加载文件内容"""
        suffix = path.suffix.lower()
        
        if suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        elif suffix in (".yaml", ".yml"):
            return self._load_yaml(path)
        elif suffix == ".toml":
            return self._load_toml(path)
        else:
            raise ValueError(f"不支持的配置文件格式: {suffix}")
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """加载 YAML 文件"""
        try:
            import yaml
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except ImportError:
            raise ImportError("需要安装 pyyaml: pip install pyyaml")
    
    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """加载 TOML 文件"""
        try:
            import tomli
            return tomli.loads(path.read_text(encoding="utf-8"))
        except ImportError:
            raise ImportError("需要安装 tomli: pip install tomli")
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为 JSON
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        elif value.lower() == "none":
            return None
        
        # 尝试数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    
    def _rebuild_cache(self) -> None:
        """重建配置缓存"""
        # 按优先级排序（从小到大）
        sorted_sources = sorted(self._sources, key=lambda s: s.priority)
        
        # 合并配置
        self._cache = {}
        for source in sorted_sources:
            self._deep_update(self._cache, source.data)
        
        self._cache_valid = True
    
    def _deep_update(self, target: dict, source: dict) -> None:
        """深度合并字典"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _invalidate_cache(self) -> None:
        """使缓存失效"""
        self._cache_valid = False


# ========== 全局单例 ==========

_global_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """获取全局配置管理器"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config


def init_config(config_path: Optional[str] = None) -> ConfigManager:
    """初始化全局配置"""
    global _global_config
    _global_config = ConfigManager()
    
    # 加载默认配置
    _global_config.add_source("default", _DEFAULT_CONFIG, priority=0)
    
    # 加载配置文件
    if config_path:
        _global_config.load_file(config_path)
    
    # 加载环境变量
    _global_config.load_env()
    
    return _global_config


# ========== 默认配置 ==========

_DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0.0",
    "log_level": "INFO",
    "skills_dir": "skills",
    "workflows_dir": "workflows",
    "data_dir": "data",
    "max_retries": 3,
    "timeout": 300,
    "llm": {
        "provider": "claude-code",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
    },
    "event_bus": {
        "max_queue_size": 1000,
        "batch_size": 10,
    },
    "memory": {
        "backend": "sqlite",
        "path": "data/memory.db",
    },
}
