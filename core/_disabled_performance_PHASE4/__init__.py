# -*- coding: utf-8 -*-
"""
Performance 模块
"""
from .profiler import Profiler, ProfileResult, ProfilerStats, get_profiler, profile

__all__ = [
    "Profiler",
    "ProfileResult",
    "ProfilerStats",
    "get_profiler",
    "profile",
]
