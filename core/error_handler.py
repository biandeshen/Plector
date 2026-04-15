"""
统一错误处理层 - Plector v2.0 Phase 1
集中管理所有技能和核心模块的错误处理
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ErrorLevel(Enum):
    """错误级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类"""
    VALIDATION = "validation"           # 参数验证失败
    PERMISSION = "permission"           # 权限不足
    NOT_FOUND = "not_found"             # 资源不存在
    TIMEOUT = "timeout"                 # 操作超时
    NETWORK = "network"                 # 网络错误
    STORAGE = "storage"                 # 存储错误
    SKILL = "skill"                     # 技能执行错误
    SYSTEM = "system"                  # 系统内部错误
    UNKNOWN = "unknown"                 # 未知错误


@dataclass
class ErrorInfo:
    """错误信息结构"""
    code: str                           # 错误码: ERR_{CATEGORY}_{NUM}
    message: str                         # 用户可读的错误消息
    category: ErrorCategory             # 错误分类
    level: ErrorLevel                   # 错误级别
    detail: Optional[str] = None        # 详细错误信息
    cause: Optional[Exception] = None   # 原始异常
    context: dict = field(default_factory=dict)  # 额外上下文
    traceback: Optional[str] = None      # 堆栈跟踪

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "category": self.category.value,
                "level": self.level.value,
                "detail": self.detail,
                "context": self.context,
            }
        }


class PlectorError(Exception):
    """Plector 统一异常基类"""

    _code_prefix: str = "ERR"
    _category: ErrorCategory = ErrorCategory.UNKNOWN

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        detail: Optional[str] = None,
        cause: Optional[Exception] = None,
        **context
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self._generate_code()
        self.detail = detail
        self.cause = cause
        self.context = context
        self.traceback_str = traceback.format_exc() if cause else None

    def _generate_code(self) -> str:
        """生成错误码"""
        return f"{self._code_prefix}_{self._category.value.upper()}_001"

    def to_info(self, level: ErrorLevel = ErrorLevel.ERROR) -> ErrorInfo:
        """转换为 ErrorInfo"""
        return ErrorInfo(
            code=self.code,
            message=self.message,
            category=self._category,
            level=level,
            detail=self.detail,
            cause=self.cause,
            context=self.context,
            traceback=self.traceback_str
        )


# 具体的错误类型
class ValidationError(PlectorError):
    """参数验证失败"""
    _category = ErrorCategory.VALIDATION
    _code_prefix = "VAL"


class PermissionError(PlectorError):
    """权限不足"""
    _category = ErrorCategory.PERMISSION
    _code_prefix = "PER"


class NotFoundError(PlectorError):
    """资源不存在"""
    _category = ErrorCategory.NOT_FOUND
    _code_prefix = "NF"


class TimeoutError(PlectorError):
    """操作超时"""
    _category = ErrorCategory.TIMEOUT
    _code_prefix = "TMO"


class NetworkError(PlectorError):
    """网络错误"""
    _category = ErrorCategory.NETWORK
    _code_prefix = "NET"


class StorageError(PlectorError):
    """存储错误"""
    _category = ErrorCategory.STORAGE
    _code_prefix = "STO"


class SkillError(PlectorError):
    """技能执行错误"""
    _category = ErrorCategory.SKILL
    _code_prefix = "SKL"


class SystemError(PlectorError):
    """系统内部错误"""
    _category = ErrorCategory.SYSTEM
    _code_prefix = "SYS"


class ErrorHandler:
    """
    统一错误处理器
    
    功能：
    1. 集中捕获和处理所有异常
    2. 统一错误格式输出
    3. 错误分类和日志记录
    4. 错误恢复建议
    """

    def __init__(self):
        self._error_count: dict[ErrorCategory, int] = {}
        self._handlers: dict[ErrorCategory, list] = {}

    def register_handler(
        self,
        category: ErrorCategory,
        handler: callable
    ):
        """注册错误类别处理器"""
        if category not in self._handlers:
            self._handlers[category] = []
        self._handlers[category].append(handler)

    def handle(
        self,
        error: Exception,
        context: Optional[dict] = None,
        level: Optional[ErrorLevel] = None
    ) -> ErrorInfo:
        """
        处理异常并返回结构化错误信息
        
        Args:
            error: 捕获的异常
            context: 额外的上下文信息
            level: 错误级别（可选，自动推断）
            
        Returns:
            ErrorInfo: 结构化的错误信息
        """
        # 确定错误类型
        if isinstance(error, PlectorError):
            info = error.to_info()
            if context:
                info.context.update(context)
        else:
            # 未知异常，尝试分类
            info = self._classify_unknown_error(error, context)

        # 更新统计
        self._update_stats(info.category)

        # 记录日志
        self._log_error(info)

        # 触发注册的处理器
        self._dispatch_handlers(info)

        return info

    async def handle_async(
        self,
        coro,
        context: Optional[dict] = None
    ) -> Any:
        """
        异步执行并捕获异常
        
        Args:
            coro: 协程对象
            context: 额外的上下文信息
            
        Returns:
            成功时返回协程结果，失败时返回错误信息字典
        """
        try:
            return await coro
        except Exception as e:
            info = self.handle(e, context)
            return info.to_dict()

    def _classify_unknown_error(
        self,
        error: Exception,
        context: Optional[dict]
    ) -> ErrorInfo:
        """分类未知错误"""
        error_msg = str(error).lower()
        
        # 根据错误消息推断类别
        if "timeout" in error_msg or "timed out" in error_msg:
            category = ErrorCategory.TIMEOUT
        elif "permission" in error_msg or "denied" in error_msg:
            category = ErrorCategory.PERMISSION
        elif "not found" in error_msg or "does not exist" in error_msg:
            category = ErrorCategory.NOT_FOUND
        elif "network" in error_msg or "connection" in error_msg:
            category = ErrorCategory.NETWORK
        elif "storage" in error_msg or "disk" in error_msg or "io" in error_msg:
            category = ErrorCategory.STORAGE
        else:
            category = ErrorCategory.UNKNOWN

        return ErrorInfo(
            code=f"ERR_{category.value.upper()}_000",
            message=str(error),
            category=category,
            level=ErrorLevel.ERROR,
            cause=error,
            context=context or {},
            traceback=traceback.format_exc()
        )

    def _update_stats(self, category: ErrorCategory):
        """更新错误统计"""
        self._error_count[category] = self._error_count.get(category, 0) + 1

    def _log_error(self, info: ErrorInfo):
        """记录错误日志"""
        log_data = {
            "code": info.code,
            "message": info.message,
            "category": info.category.value,
            "context": info.context
        }
        
        if info.level == ErrorLevel.CRITICAL:
            logger.critical(log_data, exc_info=info.cause)
        elif info.level == ErrorLevel.ERROR:
            logger.error(log_data, exc_info=info.cause)
        elif info.level == ErrorLevel.WARNING:
            logger.warning(log_data)
        else:
            logger.info(log_data)

    def _dispatch_handlers(self, info: ErrorInfo):
        """分发错误到注册的处理器"""
        handlers = self._handlers.get(info.category, [])
        for handler in handlers:
            try:
                handler(info)
            except Exception as e:
                logger.error(f"错误处理器执行失败: {e}")

    def get_stats(self) -> dict:
        """获取错误统计"""
        return dict(self._error_count)

    def get_recovery_suggestion(self, info: ErrorInfo) -> str:
        """根据错误类型返回恢复建议"""
        suggestions = {
            ErrorCategory.VALIDATION: "请检查输入参数是否正确",
            ErrorCategory.PERMISSION: "请检查权限配置或联系管理员",
            ErrorCategory.NOT_FOUND: "请确认资源是否存在",
            ErrorCategory.TIMEOUT: "请稍后重试或增加超时时间",
            ErrorCategory.NETWORK: "请检查网络连接",
            ErrorCategory.STORAGE: "请检查磁盘空间或存储配置",
            ErrorCategory.SKILL: "请检查技能配置或查看详细日志",
            ErrorCategory.SYSTEM: "请联系技术支持",
            ErrorCategory.UNKNOWN: "请联系技术支持并提供错误日志",
        }
        return suggestions.get(info.category, "请稍后重试")


# 全局实例
_instance: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局 ErrorHandler 实例"""
    global _instance
    if _instance is None:
        _instance = ErrorHandler()
    return _instance


def handle_error(
    error: Exception,
    context: Optional[dict] = None
) -> ErrorInfo:
    """快捷函数：处理异常"""
    return get_error_handler().handle(error, context)


async def safe_execute(
    coro,
    context: Optional[dict] = None
) -> Any:
    """快捷函数：安全执行异步操作"""
    return await get_error_handler().handle_async(coro, context)
