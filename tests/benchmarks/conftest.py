"""Pytest 配置和 fixtures"""
import pytest
import time
from typing import Dict, Any


@pytest.fixture
def benchmark_config() -> Dict[str, Any]:
    """基准测试配置"""
    return {
        "iterations": 100,
        "warmup": 10,
        "timeout": 30.0,
    }


@pytest.fixture
def timing_context():
    """计时上下文管理器"""
    class TimingContext:
        def __init__(self):
            self.start = 0
            self.end = 0
            self.duration = 0

        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.duration = self.end - self.start

    return TimingContext()


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--benchmark", action="store_true", default=False,
        help="运行性能基准测试"
    )
