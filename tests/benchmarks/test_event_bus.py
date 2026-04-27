"""Event Bus 性能基准测试"""
import pytest
import time
from typing import List
import asyncio


class MockEventBus:
    """模拟事件总线"""

    def __init__(self):
        self.handlers = {}
        self.event_count = 0

    def subscribe(self, event_type: str, handler):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def publish(self, event_type: str, data: dict):
        self.event_count += 1
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(data)

    def clear(self):
        self.handlers = {}
        self.event_count = 0


def measure_event_bus_throughput(event_count: int) -> float:
    """测量事件总线吞吐量，返回每秒处理事件数"""
    bus = MockEventBus()

    def handler(data):
        pass

    bus.subscribe("test_event", handler)

    start = time.perf_counter()
    for i in range(event_count):
        bus.publish("test_event", {"id": i})
    end = time.perf_counter()

    duration = end - start
    return event_count / duration


class TestEventBusBenchmark:
    """Event Bus 基准测试套件"""

    @pytest.mark.benchmark
    def test_event_bus_throughput(self):
        """事件总线吞吐量基准"""
        events_per_sec = measure_event_bus_throughput(10000)
        print(f"\nEvent Bus: {events_per_sec:.0f} events/sec")

        assert events_per_sec > 10000, f"Throughput too low: {events_per_sec:.0f}/s"

    @pytest.mark.benchmark
    def test_event_bus_latency(self):
        """事件处理延迟基准"""
        bus = MockEventBus()
        latencies = []

        for _ in range(100):
            start = time.perf_counter()
            bus.publish("latency_test", {"index": _})
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAvg Event Latency: {avg_latency:.3f}ms")

        assert avg_latency < 1.0, f"Latency too high: {avg_latency:.3f}ms"
