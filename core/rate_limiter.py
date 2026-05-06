"""
速率限制器 - 令牌桶算法

使用方式:
    from core.rate_limiter import rate_limiter

    if not rate_limiter.allow("user_123"):
        return {"error": "请求过于频繁"}
"""

import time
from collections import defaultdict
from collections.abc import Callable


class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, requests_per_minute: int = 60):
        self.rate = requests_per_minute / 60  # 每秒令牌数
        self.capacity = requests_per_minute  # 桶容量
        self.buckets: dict[str, dict] = defaultdict(lambda: {"tokens": self.capacity, "last": time.time()})

    def allow(self, key: str) -> bool:
        """检查是否允许请求，更新令牌桶"""
        now = time.time()
        data = self.buckets[key]
        elapsed = now - data["last"]
        # 补充令牌
        data["tokens"] = min(self.capacity, data["tokens"] + elapsed * self.rate)
        data["last"] = now
        # 消费令牌
        if data["tokens"] >= 1:
            data["tokens"] -= 1
            return True
        return False

    def get_remaining(self, key: str) -> int:
        """获取剩余令牌数"""
        return int(self.buckets[key].get("tokens", 0))

    def reset(self, key: str | None = None):
        """重置指定 key 或全部"""
        if key:
            if key in self.buckets:
                del self.buckets[key]
        else:
            self.buckets.clear()


# 全局实例
rate_limiter = RateLimiter(requests_per_minute=60)


def check_rate_limit(key: str) -> tuple[bool, str]:
    """
    检查速率限制，返回 (是否通过, 错误消息)

    使用方式:
        allowed, msg = check_rate_limit("user_123")
        if not allowed:
            return {"error": msg}
    """
    if not rate_limiter.allow(key):
        return False, "请求过于频繁，请稍后再试"
    return True, ""


# 便捷装饰器
def rate_limit(key_func: Callable | None = None, requests_per_minute: int = 60):
    """
    速率限制装饰器

    使用方式:
        @rate_limit()
        async def my_handler():
            pass

        # 或指定 key 函数
        @rate_limit(key_func=lambda args: args.get("user_id"))
        async def my_handler(user_id, ...):
            pass
    """
    limiter = RateLimiter(requests_per_minute)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else "default"
            if not limiter.allow(key):
                return {"success": False, "error": "请求过于频繁，请稍后再试", "rate_limited": True}
            return await func(*args, **kwargs)

        return wrapper

    return decorator
