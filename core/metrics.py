"""
Prometheus-style metrics collector for Plector

Provides:
- Counter: for events (tool_calls, errors, iterations)
- Histogram: for latencies (LLM calls, tool execution)
- Gauge: for current state (active connections)

Metrics are returned as JSON at /api/metrics endpoint.
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Counter:
    """Simple counter metric"""

    _value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, value: int = 1):
        with self._lock:
            self._value += value

    def get(self) -> int:
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0


@dataclass
class Histogram:
    """Simple histogram metric for tracking latencies"""

    _values: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _max_size: int = 1000  # Keep last 1000 values

    def observe(self, value: float):
        with self._lock:
            self._values.append(value)
            if len(self._values) > self._max_size:
                self._values = self._values[-self._max_size :]

    def get_stats(self) -> dict:
        with self._lock:
            if not self._values:
                return {"count": 0, "sum": 0, "min": 0, "max": 0, "avg": 0}
            return {
                "count": len(self._values),
                "sum": round(sum(self._values), 3),
                "min": round(min(self._values), 3),
                "max": round(max(self._values), 3),
                "avg": round(sum(self._values) / len(self._values), 3),
            }


@dataclass
class Gauge:
    """Simple gauge metric for current state"""

    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set(self, value: float):
        with self._lock:
            self._value = value

    def get(self) -> float:
        with self._lock:
            return self._value

    def inc(self, value: float = 1):
        with self._lock:
            self._value += value

    def dec(self, value: float = 1):
        with self._lock:
            self._value -= value


class MetricsCollector:
    """
    Central metrics collector for Plector

    Metrics are organized by category:
    - agent: iteration count, response time
    - llm: token usage, API latency, error rates
    - tool: tool call counts and latencies
    - system: active connections
    """

    def __init__(self):
        # Agent metrics
        self.iterations_total = Counter()
        self.agent_response_time = Histogram()
        self.agent_errors = Counter()

        # LLM metrics
        self.llm_requests_total = Counter()
        self.llm_latency = Histogram()
        self.llm_errors = Counter()
        self.tokens_used = Counter()

        # Tool metrics
        self.tool_calls_total = Counter()
        self.tool_latency = Histogram()
        self.tool_errors = Counter()
        self._tool_call_counts: dict[str, Counter] = defaultdict(Counter)

        # System metrics
        self.active_connections = Gauge()
        self.websocket_connections = Gauge()

    def inc_iteration(self):
        """Increment iteration counter"""
        self.iterations_total.inc()

    def record_agent_response_time(self, duration: float):
        """Record agent response time in seconds"""
        self.agent_response_time.observe(duration)

    def inc_agent_error(self):
        """Increment agent error counter"""
        self.agent_errors.inc()

    def inc_llm_request(self):
        """Increment LLM request counter"""
        self.llm_requests_total.inc()

    def record_llm_latency(self, duration: float):
        """Record LLM API latency in seconds"""
        self.llm_latency.observe(duration)

    def inc_llm_error(self):
        """Increment LLM error counter"""
        self.llm_errors.inc()

    def inc_tokens(self, count: int = 1):
        """Increment token counter"""
        self.tokens_used.inc(count)

    def inc_tool_call(self, tool_name: str):
        """Increment tool call counter for specific tool"""
        self.tool_calls_total.inc()
        self._tool_call_counts[tool_name].inc()

    def record_tool_latency(self, duration: float):
        """Record tool execution latency in seconds"""
        self.tool_latency.observe(duration)

    def inc_tool_error(self):
        """Increment tool error counter"""
        self.tool_errors.inc()

    def set_active_connections(self, count: int):
        """Set active connections gauge"""
        self.active_connections.set(count)

    def inc_websocket_connection(self):
        """Increment WebSocket connection counter"""
        self.websocket_connections.inc()

    def dec_websocket_connection(self):
        """Decrement WebSocket connection counter"""
        self.websocket_connections.dec()

    def get_all_metrics(self) -> dict:
        """Get all metrics as a dictionary"""
        metrics = {
            "agent": {
                "iterations_total": self.iterations_total.get(),
                "response_time": self.agent_response_time.get_stats(),
                "errors_total": self.agent_errors.get(),
            },
            "llm": {
                "requests_total": self.llm_requests_total.get(),
                "latency": self.llm_latency.get_stats(),
                "errors_total": self.llm_errors.get(),
                "tokens_used_total": self.tokens_used.get(),
            },
            "tool": {
                "calls_total": self.tool_calls_total.get(),
                "latency": self.tool_latency.get_stats(),
                "errors_total": self.tool_errors.get(),
                "by_tool": {name: counter.get() for name, counter in self._tool_call_counts.items()},
            },
            "system": {
                "active_connections": self.active_connections.get(),
                "websocket_connections": self.websocket_connections.get(),
            },
        }
        return metrics

    def reset_all(self):
        """Reset all metrics (useful for testing)"""
        self.iterations_total.reset()
        self.agent_response_time._values = []
        self.agent_errors.reset()
        self.llm_requests_total.reset()
        self.llm_latency._values = []
        self.llm_errors.reset()
        self.tokens_used.reset()
        self.tool_calls_total.reset()
        self.tool_latency._values = []
        self.tool_errors.reset()
        self._tool_call_counts.clear()
        self.active_connections = Gauge()
        self.websocket_connections = Gauge()


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None
_metrics_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    with _metrics_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector (for testing)"""
    global _metrics_collector
    with _metrics_lock:
        if _metrics_collector is not None:
            _metrics_collector.reset_all()
        _metrics_collector = None


class Timer:
    """Context manager for timing operations"""

    def __init__(self, callback: Callable[[float], None]):
        self.callback = callback
        self.start_time: float | None = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time
            self.callback(duration)
