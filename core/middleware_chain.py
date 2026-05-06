# mypy: ignore-errors
"""
MiddlewareChain - 中间件链式处理架构

为 AgentLoop 提供可插拔的中间件能力，支持：
- MemoryMiddleware: 记忆上下文自动注入
- GovernanceMiddleware: 技能健康分检查
- SecurityMiddleware: 安全检查
- LoggingMiddleware: 日志记录
- AuditMiddleware: 操作审计

使用方式：
    chain = MiddlewareChain()
    chain.add(MemoryMiddleware())
    chain.add(GovernanceMiddleware())
    result = await chain.execute(request, handler)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .governance import Governance

logger = logging.getLogger(__name__)


@dataclass
class MiddlewareContext:
    """中间件共享上下文"""

    session_id: str = "default"
    user_input: str = ""
    messages: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.metadata[key] = value


class Middleware(ABC):
    """中间件基类"""

    name: str = "base_middleware"

    @abstractmethod
    async def before(self, ctx: MiddlewareContext) -> bool:
        """
        前置处理。返回 True 继续执行，返回 False 跳过此中间件。

        Args:
            ctx: 中间件共享上下文

        Returns:
            True 继续执行，False 跳过
        """
        return True

    async def after(self, ctx: MiddlewareContext, response: Any) -> Any:
        """
        后置处理。可以修改响应。

        Args:
            ctx: 中间件共享上下文
            response: 原始响应

        Returns:
            修改后的响应
        """
        return response

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:  # noqa: B027
        """
        错误处理。子类可重写以自定义错误处理逻辑。

        Args:
            ctx: 中间件共享上下文
            error: 发生的异常
        """
        pass


class MiddlewareChain:
    """
    中间件链式处理器

    支持：
    - add() 添加中间件
    - execute() 执行链式处理
    - 异常时调用所有中间件的 on_error
    """

    def __init__(self):
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> "MiddlewareChain":
        """添加中间件（返回自身支持链式调用）"""
        self._middlewares.append(middleware)
        return self

    def remove(self, middleware: Middleware) -> None:
        """移除中间件"""
        if middleware in self._middlewares:
            self._middlewares.remove(middleware)

    async def execute(self, ctx: MiddlewareContext, handler: Callable[[], Any]) -> Any:
        """
        执行中间件链

        Args:
            ctx: 中间件共享上下文
            handler: 实际的处理函数（可以是协程或普通函数）

        Returns:
            处理结果
        """
        # 前置处理
        for mw in self._middlewares:
            try:
                should_continue = await mw.before(ctx)
                if not should_continue:
                    logger.debug(f"Middleware {mw.name} skipped")
                    continue
            except Exception as e:
                logger.warning(f"Middleware {mw.name}.before() failed: {e}")
                continue

        # 执行处理函数
        try:
            if asyncio.iscoroutinefunction(handler):
                response = await handler()
            else:
                response = handler()
        except Exception as e:
            # 错误处理
            for mw in reversed(self._middlewares):
                try:
                    await mw.on_error(ctx, e)
                except Exception as mw_error:
                    logger.warning(f"Middleware {mw.name}.on_error() failed: {mw_error}")

            raise

        # 后置处理
        for mw in self._middlewares:
            try:
                response = await mw.after(ctx, response)
            except Exception as e:
                logger.warning(f"Middleware {mw.name}.after() failed: {e}")

        return response


# === 具体中间件实现 ===


class GovernanceMiddleware(Middleware):
    """技能健康分检查中间件"""

    name = "governance"

    def __init__(self, governance: Governance, min_health_score: float = 0.3):
        """
        Args:
            governance: Governance 实例
            min_health_score: 最小健康分，低于此值跳过技能
        """
        self._governance = governance
        self._min_health_score = min_health_score

    async def before(self, ctx: MiddlewareContext) -> bool:
        """检查技能健康分"""
        # 从 metadata 获取当前技能名
        skill_name = ctx.get("current_skill")
        if not skill_name:
            return True

        health_score = self._governance.health_scores.get(skill_name, 1.0)
        if health_score < self._min_health_score:
            logger.warning(f"技能 {skill_name} 健康分 {health_score} 低于阈值 {self._min_health_score}")
            ctx.set("skill_degraded", True)
            ctx.set("degraded_skill", skill_name)
            # 不阻止执行，只是标记
        return True

    async def on_error(self, ctx: MiddlewareContext, error: Exception) -> None:
        """记录错误到健康分"""
        skill_name = ctx.get("current_skill") or ctx.get("degraded_skill")
        if skill_name:
            try:
                self._governance.update_health_score(skill_name, success=False, duration_ms=0)
            except Exception as e:
                logger.warning(f"GovernanceMiddleware 更新健康分失败: {e}")


class LoggingMiddleware(Middleware):
    """日志记录中间件"""

    name = "logging"

    def __init__(self, log_level: str = "INFO"):
        self._log_level = getattr(logging, log_level.upper(), logging.INFO)

    async def before(self, ctx: MiddlewareContext) -> bool:
        logger.log(self._log_level, f"[{ctx.session_id}] User: {ctx.user_input[:100]}")
        return True

    async def after(self, ctx: MiddlewareContext, response: Any) -> Any:
        logger.log(self._log_level, f"[{ctx.session_id}] Response received")
        return response


class SecurityMiddleware(Middleware):
    """安全检查中间件（预留）"""

    name = "security"

    def __init__(self, blocked_patterns: list[str] | None = None):
        self._blocked_patterns = blocked_patterns or []

    async def before(self, ctx: MiddlewareContext) -> bool:
        """检查输入是否包含危险模式"""
        for pattern in self._blocked_patterns:
            if pattern in ctx.user_input.lower():
                logger.warning(f"Blocked pattern '{pattern}' detected in input")
                ctx.set("blocked", True)
                ctx.set("block_reason", f"Pattern: {pattern}")
                return False
        return True


class MemoryMiddleware(Middleware):
    """记忆上下文注入中间件（预留）"""

    name = "memory"

    def __init__(self, vector_memory=None):
        self._vm = vector_memory

    async def before(self, ctx: MiddlewareContext) -> bool:
        """注入记忆上下文"""
        if not self._vm:
            return True

        try:
            # 搜索相关记忆
            results = await self._vm.search(
                query=ctx.user_input,
                collection="preferences",
                n_results=5,
            )
            if results:
                ctx.set("memory_context", results)
        except Exception as e:
            logger.debug(f"Memory middleware search failed: {e}")

        return True


class AuditMiddleware(Middleware):
    """审计日志中间件"""

    name = "audit"

    def __init__(self, audit_log_path: str = "logs/audit.log"):
        self._log_path = audit_log_path

    async def after(self, ctx: MiddlewareContext, response: Any) -> Any:
        """记录审计日志到文件"""
        import json
        import os
        import time

        entry = {
            "session_id": ctx.session_id,
            "user_input": ctx.user_input[:200],
            "timestamp": time.time(),
        }
        try:
            log_dir = os.path.dirname(self._log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"AuditMiddleware 写入失败: {e}")
        return response
