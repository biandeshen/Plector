"""指标收集系统 - Prometheus 风格"""
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Counter:
    """计数器"""
    name: str
    value: float = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def inc(self, amount: float = 1):
        self.value += amount

    def reset(self):
        self.value = 0


@dataclass
class Gauge:
    """仪表"""
    name: str
    value: float = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float):
        self.value = value

    def inc(self, amount: float = 1):
        self.value += amount

    def dec(self, amount: float = 1):
        self.value -= amount


@dataclass
class Histogram:
    """直方图"""
    name: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10])
    labels: Dict[str, str] = field(default_factory=dict)
    values: List[float] = field(default_factory=list)

    def observe(self, value: float):
        self.values.append(value)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def sum(self) -> float:
        return sum(self.values)

    def get_percentile(self, p: float) -> float:
        if not self.values:
            return 0
        sorted_values = sorted(self.values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self._start_time = time.time()

    def counter(self, name: str, labels: Dict[str, str] = None) -> Counter:
        key = self._make_key(name, labels)
        if key not in self.counters:
            self.counters[key] = Counter(name, labels=labels or {})
        return self.counters[key]

    def gauge(self, name: str, labels: Dict[str, str] = None) -> Gauge:
        key = self._make_key(name, labels)
        if key not in self.gauges:
            self.gauges[key] = Gauge(name, labels=labels or {})
        return self.gauges[key]

    def histogram(self, name: str, labels: Dict[str, str] = None) -> Histogram:
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = Histogram(name, labels=labels or {})
        return self.histograms[key]

    def _make_key(self, name: str, labels: Optional[Dict]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_prometheus_format(self) -> str:
        """导出 Prometheus 格式"""
        lines = []

        for c in self.counters.values():
            lines.append(f"# TYPE {c.name} counter")
            label_str = self._format_labels(c.labels)
            lines.append(f"{c.name}{label_str} {c.value}")

        for g in self.gauges.values():
            lines.append(f"# TYPE {g.name} gauge")
            label_str = self._format_labels(g.labels)
            lines.append(f"{g.name}{label_str} {g.value}")

        for h in self.histograms.values():
            lines.append(f"# TYPE {h.name} histogram")
            label_str = self._format_labels(h.labels)

            cumulative = 0
            for bucket in h.buckets:
                cumulative += sum(1 for v in h.values if v <= bucket)
                lines.append(f'{h.name}_bucket{{le="{bucket}"}}{label_str} {cumulative}')
            lines.append(f'{h.name}_bucket{{le="+Inf"}}{label_str} {h.count}')
            lines.append(f"{h.name}_sum{label_str} {h.sum}")
            lines.append(f"{h.name}_count{label_str} {h.count}")

        return "\n".join(lines)

    def _format_labels(self, labels: Dict) -> str:
        if not labels:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in labels.items()) + "}"

    def reset(self):
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()


# 全局实例
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics
