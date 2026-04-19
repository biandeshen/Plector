#!/usr/bin/env python3
"""
健康监控技能 - 获取系统健康状态

功能：
    1. 获取 CPU/内存/磁盘使用率
    2. 判断系统健康状态
    3. 发布健康事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import asyncio
import logging
import os
import sys
from typing import Any

import psutil

from core.event_bus_v2 import get_event_bus_v2 as get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """健康监控技能处理器"""

    def __init__(self):
        self.name = "health_monitor"

    async def check_health(self, **kwargs: Any) -> dict[str, Any]:
        """
        执行健康检查

        参数:
            **kwargs: 忽略所有传入的参数（兼容闭包引擎调用）

        返回:
            {"success": bool, "data": {"cpu": float, "memory": float, "disk": float, "status": str}, "error": str or None}
        """
        # 忽略传入的参数，闭包引擎可能传递 payload 但此方法不需要
        _ = kwargs
        try:
            loop = asyncio.get_running_loop()
            # 跨平台磁盘路径：Linux/Mac 用 "/"，Windows 用系统盘
            disk_path = "/" if sys.platform != "win32" else os.environ.get("SYSTEMDRIVE", "C:\\")
            cpu, memory, disk = await asyncio.gather(
                loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0)),
                loop.run_in_executor(None, lambda: psutil.virtual_memory().percent),
                loop.run_in_executor(None, lambda: psutil.disk_usage(disk_path).percent),
            )

            status = "healthy" if all(v < 80 for v in [cpu, memory, disk]) else "degraded"

            # 只在异常状态发布事件，健康状态不需要广播
            if status == "degraded":
                bus = get_event_bus()
                await bus.publish(
                    "health.degraded",
                    {
                        "cpu": cpu,
                        "memory": memory,
                        "disk": disk,
                    },
                    source="health_monitor",
                )

            return {
                "success": True,
                "data": {"cpu": cpu, "memory": memory, "disk": disk, "status": status},
                "error": None,
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
