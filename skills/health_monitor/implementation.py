#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from typing import Any, Dict

import psutil

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """健康监控技能处理器"""

    def __init__(self):
        self.name = "health_monitor"

    async def check_health(self) -> Dict[str, Any]:
        """
        执行健康检查

        返回:
            {"success": bool, "data": {"cpu": float, "memory": float, "disk": float, "status": str}, "error": str or None}
        """
        try:
            loop = asyncio.get_event_loop()
            cpu = await loop.run_in_executor(None, lambda: psutil.cpu_percent(interval=0))
            memory = await loop.run_in_executor(None, lambda: psutil.virtual_memory().percent)
            disk = await loop.run_in_executor(None, lambda: psutil.disk_usage('/').percent)

            status = "healthy" if all(v < 80 for v in [cpu, memory, disk]) else "degraded"

            # 发布 CloudEvents 格式事件
            bus = get_event_bus()
            await bus.publish(f"health.{status}", {
                "cpu": cpu, "memory": memory, "disk": disk,
            }, source="health_monitor")

            return {
                "success": True,
                "data": {"cpu": cpu, "memory": memory, "disk": disk, "status": status},
                "error": None,
            }
        except Exception as e:
            logger.error(f"健康检查失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}
