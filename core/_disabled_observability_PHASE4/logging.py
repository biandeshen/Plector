"""结构化日志系统"""
import json
import time
import sys
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogRecord:
    """日志记录"""
    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    name: str = "plector"
    module: str = ""
    function: str = ""
    line: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.name,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "message": self.message,
            **self.extra
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class Logger:
    """结构化日志记录器"""

    def __init__(self, name: str = "plector", level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.handlers = [ConsoleHandler()]

    def _log(self, level: LogLevel, message: str, **kwargs):
        if level.value < self.level.value:
            return
        record = LogRecord(
            level=level.name,
            message=message,
            name=self.name,
            extra=kwargs
        )
        for handler in self.handlers:
            handler.emit(record)

    def debug(self, message: str, **kwargs):
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)


class ConsoleHandler:
    """控制台处理器"""

    def emit(self, record: LogRecord):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.timestamp))
        color = _LEVEL_COLORS.get(record.level, "")
        reset = "\033[0m" if color else ""
        print(f"{color}[{timestamp}] {record.level:<8} {reset}{record.message}")
        if record.extra:
            print(f"{' ' * 30}{json.dumps(record.extra, default=str)}")


_LEVEL_COLORS = {
    "DEBUG": "\033[36m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[35m",
}


_loggers: Dict[str, Logger] = {}


def get_logger(name: str = "plector", level: LogLevel = LogLevel.INFO) -> Logger:
    """获取日志记录器"""
    if name not in _loggers:
        _loggers[name] = Logger(name, level)
    return _loggers[name]
