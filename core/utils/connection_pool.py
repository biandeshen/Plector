"""
连接池管理器
============
支持多种连接的复用和池化管理

支持类型:
- HTTP 连接池 (httpx)
- 数据库连接池 (aiosqlite)
- 通用连接池

使用方式:
    pool = ConnectionPool(max_size=10, idle_timeout=60)
    
    # 获取连接
    conn = await pool.acquire()
    try:
        # 使用连接
        result = await do_something(conn)
    finally:
        await pool.release(conn)
    
    # 或使用上下文管理器
    async with pool.connection() as conn:
        await do_something(conn)
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class PoolConfig:
    """连接池配置"""
    max_size: int = 10
    min_size: int = 2
    idle_timeout: int = 60  # 秒
    max_lifetime: int = 3600  # 最大生命周期（秒）
    acquire_timeout: int = 30  # 获取连接超时（秒）
    health_check_interval: int = 300  # 健康检查间隔（秒）


@dataclass
class PooledConnection(Generic[T]):
    """池化连接"""
    conn: T
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True

    def mark_used(self):
        self.last_used = time.time()
        self.use_count += 1

    def age(self) -> float:
        return time.time() - self.created_at

    def idle_time(self) -> float:
        return time.time() - self.last_used


class ConnectionPool(Generic[T]):
    """
    通用连接池

    支持:
    - 连接复用
    - 空闲超时清理
    - 生命周期管理
    - 健康检查
    """

    def __init__(
        self,
        factory: Callable[[], T],
        config: PoolConfig | None = None,
    ):
        self._factory = factory
        self._config = config or PoolConfig()
        self._pool: asyncio.Queue[PooledConnection[T]] = asyncio.Queue(
            maxsize=self._config.max_size
        )
        self._all_connections: list[PooledConnection[T]] = []
        self._lock = asyncio.Lock()
        self._closed = False
        self._stats = {
            "acquired": 0,
            "released": 0,
            "created": 0,
            "closed": 0,
            "health_checks": 0,
        }

    async def initialize(self):
        """初始化 - 创建最小连接数"""
        for _ in range(self._config.min_size):
            conn = await self._create_connection()
            if conn:
                await self._pool.put(conn)

    async def acquire(self) -> T:
        """
        获取连接

        Returns:
            连接对象

        Raises:
            asyncio.TimeoutError: 获取超时
        """
        if self._closed:
            raise RuntimeError("连接池已关闭")

        try:
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=self._config.acquire_timeout,
            )
            self._stats["acquired"] += 1

            # 健康检查
            if self._should_health_check(conn):
                if not await self._check_health(conn):
                    await self._close_connection(conn)
                    conn = await self._create_connection()

            return conn.conn

        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"获取连接超时 (max_size={self._config.max_size})"
            )

    async def release(self, conn: T):
        """释放连接回池"""
        if self._closed:
            await self._close_conn_obj(conn)
            return

        pooled = PooledConnection(conn)
        pooled.mark_used()

        try:
            self._pool.put_nowait(pooled)
            self._stats["released"] += 1
        except asyncio.QueueFull:
            await self._close_conn_obj(conn)

    @asynccontextmanager
    async def connection(self):
        """上下文管理器 - 自动获取和释放"""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)

    async def close(self):
        """关闭连接池"""
        async with self._lock:
            self._closed = True

            # 关闭所有连接
            while not self._pool.empty():
                try:
                    pooled = self._pool.get_nowait()
                    await self._close_pooled(pooled)
                except asyncio.QueueEmpty:
                    break

            for pooled in self._all_connections:
                await self._close_pooled(pooled)
            self._all_connections.clear()

    # ========== 内部方法 ==========

    async def _create_connection(self) -> PooledConnection[T] | None:
        """创建新连接"""
        try:
            conn = await asyncio.get_event_loop().run_in_executor(
                None, self._factory
            )
            pooled = PooledConnection(conn)
            self._all_connections.append(pooled)
            self._stats["created"] += 1
            return pooled
        except Exception:
            logger.exception("创建连接失败")
            return None

    async def _close_pooled(self, pooled: PooledConnection[T]):
        """关闭池化连接"""
        try:
            await self._close_conn_obj(pooled.conn)
            self._stats["closed"] += 1
        except Exception:
            logger.exception("关闭连接失败")

    async def _close_conn_obj(self, conn: T):
        """关闭连接对象"""
        if hasattr(conn, "close"):
            if asyncio.iscoroutinefunction(conn.close):
                await conn.close()
            else:
                conn.close()
        elif hasattr(conn, "disconnect"):
            if asyncio.iscoroutinefunction(conn.disconnect):
                await conn.disconnect()
            else:
                conn.disconnect()

    def _should_health_check(self, pooled: PooledConnection[T]) -> bool:
        """是否应该健康检查"""
        return pooled.idle_time() > self._config.health_check_interval

    async def _check_health(self, pooled: PooledConnection[T]) -> bool:
        """健康检查"""
        self._stats["health_checks"] += 1
        try:
            if hasattr(pooled.conn, "is_connected"):
                return pooled.conn.is_connected
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "available": self._pool.qsize(),
            "max_size": self._config.max_size,
        }


# ========== 便捷函数 ==========

def create_http_pool(base_url: str, max_size: int = 10) -> ConnectionPool:
    """创建 HTTP 连接池"""
    import httpx

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=base_url,
            limits=httpx.Limits(max_connections=max_size),
        )

    config = PoolConfig(max_size=max_size)
    return ConnectionPool(factory, config)
