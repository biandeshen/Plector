"""Agent Loop 性能基准测试"""
import pytest
import time
from typing import List


def simulate_agent_loop(iterations: int) -> List[float]:
    """模拟 Agent Loop 执行并返回延迟列表"""
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        # 模拟一个简单的 agent cycle
        _ = {"state": "process", "result": None}
        _ = {"state": "decide", "action": "next"}
        _ = {"state": "execute", "done": True}
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms
    return latencies


class TestAgentLoopBenchmark:
    """Agent Loop 基准测试套件"""

    @pytest.mark.benchmark
    def test_agent_loop_single_cycle(self, benchmark_config):
        """单次循环延迟基准"""
        latencies = simulate_agent_loop(1)
        p50 = latencies[0]
        assert p50 < 100, f"Single cycle too slow: {p50:.2f}ms"

    @pytest.mark.benchmark
    def test_agent_loop_100_iterations(self, benchmark_config):
        """100 次迭代性能基准"""
        latencies = simulate_agent_loop(100)
        latencies.sort()

        p50 = latencies[49]
        p95 = latencies[94]
        p99 = latencies[98]
        mean = sum(latencies) / len(latencies)

        results = {"p50": p50, "p95": p95, "p99": p99, "mean": mean}
        print(f"\nAgent Loop Latencies: {results}")

        assert p99 < 50, f"P99 latency too high: {p99:.2f}ms"
