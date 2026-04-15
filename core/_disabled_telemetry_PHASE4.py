"""遥测数据采集

职责：收集系统运行指标，用于监控和优化
遵循规则：函数不超过 50 行
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from enum import Enum


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 瞬时值
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TimerContext:
    """计时器上下文"""
    name: str
    start_time: float
    tags: Dict[str, str]
    on_complete: Optional[Callable] = None


class TelemetryCollector:
    """遥测数据收集器"""
    
    def __init__(self):
        self._metrics: Dict[str, List[Metric]] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._active_timers: Dict[str, TimerContext] = {}
    
    # ========== 计数器 ==========
    
    def increment(self, name: str, value: float = 1, tags: Optional[Dict] = None) -> None:
        """递增计数器"""
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] = self._counters.get(key, 0) + value
            
            self._record_metric(name, self._counters[key], MetricType.COUNTER, tags)
    
    def get_counter(self, name: str, tags: Optional[Dict] = None) -> float:
        """获取计数器值"""
        with self._lock:
            key = self._make_key(name, tags)
            return self._counters.get(key, 0)
    
    # ========== 仪表 ==========
    
    def gauge(self, name: str, value: float, tags: Optional[Dict] = None) -> None:
        """设置仪表值"""
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
            
            self._record_metric(name, value, MetricType.GAUGE, tags)
    
    def get_gauge(self, name: str, tags: Optional[Dict] = None) -> Optional[float]:
        """获取仪表值"""
        with self._lock:
            key = self._make_key(name, tags)
            return self._gauges.get(key)
    
    # ========== 直方图 ==========
    
    def histogram(self, name: str, value: float, tags: Optional[Dict] = None) -> None:
        """记录直方图值"""
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            
            self._record_metric(name, value, MetricType.HISTOGRAM, tags)
    
    def get_histogram_stats(self, name: str, tags: Optional[Dict] = None) -> Dict[str, float]:
        """获取直方图统计"""
        with self._lock:
            key = self._make_key(name, tags)
            values = self._histograms.get(key, [])
            
            if not values:
                return {}
            
            sorted_values = sorted(values)
            count = len(values)
            
            return {
                "count": count,
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / count,
                "p50": sorted_values[count // 2],
                "p95": sorted_values[int(count * 0.95)] if count >= 20 else sorted_values[-1],
                "p99": sorted_values[int(count * 0.99)] if count >= 100 else sorted_values[-1],
            }
    
    # ========== 计时器 ==========
    
    def start_timer(self, name: str, tags: Optional[Dict] = None) -> TimerContext:
        """开始计时"""
        ctx = TimerContext(
            name=name,
            start_time=time.time(),
            tags=tags or {},
        )
        
        with self._lock:
            self._active_timers[name] = ctx
        
        return ctx
    
    def stop_timer(self, ctx: TimerContext) -> float:
        """停止计时并记录"""
        elapsed = time.time() - ctx.start_time
        
        with self._lock:
            if ctx.name in self._active_timers:
                del self._active_timers[ctx.name]
        
        # 记录到直方图
        self.histogram(f"{ctx.name}.duration", elapsed, ctx.tags)
        
        # 调用完成回调
        if ctx.on_complete:
            ctx.on_complete(elapsed)
        
        return elapsed
    
    def timer(self, name: str, tags: Optional[Dict] = None):
        """计时器上下文管理器"""
        class Timer:
            def __enter__(t):
                t.ctx = self.start_timer(name, tags)
                return t
            
            def __exit__(t, *args):
                self.stop_timer(t.ctx)
        
        return Timer()
    
    # ========== 事件 ==========
    
    def event(self, name: str, properties: Optional[Dict] = None, tags: Optional[Dict] = None) -> None:
        """记录事件"""
        self.increment(f"events.{name}", 1, tags)
        
        if properties:
            with self._lock:
                key = self._make_key(f"events.{name}", tags)
                self._record_metric(name, properties, MetricType.GAUGE, tags)
    
    # ========== 查询 ==========
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: self.get_histogram_stats(k.split("::")[0], self._parse_tags(k))
                    for k in self._histograms
                },
            }
    
    def reset(self) -> None:
        """重置所有指标"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    # ========== 内部方法 ==========
    
    def _make_key(self, name: str, tags: Optional[Dict]) -> str:
        """生成指标键"""
        key = name
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{name}::{tag_str}"
        return key
    
    def _parse_tags(self, key: str) -> Optional[Dict]:
        """解析标签"""
        if "::" not in key:
            return None
        
        name, tag_str = key.split("::", 1)
        tags = {}
        for item in tag_str.split(","):
            k, v = item.split("=")
            tags[k] = v
        return tags
    
    def _record_metric(self, name: str, value: Any, mtype: MetricType, tags: Optional[Dict]) -> None:
        """记录指标"""
        metric = Metric(name=name, value=value, type=mtype, tags=tags or {})
        
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(metric)


# ========== 常用指标快捷方法 ==========

def record_llm_request(model: str, duration: float, tokens: int) -> None:
    """记录 LLM 请求"""
    collector = get_collector()
    collector.increment("llm.requests", tags={"model": model})
    collector.histogram("llm.duration", duration, tags={"model": model})
    collector.histogram("llm.tokens", tokens, tags={"model": model})


def record_skill_execution(skill_name: str, duration: float, success: bool) -> None:
    """记录技能执行"""
    collector = get_collector()
    collector.increment("skill.executions", tags={"skill": skill_name, "status": "success" if success else "failure"})
    collector.histogram("skill.duration", duration, tags={"skill": skill_name})


def record_event_processing(event_type: str, duration: float) -> None:
    """记录事件处理"""
    collector = get_collector()
    collector.histogram("event.processing_time", duration, tags={"type": event_type})


# ========== 全局实例 ==========

_global_collector: Optional[TelemetryCollector] = None


def get_collector() -> TelemetryCollector:
    """获取全局收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = TelemetryCollector()
    return _global_collector
