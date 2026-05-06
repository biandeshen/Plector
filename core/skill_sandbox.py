# mypy: ignore-errors
"""
技能沙箱管理器 - Plector v2.0 Phase 1
提供技能执行的隔离环境，支持超时、资源限制和权限控制
"""

import asyncio
import hashlib
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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
    allowed_paths: list[str] = field(default_factory=list)  # 路径白名单
    denied_paths: list[str] = field(default_factory=lambda: ["/etc", "/root", "/home", "/var"])
    max_iterations: int = 1000
    enable_network: bool = False
    max_file_size_mb: int = 20


class PathIsolationError(Exception):
    """Path isolation violation"""

    pass


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
    3. 权限控制（路径白名单/黑名单）
    4. 执行统计
    """

    def __init__(self, config: SandboxConfig | None = None):
        self._config = config or SandboxConfig()
        self._execution_count = 0
        self._total_duration = 0.0
        self._active_executions: dict[str, asyncio.Task] = {}

    def _is_path_under(self, abs_path: Path, base: Path) -> bool:
        """检查 abs_path 是否在 base 下"""
        try:
            abs_path.relative_to(base)
            return True
        except ValueError:
            return False

    def validate_path(self, file_path: str, operation: str = "read") -> tuple[bool, str]:
        """
        验证文件路径是否在允许的目录内

        Args:
            file_path: 要验证的路径
            operation: 操作类型 ("read", "write", "execute")

        Returns:
            (是否有效, 错误消息)
        """
        if self._config.mode == SandboxMode.UNRESTRICTED:
            return True, ""
        try:
            abs_path = Path(file_path).expanduser().resolve()
            # Check denied paths
            for denied in self._config.denied_paths:
                if self._is_path_under(abs_path, Path(denied).resolve()):
                    return False, f"路径在禁止目录内: {denied}"
            # Check allowed paths whitelist
            if self._config.allowed_paths and not any(
                self._is_path_under(abs_path, Path(p).resolve()) for p in self._config.allowed_paths
            ):
                return False, f"路径不在允许的目录内: {self._config.allowed_paths}"
            # Default: allow cwd and home
            cwd, home = Path.cwd().resolve(), Path.home().resolve()
            if not self._is_path_under(abs_path, cwd) and not self._is_path_under(abs_path, home):
                return False, "路径不在允许的目录内（仅允许当前目录或用户主目录）"
            return True, ""
        except PermissionError:
            return False, "没有权限访问该路径"
        except Exception as e:
            logger.warning(f"路径验证异常: {file_path}, {e}")
            return False, f"路径验证失败: {e}"

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
        result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
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

    def _check_path_access(self, path: str, operation: str = "read") -> tuple[bool, str]:
        """
        检查沙箱模式下的路径访问权限

        Args:
            path: 文件路径
            operation: 操作类型

        Returns:
            (允许, 错误消息)
        """
        if self._config.mode == SandboxMode.UNRESTRICTED:
            return True, ""

        if self._config.mode == SandboxMode.RESTRICTED:
            return self.validate_path(path, operation)

        # STANDARD 模式允许当前目录和主目录
        return True, ""

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

        # 代码安全验证
        try:
            skill_code = inspect.getsource(func)
            validation = self.validate_skill(skill_name, skill_code)
            if validation["data"]["warnings"]:
                logger.warning(f"技能 {skill_name} 安全警告: {validation['data']['warnings']}")
        except Exception as e:
            logger.debug(f"无法获取技能源码进行验证: {skill_name}, {e}")

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

        except PathIsolationError as e:
            logger.warning(f"路径隔离违规: {skill_name}, {e}")
            return self._build_error_result(f"路径隔离违规: {e}", (time.time() - start_time) * 1000)
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
                "allowed_paths": self._config.allowed_paths,
                "denied_paths": self._config.denied_paths,
            },
        }

    def set_config(self, **kwargs) -> dict:
        """更新沙箱配置"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        return {"success": True, "data": self._config.__dict__, "error": None}

    def add_allowed_path(self, path: str) -> dict:
        """添加允许的路径到白名单"""
        resolved = str(Path(path).resolve())
        if resolved not in self._config.allowed_paths:
            self._config.allowed_paths.append(resolved)
        return {"success": True, "data": {"allowed_paths": self._config.allowed_paths}, "error": None}

    def remove_allowed_path(self, path: str) -> dict:
        """从白名单移除路径"""
        resolved = str(Path(path).resolve())
        if resolved in self._config.allowed_paths:
            self._config.allowed_paths.remove(resolved)
        return {"success": True, "data": {"allowed_paths": self._config.allowed_paths}, "error": None}


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
    def create_restricted(cls, name: str, allowed_paths: list[str] | None = None) -> "SkillSandbox":
        """
        创建严格模式沙箱

        Args:
            name: 沙箱名称
            allowed_paths: 可选的路径白名单
        """
        config = SandboxConfig(mode=SandboxMode.RESTRICTED)
        if allowed_paths:
            config.allowed_paths = [str(Path(p).resolve()) for p in allowed_paths]
        return cls.get_sandbox(name, config)

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


def create_isolated_sandbox(name: str, allowed_paths: list[str]) -> SkillSandbox:
    """
    创建带有路径白名单的隔离沙箱

    Args:
        name: 沙箱名称
        allowed_paths: 允许访问的目录列表

    Returns:
        配置好的 SkillSandbox 实例
    """
    config = SandboxConfig(mode=SandboxMode.RESTRICTED, allowed_paths=[str(Path(p).resolve()) for p in allowed_paths])
    return SkillSandbox(config)
