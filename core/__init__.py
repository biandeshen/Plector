"""
Plector Core Module
"""

# 导出主要组件 - 使用相对导入
from .error_handler import (
    ErrorHandler,
    ErrorInfo,
    NetworkError,
    NotFoundError,
    PlectorError,
    SkillError,
    SystemError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
)
from .event_bus_v2 import EventBus, EventBusV2, get_event_bus, get_event_bus_v2
from .function_calling import ToolRegistry
from .llm_client_v2 import LLMClientV2
from .mcp_client import MCPServer
from .skill_registry import SkillRegistry
from .skill_sandbox import SkillSandbox, get_default_sandbox_config, get_sandbox

# 尝试导入 SecretsManager（可选依赖）
try:
    from .security.secrets_manager import SecretEntry, SecretScope, SecretsManager

    _has_secrets = True
except ImportError:
    _has_secrets = False
    SecretsManager = None
    SecretScope = None
    SecretEntry = None

# TODO: Phase 3-5 特性（当前禁用以保持简洁）
# from .config_manager import ConfigManager  # 配置中心
# from .plugin_system import PluginRegistry, PluginInfo, PluginHook  # 插件系统
# from .role_switcher import RoleSwitcher, Role, RoleType, RoleContext  # 角色切换器（使用 agency_orchestrator 替代）
# from .telemetry import TelemetryCollector, Metric, MetricType, TimerContext  # 遥测
# from .docs_generator import DocGenerator, DocEntry, GeneratedDoc  # 文档生成
# from .cli import ...  # CLI 命令系统
# from .compat import ...  # v1 适配器
# from .interfaces import ...  # 接口抽象层
# from .observability import ...  # 可观测性
# from .performance import ...  # 性能监控
# from .protocols import ...  # 协议定义

__all__ = [
    "ErrorHandler",
    "ErrorInfo",
    "EventBus",
    "EventBusV2",
    "LLMClientV2",
    "MCPServer",
    "NetworkError",
    "NotFoundError",
    "PlectorError",
    "SecretEntry",
    "SecretScope",
    "SecretsManager",
    "SkillError",
    "SkillRegistry",
    "SkillSandbox",
    "SystemError",
    "TimeoutError",
    "ToolRegistry",
    "ValidationError",
    "get_default_sandbox_config",
    "get_error_handler",
    "get_event_bus",
    "get_event_bus_v2",
    "get_sandbox",
    "handle_error",
]
