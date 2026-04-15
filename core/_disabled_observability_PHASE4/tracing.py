"""分布式追踪系统 - OpenTelemetry 风格"""
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """追踪 Span"""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "OK"

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })

    def end(self, status: str = "OK"):
        self.end_time = time.time()
        self.status = status

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
        }


class Tracer:
    """轻量级追踪器"""

    def __init__(self, service_name: str = "plector"):
        self.service_name = service_name
        self.spans: List[Span] = []

    def start_span(self, name: str, kind: SpanKind = SpanKind.INTERNAL,
                   parent_id: Optional[str] = None, **kwargs) -> Span:
        """启动新的 Span"""
        span = Span(
            name=name,
            trace_id=uuid.uuid4().hex[:16],
            span_id=uuid.uuid4().hex[:8],
            parent_id=parent_id,
            kind=kind,
        )
        for key, value in kwargs.items():
            span.set_attribute(key, value)
        return span

    def end_span(self, span: Span, status: str = "OK"):
        """结束 Span"""
        span.end(status)
        self.spans.append(span)

    def trace(self, name: str, kind: SpanKind = SpanKind.INTERNAL):
        """上下文管理器装饰器"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                span = self.start_span(name, kind)
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.status = "ERROR"
                    raise
                finally:
                    self.end_span(span)

            def sync_wrapper(*args, **kwargs):
                span = self.start_span(name, kind)
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("error", str(e))
                    span.status = "ERROR"
                    raise
                finally:
                    self.end_span(span)

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator

    def get_traces(self) -> List[Dict[str, Any]]:
        """获取所有追踪记录"""
        return [s.to_dict() for s in self.spans]

    def clear(self):
        """清空追踪记录"""
        self.spans.clear()


# 全局追踪器实例
_tracer = Tracer()


def get_tracer() -> Tracer:
    return _tracer
