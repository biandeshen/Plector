"""
技能沙箱管理器 - Plector v2.0 Phase 1
提供技能执行的隔离环境，支持超时、资源限制和权限控制
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class SandboxMode(Enum):
    """沙箱模式"""

    RESTRICTED = "restricted"  # 严格模式：限制文件/网络访问
    STANDARD = "standard"  # 标准模式：允许基础操作
    UNRESTRICTED = "unrestricted"  # 无限制（仅用于可信技能）


@dataclass
class SandboxConfig:
    """沙箱配置"""

    mode: SandboxMode = SandboxMode.RESTRICTED
    timeout_seconds: int = 30
    max_memory_mb: int = 256
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=lambda: ["/etc", "/root", "/home"])
    max_iterations: int = 1000
    enable_network: bool = False


@dataclass
class ExecutionResult:
    """执行结果"""

    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: float = 0
    iterations: int = 0
    memory_mb: float = 0
    stats: dict = field(default_factory=dict)


class SkillSandbox:
    """
    技能沙箱管理器

    功能：
    1. 技能执行隔离
    2. 超时和资源限制
    3. 权限控制
    4. 执行统计
    """

    def __init__(self, config: SandboxConfig | None = None):
        self._config = config or SandboxConfig()
        self._execution_count = 0
        self._total_duration = 0.0
        self._active_executions: dict[str, asyncio.Task] = {}

    def validate_skill(self, skill_name: str, skill_code: str) -> dict:
        """
        验证技能代码安全性

        Args:
            skill_name: 技能名称
            skill_code: 技能代码

        Returns:
            {"success": bool, "data": {"hash": str, "warnings": list}, "error": str|None}
        """
        warnings = []

        dangerous_patterns = [
            (r"import\s+os\s*;.*os\.system", "潜在代码执行"),
            (r"import\s+subprocess", "潜在子进程执行"),
            (r"eval\s*\(", "潜在代码注入: eval"),
            (r"exec\s*\(", "潜在代码注入: exec"),
            (r"__import__\s*\(", "潜在动态导入"),
            (r"open\s*\([^)]*[\"']w[\"']", "潜在文件写入"),
            (r"rm\s+-rf", "危险系统命令"),
        ]

        for pattern, reason in dangerous_patterns:
            import re

            if re.search(pattern, skill_code, re.IGNORECASE):
                warnings.append(f"检测到 {reason}")

        code_hash = hashlib.sha256(skill_code.encode()).hexdigest()[:16]

        return {"success": True, "data": {"hash": code_hash, "warnings": warnings}, "error": None}

    async def _run_async_with_timeout(self, func: Callable, args: tuple, kwargs: dict, execution_id: str):
        """运行异步函数并处理超时"""
        task = asyncio.create_task(func(*args, **kwargs))
        self._active_executions[execution_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=self._config.timeout_seconds)
            return result, None
        except asyncio.TimeoutError:
            task.cancel()
            return None, f"执行超时 ({self._config.timeout_seconds}s)"

    async def _run_sync_in_executor(self, func: Callable, args: tuple, kwargs: dict):
        """在 executor 中运行同步函数"""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, func, *args, **kwargs)
        return result

    def _prepare_execution(self, skill_name: str, execution_id: str | None = None) -> tuple:
        """准备执行，返回 (execution_id, start_time)"""
        execution_id = execution_id or f"{skill_name}-{int(time.time() * 1000)}"
        start_time = time.time()
        self._execution_count += 1
        return execution_id, start_time

    def _build_success_result(self, result, duration_ms: float, iterations: int) -> ExecutionResult:
        """构建成功结果"""
        self._total_duration += duration_ms
        return ExecutionResult(
            success=True, data=result, duration_ms=duration_ms, iterations=iterations, stats=self.get_stats()
        )

    def _build_error_result(self, error: str, duration_ms: float) -> ExecutionResult:
        """构建错误结果"""
        return ExecutionResult(success=False, error=error, duration_ms=duration_ms)

    async def execute(
        self, skill_name: str, func: Callable, *args, execution_id: str | None = None, **kwargs
    ) -> ExecutionResult:
        """
        在沙箱中执行技能

        Args:
            skill_name: 技能名称
            func: 要执行的函数
            *args: 位置参数
            execution_id: 执行ID（可选）
            **kwargs: 关键字参数

        Returns:
            ExecutionResult
        """
        execution_id, start_time = self._prepare_execution(skill_name, execution_id)

        try:
            if asyncio.iscoroutinefunction(func):
                result, error = await self._run_async_with_timeout(func, args, kwargs, execution_id)
            else:
                result = await self._run_sync_in_executor(func, args, kwargs)
                error = None

            duration_ms = (time.time() - start_time) * 1000

            if error:
                return self._build_error_result(error, duration_ms)

            return self._build_success_result(result, duration_ms, iterations=0)

        except Exception as e:
            logger.error(f"沙箱执行失败: {skill_name}, {e}")
            return self._build_error_result(str(e), (time.time() - start_time) * 1000)
        finally:
            self._active_executions.pop(execution_id, None)

    def cancel(self, execution_id: str) -> dict:
        """取消正在执行的技能"""
        task = self._active_executions.get(execution_id)
        if task and not task.done():
            task.cancel()
            return {"success": True, "data": {"execution_id": execution_id}, "error": None}
        return {"success": False, "data": None, "error": "执行不存在或已完成"}

    def get_stats(self) -> dict:
        """获取沙箱统计信息"""
        return {
            "total_executions": self._execution_count,
            "total_duration_ms": round(self._total_duration, 2),
            "avg_duration_ms": round(self._total_duration / self._execution_count, 2) if self._execution_count else 0,
            "active_executions": len(self._active_executions),
            "config": {
                "mode": self._config.mode.value,
                "timeout_seconds": self._config.timeout_seconds,
                "max_memory_mb": self._config.max_memory_mb,
            },
        }

    def set_config(self, **kwargs) -> dict:
        """更新沙箱配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        return {"success": True, "data": self._config.__dict__, "error": None}


class SkillSandboxFactory:
    """沙箱工厂"""

    _sandboxes: ClassVar[dict[str, SkillSandbox]] = {}

    @classmethod
    def get_sandbox(cls, name: str = "default", config: SandboxConfig | None = None) -> "SkillSandbox":
        """获取或创建沙箱实例"""
        if name not in cls._sandboxes:
            cls._sandboxes[name] = SkillSandbox(config)
        return cls._sandboxes[name]

    @classmethod
    def create_restricted(cls, name: str) -> "SkillSandbox":
        """创建严格模式沙箱"""
        return cls.get_sandbox(name, SandboxConfig(mode=SandboxMode.RESTRICTED))

    @classmethod
    def create_standard(cls, name: str) -> "SkillSandbox":
        """创建标准模式沙箱"""
        return cls.get_sandbox(name, SandboxConfig(mode=SandboxMode.STANDARD))

    @classmethod
    def create_trusted(cls, name: str) -> "SkillSandbox":
        """创建可信沙箱（无限制）"""
        return cls.get_sandbox(name, SandboxConfig(mode=SandboxMode.UNRESTRICTED))

    @classmethod
    def list_sandboxes(cls) -> dict:
        """列出所有沙箱"""
        return {"success": True, "data": {name: sb.get_stats() for name, sb in cls._sandboxes.items()}, "error": None}


# 便捷函数
def get_sandbox(name: str = "default", config: SandboxConfig | None = None) -> SkillSandbox:
    """获取沙箱实例"""
    return SkillSandboxFactory.get_sandbox(name, config)


def get_default_sandbox_config() -> SandboxConfig:
    """获取默认沙箱配置"""
    return SandboxConfig()
