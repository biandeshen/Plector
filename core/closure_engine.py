import logging
import time

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
            await self._execute_loop(self.loops[loop_id], payload, loop_id)

        return handler

    async def _execute_loop(self, loop_def, payload, loop_id: str = "unknown"):
        current_node = loop_def["entry"]
        context = {
            "payload": payload.get("data", {}) if isinstance(payload, dict) and "data" in payload else payload,
            "last_result": None,
        }
        steps: list[dict] = []
        errors: list[dict] = []
        start_time = time.perf_counter()

        try:
            for _ in range(loop_def.get("max_iterations", 10)):
                node = loop_def["nodes"][current_node]
                if node["type"] == "skill":
                    current_node = await self._execute_skill_node(node, current_node, context, steps, errors)
                    if not current_node:
                        break
                elif node["type"] == "condition":
                    last_result = context.get("last_result") or {}
                    for key in node["transitions"]:
                        if key in last_result:
                            current_node = node["transitions"][key]
                            break
                    else:
                        current_node = next(iter(node["transitions"].values()))
                    if not current_node:
                        break
                elif node["type"] == "end":
                    break
        except Exception as e:
            errors.append({"node": current_node, "error": str(e)})

        duration_ms = (time.perf_counter() - start_time) * 1000
        success = len(errors) == 0

        if success:
            await self.event_bus.publish(
                "closure_loop.completed",
                {"loop_id": loop_id, "steps": steps, "duration_ms": duration_ms, "result": context.get("last_result")},
                source="closure_engine",
            )
        else:
            await self.event_bus.publish(
                "closure_loop.failed",
                {"loop_id": loop_id, "steps": steps, "errors": errors, "duration_ms": duration_ms},
                source="closure_engine",
            )

    async def _execute_skill_node(self, node, current_node, context, steps, errors):
        params_from = node.get("params_from", "last_result")
        if params_from == "payload" or context["last_result"] is None:
            params = context.get("payload", {})
        else:
            params = context.get("last_result", {})
        result = await self.skill_handler.execute(node["skill"], node["method"], params)
        context["last_result"] = result
        success = isinstance(result, dict) and result.get("success", True)
        steps.append({"node": current_node, "skill": node["skill"], "method": node["method"], "success": success})
        if not success:
            errors.append(
                {
                    "node": current_node,
                    "error": str(result.get("error", "unknown")) if isinstance(result, dict) else "unknown",
                }
            )
        return node.get("next")
