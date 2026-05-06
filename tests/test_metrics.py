"""
Tests for core.metrics
"""

import time
from concurrent.futures import ThreadPoolExecutor

from core.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    Timer,
    get_metrics_collector,
    reset_metrics,
)

# ─── Counter ────────────────────────────────────────────────────


class TestCounter:
    def test_initial_value_zero(self):
        c = Counter()
        assert c.get() == 0

    def test_inc_default(self):
        c = Counter()
        c.inc()
        assert c.get() == 1

    def test_inc_custom_value(self):
        c = Counter()
        c.inc(5)
        assert c.get() == 5

    def test_inc_multiple_times(self):
        c = Counter()
        c.inc(2)
        c.inc(3)
        assert c.get() == 5

    def test_reset(self):
        c = Counter()
        c.inc(100)
        c.reset()
        assert c.get() == 0

    def test_reset_from_zero(self):
        c = Counter()
        c.reset()
        assert c.get() == 0


# ─── Histogram ──────────────────────────────────────────────────


class TestHistogram:
    def test_empty_stats(self):
        h = Histogram()
        stats = h.get_stats()
        assert stats == {"count": 0, "sum": 0, "min": 0, "max": 0, "avg": 0}

    def test_single_observation(self):
        h = Histogram()
        h.observe(10.0)
        stats = h.get_stats()
        assert stats["count"] == 1
        assert stats["min"] == 10.0
        assert stats["max"] == 10.0
        assert stats["avg"] == 10.0
        assert stats["sum"] == 10.0

    def test_multiple_observations(self):
        h = Histogram()
        h.observe(1.0)
        h.observe(2.0)
        h.observe(3.0)
        stats = h.get_stats()
        assert stats["count"] == 3
        assert stats["min"] == 1.0
        assert stats["max"] == 3.0
        assert stats["avg"] == 2.0
        assert stats["sum"] == 6.0

    def test_rounding_to_three_decimals(self):
        h = Histogram()
        h.observe(1.12345)
        stats = h.get_stats()
        assert stats["min"] == 1.123
        assert stats["max"] == 1.123
        assert stats["avg"] == 1.123
        assert stats["sum"] == 1.123

    def test_max_size_trimming(self):
        """Histogram keeps only the last _max_size values."""
        h = Histogram()
        h._max_size = 5
        for i in range(10):
            h.observe(float(i))
        stats = h.get_stats()
        assert stats["count"] == 5
        assert stats["min"] == 5.0
        assert stats["max"] == 9.0


# ─── Gauge ──────────────────────────────────────────────────────


class TestGauge:
    def test_initial_value_zero(self):
        g = Gauge()
        assert g.get() == 0.0

    def test_set(self):
        g = Gauge()
        g.set(42.5)
        assert g.get() == 42.5

    def test_set_overwrites(self):
        g = Gauge()
        g.set(10.0)
        g.set(20.0)
        assert g.get() == 20.0

    def test_inc_default(self):
        g = Gauge()
        g.inc()
        assert g.get() == 1.0

    def test_inc_custom_value(self):
        g = Gauge()
        g.inc(5.5)
        assert g.get() == 5.5

    def test_dec_default(self):
        g = Gauge()
        g.set(10.0)
        g.dec()
        assert g.get() == 9.0

    def test_dec_custom_value(self):
        g = Gauge()
        g.set(10.0)
        g.dec(3.5)
        assert g.get() == 6.5

    def test_inc_then_dec(self):
        g = Gauge()
        g.inc(5)
        g.dec(2)
        assert g.get() == 3.0


# ─── MetricsCollector ───────────────────────────────────────────


class TestMetricsCollector:
    def test_initial_all_zeros(self):
        mc = MetricsCollector()
        metrics = mc.get_all_metrics()
        assert metrics["agent"]["iterations_total"] == 0
        assert metrics["agent"]["errors_total"] == 0
        assert metrics["llm"]["requests_total"] == 0
        assert metrics["llm"]["errors_total"] == 0
        assert metrics["llm"]["tokens_used_total"] == 0
        assert metrics["tool"]["calls_total"] == 0
        assert metrics["tool"]["errors_total"] == 0
        assert metrics["system"]["active_connections"] == 0.0
        assert metrics["system"]["websocket_connections"] == 0.0

    def test_inc_iteration(self):
        mc = MetricsCollector()
        mc.inc_iteration()
        assert mc.get_all_metrics()["agent"]["iterations_total"] == 1

    def test_record_agent_response_time(self):
        mc = MetricsCollector()
        mc.record_agent_response_time(1.5)
        stats = mc.get_all_metrics()["agent"]["response_time"]
        assert stats["count"] == 1
        assert stats["avg"] == 1.5

    def test_inc_agent_error(self):
        mc = MetricsCollector()
        mc.inc_agent_error()
        mc.inc_agent_error()
        assert mc.get_all_metrics()["agent"]["errors_total"] == 2

    def test_inc_llm_request(self):
        mc = MetricsCollector()
        mc.inc_llm_request()
        assert mc.get_all_metrics()["llm"]["requests_total"] == 1

    def test_record_llm_latency(self):
        mc = MetricsCollector()
        mc.record_llm_latency(0.5)
        mc.record_llm_latency(1.5)
        stats = mc.get_all_metrics()["llm"]["latency"]
        assert stats["count"] == 2
        assert stats["avg"] == 1.0

    def test_inc_llm_error(self):
        mc = MetricsCollector()
        mc.inc_llm_error()
        assert mc.get_all_metrics()["llm"]["errors_total"] == 1

    def test_inc_tokens(self):
        mc = MetricsCollector()
        mc.inc_tokens(100)
        mc.inc_tokens(50)
        assert mc.get_all_metrics()["llm"]["tokens_used_total"] == 150

    def test_inc_tool_call(self):
        mc = MetricsCollector()
        mc.inc_tool_call("search")
        mc.inc_tool_call("search")
        mc.inc_tool_call("read")
        metrics = mc.get_all_metrics()
        assert metrics["tool"]["calls_total"] == 3
        assert metrics["tool"]["by_tool"]["search"] == 2
        assert metrics["tool"]["by_tool"]["read"] == 1

    def test_inc_tool_error(self):
        mc = MetricsCollector()
        mc.inc_tool_error()
        assert mc.get_all_metrics()["tool"]["errors_total"] == 1

    def test_record_tool_latency(self):
        mc = MetricsCollector()
        mc.record_tool_latency(0.3)
        stats = mc.get_all_metrics()["tool"]["latency"]
        assert stats["count"] == 1

    def test_set_active_connections(self):
        mc = MetricsCollector()
        mc.set_active_connections(5)
        assert mc.get_all_metrics()["system"]["active_connections"] == 5

    def test_inc_websocket_connection(self):
        mc = MetricsCollector()
        mc.inc_websocket_connection()
        mc.inc_websocket_connection()
        assert mc.get_all_metrics()["system"]["websocket_connections"] == 2.0

    def test_dec_websocket_connection(self):
        mc = MetricsCollector()
        mc.inc_websocket_connection()
        mc.inc_websocket_connection()
        mc.dec_websocket_connection()
        assert mc.get_all_metrics()["system"]["websocket_connections"] == 1.0

    def test_get_all_metrics_structure(self):
        """get_all_metrics returns the expected nested structure."""
        mc = MetricsCollector()
        mc.inc_iteration()
        mc.inc_llm_request()
        mc.inc_tool_call("test_tool")
        mc.set_active_connections(3)

        metrics = mc.get_all_metrics()
        assert set(metrics.keys()) == {"agent", "llm", "tool", "system"}
        assert metrics["agent"]["iterations_total"] == 1
        assert metrics["llm"]["requests_total"] == 1
        assert metrics["tool"]["by_tool"]["test_tool"] == 1
        assert metrics["system"]["active_connections"] == 3

    def test_reset_all(self):
        mc = MetricsCollector()
        mc.inc_iteration()
        mc.inc_llm_request()
        mc.inc_tool_call("search")
        mc.set_active_connections(5)
        mc.record_agent_response_time(1.0)
        mc.record_llm_latency(0.5)

        mc.reset_all()
        metrics = mc.get_all_metrics()
        assert metrics["agent"]["iterations_total"] == 0
        assert metrics["llm"]["requests_total"] == 0
        assert metrics["tool"]["calls_total"] == 0
        assert metrics["tool"]["by_tool"] == {}
        assert metrics["system"]["active_connections"] == 0.0
        assert metrics["agent"]["response_time"]["count"] == 0
        assert metrics["llm"]["latency"]["count"] == 0

    def test_reset_all_empty_collector(self):
        """reset_all on a fresh collector does not raise."""
        mc = MetricsCollector()
        mc.reset_all()
        metrics = mc.get_all_metrics()
        assert metrics["agent"]["iterations_total"] == 0


# ─── Timer ──────────────────────────────────────────────────────


class TestTimer:
    def test_timer_records_duration(self):
        """Timer context manager calls the callback with a positive duration."""
        recorded = []

        def cb(duration):
            recorded.append(duration)

        with Timer(cb):
            time.sleep(0.01)

        assert len(recorded) == 1
        assert recorded[0] > 0

    def test_timer_noop_without_enter(self):
        """Timer does not blow up if __exit__ is called without __enter__."""
        recorded = []

        def cb(duration):
            recorded.append(duration)

        t = Timer(cb)
        t.__exit__(None, None, None)
        assert len(recorded) == 0


# ─── Concurrency / Thread safety ────────────────────────────────


class TestConcurrency:
    def test_counter_thread_safety(self):
        """Counter is safe under concurrent increments from multiple threads."""
        c = Counter()
        n_threads = 10
        increments_per_thread = 1000

        def worker():
            for _ in range(increments_per_thread):
                c.inc()

        with ThreadPoolExecutor(max_workers=n_threads) as exe:
            futures = [exe.submit(worker) for _ in range(n_threads)]
            for f in futures:
                f.result()

        assert c.get() == n_threads * increments_per_thread

    def test_histogram_thread_safety(self):
        """Histogram is safe under concurrent observations."""
        h = Histogram()
        n_threads = 10
        obs_per_thread = 100

        def worker():
            for i in range(obs_per_thread):
                h.observe(float(i))

        with ThreadPoolExecutor(max_workers=n_threads) as exe:
            futures = [exe.submit(worker) for _ in range(n_threads)]
            for f in futures:
                f.result()

        stats = h.get_stats()
        assert stats["count"] == n_threads * obs_per_thread

    def test_gauge_thread_safety(self):
        """Gauge is safe under concurrent operations."""
        g = Gauge()
        n_threads = 10

        def worker():
            for _ in range(500):
                g.inc()
                g.dec()

        with ThreadPoolExecutor(max_workers=n_threads) as exe:
            futures = [exe.submit(worker) for _ in range(n_threads)]
            for f in futures:
                f.result()

        # Should be back to zero since inc/dec are balanced
        assert g.get() == 0.0

    def test_metrics_collector_thread_safety(self):
        """MetricsCollector operations are safe from multiple threads."""
        mc = MetricsCollector()
        n_threads = 10
        ops_per_thread = 500

        def worker():
            for _ in range(ops_per_thread):
                mc.inc_iteration()
                mc.inc_llm_request()
                mc.inc_tool_call("search")
                mc.inc_tool_call("read")

        with ThreadPoolExecutor(max_workers=n_threads) as exe:
            futures = [exe.submit(worker) for _ in range(n_threads)]
            for f in futures:
                f.result()

        metrics = mc.get_all_metrics()
        expected_total = n_threads * ops_per_thread
        assert metrics["agent"]["iterations_total"] == expected_total
        assert metrics["llm"]["requests_total"] == expected_total
        assert metrics["tool"]["calls_total"] == expected_total * 2
        assert metrics["tool"]["by_tool"]["search"] == expected_total
        assert metrics["tool"]["by_tool"]["read"] == expected_total


# ─── Global helpers ─────────────────────────────────────────────


class TestGlobalHelpers:
    def test_get_metrics_collector_singleton(self):
        """get_metrics_collector() returns the same instance on repeated calls."""
        mc1 = get_metrics_collector()
        mc2 = get_metrics_collector()
        assert mc1 is mc2

    def test_reset_metrics_clears_global(self):
        """reset_metrics() resets and replaces the global instance."""
        mc = get_metrics_collector()
        mc.inc_iteration()
        reset_metrics()
        mc2 = get_metrics_collector()
        assert mc2.get_all_metrics()["agent"]["iterations_total"] == 0
        assert mc2 is not mc

    def test_reset_metrics_noop_when_no_instance(self):
        """reset_metrics() does not raise when called with no global instance."""
        # Ensure no global instance
        reset_metrics()
        # This should not raise even though _metrics_collector is None
        reset_metrics()
