import logging

import yaml

from .event_bus import get_event_bus

logger = logging.getLogger(__name__)


class ClosureEngine:
    def __init__(self, skill_handler, config_path: str = "config/closed_loops.yaml"):
        self.skill_handler = skill_handler
        try:
            with open(config_path, encoding="utf-8") as f:
                self.loops = yaml.safe_load(f) or {}
        except (FileNotFoundError, yaml.YAMLError, PermissionError) as e:
            logger.warning(f"闭循环配置加载失败: {e}，使用空配置")
            self.loops = {}
        self.event_bus = get_event_bus()
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        for loop_id, loop_def in self.loops.items():
            for event in loop_def.get("trigger_on", []):
                self.event_bus.subscribe(event, self._create_handler(loop_id))

    def _create_handler(self, loop_id):
        async def handler(payload):
            await self._execute_loop(self.loops[loop_id], payload)

        return handler

    async def _execute_loop(self, loop_def, payload):
        current_node = loop_def["entry"]
        # CloudEvents 事件格式: payload 包含 specversion, id, source, type, time, data
        # 技能方法只需要 data 字段
        context = {
            "payload": payload.get("data", {}) if isinstance(payload, dict) and "data" in payload else payload,
            "last_result": None,
        }
        for _ in range(loop_def.get("max_iterations", 10)):
            node = loop_def["nodes"][current_node]
            if node["type"] == "skill":
                # Determine params: use payload (first call) or last_result (chained)
                params_from = node.get("params_from", "last_result")
                if params_from == "payload" or context["last_result"] is None:
                    params = context.get("payload", {})
                else:
                    params = context.get("last_result", {})
                result = await self.skill_handler.execute(node["skill"], node["method"], params)
                context["last_result"] = result
                current_node = node.get("next")
                if not current_node:
                    break
            elif node["type"] == "condition":
                for key in node["transitions"]:
                    if key in context.get("last_result", {}):
                        current_node = node["transitions"][key]
                        break
                else:
                    current_node = next(iter(node["transitions"].values()))
                if not current_node:
                    break
            elif node["type"] == "end":
                break
