"""
Plector Core Module
"""

# 导出主要组件 - 使用相对导入
from .event_bus import EventBus, get_event_bus
from .error_handler import (
    ErrorHandler,
    ErrorInfo,
    PlectorError,
    ValidationError,
    NotFoundError,
    TimeoutError,
    NetworkError,
    SkillError,
    SystemError,
    get_error_handler,
    handle_error,
)
from .event_bus_v2 import EventBusV2, get_event_bus_v2
from .skill_sandbox import SkillSandbox, get_sandbox, get_default_sandbox_config
from .skill_registry import SkillRegistry
from .function_calling import ToolRegistry
from .mcp_client import MCPServer
from .llm_client_v2 import LLMClientV2, get_llm_client_v2

# 尝试导入 SecretsManager（可选依赖）
try:
    from .security.secrets_manager import SecretsManager, SecretScope, SecretEntry
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

__all__ = [
    # Event Bus
    "EventBus",
    "get_event_bus",
    "EventBusV2",
    "get_event_bus_v2",
    # Error Handling
    "ErrorHandler",
    "ErrorInfo",
    "PlectorError",
    "ValidationError",
    "NotFoundError",
    "TimeoutError",
    "NetworkError",
    "SkillError",
    "SystemError",
    "get_error_handler",
    "handle_error",
    # Sandbox
    "SkillSandbox",
    "get_sandbox",
    "get_default_sandbox_config",
    # Skill Registry
    "SkillRegistry",
    # Function Calling
    "ToolRegistry",
    # MCP Client
    "MCPServer",
    # LLM Client V2
    "LLMClientV2",
    "get_llm_client_v2",
    # Secrets Manager (optional)
    "SecretsManager",
    "SecretScope",
    "SecretEntry",
]
