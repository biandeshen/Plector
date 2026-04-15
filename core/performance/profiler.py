"""性能瓶领分析器 - Plector Profiler"""
import time
import functools
from typing import Dict, Callable, Any, List
from dataclasses import dataclass, field


@dataclass
class ProfileResult:
    """性能剖析结果"""
    name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0

    def update(self, duration: float):
        self.call_count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.call_count


class Profiler:
    """轻量级性能剖析器"""

    def __init__(self):
        self.results: Dict[str, ProfileResult] = {}
        self.enabled = True
        self._stack: List[tuple] = []

    def profile(self, name: str = None) -> Callable:
        """装饰器：标记需要剖析的函数"""
        def decorator(func: Callable) -> Callable:
            profile_name = name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    self._record(profile_name, duration)

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if not self.enabled:
                    return await func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    duration = time.perf_counter() - start
                    self._record(profile_name, duration)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator

    def _record(self, name: str, duration: float):
        """记录执行时间"""
        if name not in self.results:
            self.results[name] = ProfileResult(name=name)
        self.results[name].update(duration)

    def get_report(self) -> List[ProfileResult]:
        """获取剖析报告，按总时间降序"""
        return sorted(self.results.values(), key=lambda x: x.total_time, reverse=True)

    def print_report(self):
        """打印剖析报告"""
        print("\n" + "=" * 70)
        print(f"{'Name':<40} {'Calls':>6} {'Total':>8} {'Avg':>8} {'Min':>8} {'Max':>8}")
        print("-" * 70)
        for r in self.get_report():
            print(f"{r.name:<40} {r.call_count:>6} {r.total_time*1000:>7.2f}ms "
                  f"{r.avg_time*1000:>7.2f}ms {r.min_time*1000:>7.2f}ms {r.max_time*1000:>7.2f}ms")
        print("=" * 70)

    def reset(self):
        """重置所有数据"""
        self.results.clear()


# 全局实例
_default_profiler = Profiler()


def get_profiler() -> Profiler:
    """获取全局剖析器实例"""
    return _default_profiler


# 便捷装饰器
def profile(name: str = None):
    return _default_profiler.profile(name)


import asyncio
