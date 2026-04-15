"""LLM Client 性能基准测试"""
import pytest
import time
import asyncio
from typing import List


class MockLLMClient:
    """模拟 LLM 客户端"""

    def __init__(self, latency_ms: float = 100):
        self.latency_ms = latency_ms
        self.call_count = 0

    def complete(self, prompt: str) -> str:
        self.call_count += 1
        time.sleep(self.latency_ms / 1000)
        return f"Response to: {prompt[:20]}..."

    async def acomplete(self, prompt: str) -> str:
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return f"Async Response to: {prompt[:20]}..."


def measure_llm_throughput(client: MockLLMClient, count: int) -> float:
    """测量 LLM 客户端吞吐量"""
    start = time.perf_counter()
    for _ in range(count):
        client.complete("test prompt")
    end = time.perf_counter()
    return count / (end - start)


class TestLLMClientBenchmark:
    """LLM Client 基准测试套件"""

    @pytest.mark.benchmark
    def test_llm_client_throughput(self):
        """LLM 客户端吞吐量基准"""
        client = MockLLMClient(latency_ms=50)
        throughput = measure_llm_throughput(client, 20)

        print(f"\nLLM Throughput: {throughput:.1f} requests/sec")
        assert throughput > 10, f"Throughput too low: {throughput:.1f}/s"

    @pytest.mark.benchmark
    def test_llm_client_latency(self):
        """LLM 响应延迟基准"""
        client = MockLLMClient(latency_ms=100)
        latencies = []

        for _ in range(10):
            start = time.perf_counter()
            client.complete("test")
            latencies.append((time.perf_counter() - start) * 1000)

        avg = sum(latencies) / len(latencies)
        print(f"\nAvg LLM Latency: {avg:.1f}ms")
        assert avg < 200, f"Latency too high: {avg:.1f}ms"
