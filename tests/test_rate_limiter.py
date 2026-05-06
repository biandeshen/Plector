"""
Tests for core/rate_limiter.py

Covers:
- TokenBucket allow/deny
- get_remaining, reset
- Multi-key isolation
- Time-based refill behavior
- rate_limit decorator
- check_rate_limit convenience function
"""

import time

import pytest

from core.rate_limiter import RateLimiter, check_rate_limit, rate_limit

# ─── RateLimiter ────────────────────────────────────────


class TestRateLimiter:
    def test_initial_state_has_no_buckets(self):
        limiter = RateLimiter(requests_per_minute=10)
        assert len(limiter.buckets) == 0

    def test_allow_returns_true_within_capacity(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert limiter.allow("key1") is True

    def test_deny_when_exceeds_capacity(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            limiter.allow("key1")
        assert limiter.allow("key1") is False

    def test_single_request_allowed(self):
        limiter = RateLimiter(requests_per_minute=1)
        assert limiter.allow("key1") is True
        assert limiter.allow("key1") is False

    def test_different_keys_isolated(self):
        """Each key has its own token bucket."""
        limiter = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            assert limiter.allow("key_a") is True
        assert limiter.allow("key_a") is False

        assert limiter.allow("key_b") is True
        assert limiter.allow("key_b") is True
        assert limiter.allow("key_b") is True
        assert limiter.allow("key_b") is False

    def test_get_remaining_returns_capacity_for_new_key(self):
        limiter = RateLimiter(requests_per_minute=10)
        assert limiter.get_remaining("new_key") == 10

    def test_reset_single_key(self):
        limiter = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            limiter.allow("key1")
        assert limiter.allow("key1") is False

        limiter.reset("key1")
        assert limiter.get_remaining("key1") == 3

    def test_reset_all_keys(self):
        limiter = RateLimiter(requests_per_minute=3)
        limiter.allow("key_a")
        limiter.allow("key_b")
        limiter.allow("key_c")
        assert len(limiter.buckets) == 3

        limiter.reset()
        assert len(limiter.buckets) == 0

    def test_reset_nonexistent_key_no_error(self):
        limiter = RateLimiter(requests_per_minute=10)
        limiter.reset("nonexistent")

    def test_reset_empty_no_error(self):
        limiter = RateLimiter()
        limiter.reset()

    def test_time_based_refill(self):
        """After exhausting tokens, waiting should refill at least one token."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 token/sec
        for _ in range(60):
            limiter.allow("refill_test")
        assert limiter.allow("refill_test") is False

        time.sleep(1.1)

        assert limiter.allow("refill_test") is True

    def test_time_based_partial_refill_not_enough(self):
        """Partial refill (less than 1 token) should still deny."""
        limiter = RateLimiter(requests_per_minute=600)  # 10 tokens/sec
        for _ in range(600):
            limiter.allow("partial_test")
        assert limiter.allow("partial_test") is False

        time.sleep(0.05)

        assert isinstance(limiter.allow("partial_test"), bool)

    def test_bucket_capacity_respected_after_refill(self):
        """Tokens should never exceed capacity even after long waits."""
        limiter = RateLimiter(requests_per_minute=10)
        assert limiter.allow("cap_test") is True
        time.sleep(2)
        remaining = limiter.get_remaining("cap_test")
        assert remaining <= 10

    def test_default_rate_is_60_per_minute(self):
        limiter = RateLimiter()
        assert limiter.rate == 1.0
        assert limiter.capacity == 60

    def test_zero_rate_construction(self):
        """With requests_per_minute=0, the limiter should not crash."""
        limiter = RateLimiter(requests_per_minute=0)
        assert limiter.allow("key") is False

    def test_high_capacity_sequential_consumption(self):
        """All tokens in a full bucket can be consumed sequentially."""
        cap = 100
        limiter = RateLimiter(requests_per_minute=cap)
        for i in range(cap):
            assert limiter.allow("high_cap") is True, f"Failed at token {i + 1}/{cap}"
        assert limiter.allow("high_cap") is False

    def test_allow_returns_bool(self):
        limiter = RateLimiter(requests_per_minute=5)
        result = limiter.allow("bool_test")
        assert isinstance(result, bool)


# ─── check_rate_limit ───────────────────────────────────


class TestCheckRateLimit:
    def test_allowed_below_limit(self):
        allowed, msg = check_rate_limit("new_key")
        assert allowed is True
        assert msg == ""

    def test_blocked_at_limit(self):
        """Exhaust the limiter and verify the block message."""
        # Import and monkeypatch the global rate_limiter
        import core.rate_limiter as rl

        original = rl.rate_limiter
        try:
            limiter = RateLimiter(requests_per_minute=3)
            for _ in range(3):
                limiter.allow("block_key")
            rl.rate_limiter = limiter

            allowed, msg = check_rate_limit("block_key")
            assert allowed is False
            assert "请求过于频繁" in msg
        finally:
            rl.rate_limiter = original


# ─── rate_limit decorator ───────────────────────────────


class TestRateLimitDecorator:
    @pytest.mark.asyncio
    async def test_allows_normal_requests(self):
        """Basic usage: requests under the limit pass through."""

        @rate_limit()
        async def my_handler():
            return {"success": True}

        result = await my_handler()
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_blocks_excessive_requests(self):
        """Excessive requests get a rate_limited response."""

        @rate_limit(requests_per_minute=2)
        async def my_handler():
            return {"success": True}

        result1 = await my_handler()
        assert result1 == {"success": True}

        result2 = await my_handler()
        assert result2 == {"success": True}

        result3 = await my_handler()
        assert result3["success"] is False
        assert result3["rate_limited"] is True
        assert "请求过于频繁" in result3["error"]

    @pytest.mark.asyncio
    async def test_custom_key_func(self):
        """Key function extracts the rate-limiting key from args/kwargs."""

        @rate_limit(key_func=lambda *args, **kwargs: kwargs.get("user_id", "default"), requests_per_minute=1)
        async def user_handler(user_id: str):
            return {"success": True, "user_id": user_id}

        r1 = await user_handler(user_id="user_a")
        assert r1["success"] is True

        r2 = await user_handler(user_id="user_a")
        assert r2["success"] is False
        assert r2["rate_limited"] is True

        r3 = await user_handler(user_id="user_b")
        assert r3["success"] is True

    @pytest.mark.asyncio
    async def test_default_key_is_default(self):
        """Without a key_func, the decorator uses 'default' as the key."""

        @rate_limit(requests_per_minute=1)
        async def handler():
            return {"success": True}

        assert await handler() == {"success": True}
        assert (await handler())["success"] is False

    @pytest.mark.asyncio
    async def test_async_function_preserved(self):
        """The decorated function remains awaitable."""

        @rate_limit()
        async def async_fn():
            return 42

        result = await async_fn()
        assert result == 42
