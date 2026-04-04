#!/usr/bin/env python3
"""
错误知识技能 - 记录并分类错误

功能：
    1. 存储错误到本地知识库
    2. 分类错误类型
    3. 发布错误事件

Author: Plector
Version: 1.0.0
Created: 2026-04-04
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class SkillHandler:
    """错误知识技能处理器"""

    def __init__(self):
        self.name = "error_knowledge"
        self.errors_dir = Path("data/errors")
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        # ✅ 审查修复：注册事件订阅
        bus = get_event_bus()
        bus.subscribe("test.failed", self._on_test_failed)
        bus.subscribe("skill.failed", self._on_skill_failed)

    async def _on_test_failed(self, event: dict):
        """处理 test.failed 事件（CloudEvents 格式）"""
        data = event.get("data", {})
        error = data.get("error", "unknown error")
        await self.store_error(error=error)

    async def _on_skill_failed(self, event: dict):
        """处理 skill.failed 事件（CloudEvents 格式）"""
        data = event.get("data", {})
        error = data.get("error", "unknown error")
        await self.store_error(error=error)

    async def store_error(self, error: str) -> dict[str, Any]:
        """
        存储错误信息

        参数:
            error: 错误描述

        返回:
            {"success": bool, "data": {"error_id": str}, "error": str or None}
        """
        try:
            error_id = str(uuid.uuid4())[:8]
            classified = self._classify(error)
            record = {
                "id": error_id,
                "error": error,
                "timestamp": datetime.now().isoformat(),
                "classified": classified,
            }

            file_path = self.errors_dir / f"{error_id}.json"
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)

            # 发布 CloudEvents 格式事件
            bus = get_event_bus()
            await bus.publish("error.stored", {"error_id": error_id, "error": error}, source="error_knowledge")

            return {"success": True, "data": {"error_id": error_id}, "error": None}
        except Exception as e:
            logger.error(f"存储错误失败: {e}", exc_info=True)
            return {"success": False, "data": None, "error": str(e)}

    async def classify_error(self, error: str) -> dict[str, Any]:
        """
        分类错误类型

        参数:
            error: 错误描述

        返回:
            {"success": bool, "data": {"category": str, "confidence": float}, "error": str or None}
        """
        try:
            classified = self._classify(error)

            bus = get_event_bus()
            await bus.publish("error.classified", classified, source="error_knowledge")

            return {"success": True, "data": classified, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _classify(self, error: str) -> dict[str, Any]:
        """内部分类逻辑"""
        error_lower = error.lower()
        if "syntax" in error_lower:
            return {"category": "syntax_error", "confidence": 0.9}
        elif "timeout" in error_lower:
            return {"category": "timeout", "confidence": 0.8}
        elif "permission" in error_lower:
            return {"category": "permission", "confidence": 0.8}
        elif "connection" in error_lower:
            return {"category": "connection", "confidence": 0.7}
        else:
            return {"category": "unknown", "confidence": 0.3}
