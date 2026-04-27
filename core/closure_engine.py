import yaml

from .event_bus_v2 import get_event_bus_v2 as get_event_bus


class ClosureEngine:
    def __init__(self, skill_handler, config_path: str = "config/closed_loops.yaml"):
        self.skill_handler = skill_handler
        with open(config_path, encoding="utf-8") as f:
            self.loops = yaml.safe_load(f)
        self.event_bus = get_event_bus()
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        for loop_id, loop_def in self.loops.items():
            for event in loop_def.get("trigger_on", []):
                self.event_bus.subscribe(event, self._create_handler(loop_id))

    def _create_handler(self, loop_id):
        async def handler(payload):
            await self._execute_loop(loop_id, payload)

        return handler

    async def _execute_loop(self, loop_id, payload):
        # 获取 loop 定义
        loop_def = self.loops.get(loop_id)
        if not loop_def:
            await self.event_bus.publish(
                "closure_loop.failed",
                {"loop_id": loop_id, "error": f"Unknown loop_id: {loop_id}"},
                source="closure_engine",
            )
            return

        # CloudEvents 事件格式: payload 包含 specversion, id, source, type, time, data
        # 技能方法只需要 data 字段
        context = {
            "payload": payload.get("data", {}) if isinstance(payload, dict) and "data" in payload else payload,
            "last_result": None,
        }
        try:
            last_result = await self._execute_loop_nodes(loop_def, context)
            # 发布完成事件
            await self.event_bus.publish(
                "closure_loop.completed",
                {"loop_id": loop_id, "result": last_result},
                source="closure_engine",
            )
        except Exception as e:
            # 发布失败事件
            await self.event_bus.publish(
                "closure_loop.failed", {"loop_id": loop_id, "error": str(e)}, source="closure_engine"
            )

    async def _execute_loop_nodes(self, loop_def, context):
        """执行闭环节点"""
        current_node = loop_def["entry"]
        for _ in range(loop_def.get("max_iterations", 10)):
            node = loop_def["nodes"][current_node]
            if node["type"] == "skill":
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
        return context["last_result"]
