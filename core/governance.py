import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class Governance:
    def __init__(self, skill_registry, event_bus=None):
        self.registry = skill_registry
        self.event_bus = event_bus
        self.health_scores = defaultdict(float)

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float):
        old = self.health_scores.get(skill_name, 1.0)
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        new = 0.7 * success_factor + 0.3 * time_factor
        self.health_scores[skill_name] = 0.9 * old + 0.1 * new

    def check_dependencies(self):
        graph = {}
        for name, info in self.registry.skills.items():
            graph[name] = info["meta"].get("dependencies", [])
        cycles = self._detect_cycles(graph)
        return cycles

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """DFS 检测依赖环"""
        visited = set()
        path = []
        cycles = []

        def dfs(node):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for dep in graph.get(node, []):
                dfs(dep)
            path.pop()

        for node in graph:
            dfs(node)
        return cycles

    async def auto_eliminate(self):
        """淘汰健康分过低的技能，发布事件"""
        for name, score in list(self.health_scores.items()):
            if score < 0.6:
                logger.warning(f"技能 '{name}' 健康分过低 ({score:.2f})，建议淘汰")
                if self.event_bus:
                    await self.event_bus.publish(
                        "governance.eliminate",
                        {"skill": name, "score": score},
                        source="governance",
                    )
