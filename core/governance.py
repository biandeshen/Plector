from collections import defaultdict
from typing import Any


class Governance:
    def __init__(self, skill_registry):
        self.registry = skill_registry
        self.health_scores: dict[str, float] = defaultdict(float)
        self.eliminations: list[dict[str, Any]] = []

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float):
        old = self.health_scores.get(skill_name, 1.0)
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        new = 0.7 * success_factor + 0.3 * time_factor
        self.health_scores[skill_name] = 0.9 * old + 0.1 * new

    def check_dependencies(self):
        graph: dict[str, list[str]] = {}
        for name, info in self.registry.skills.items():
            graph[name] = info["meta"].get("dependencies", [])
        return self._detect_cycles(graph)

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """DFS 循环检测，返回所有发现的循环路径。"""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: list[str] = []

        def dfs(node: str):
            if node in stack:
                cycle_start = stack.index(node)
                cycles.append([*stack[cycle_start:], node])
                return
            if node in visited:
                return
            visited.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                if neighbor in graph:
                    dfs(neighbor)
            stack.pop()

        for node in graph:
            dfs(node)
        return cycles

    def auto_eliminate(self):
        """淘汰健康分低于 0.4 的技能，记录淘汰事件。"""
        to_eliminate = [name for name, score in self.health_scores.items() if score < 0.4]
        for name in to_eliminate:
            self.eliminations.append(
                {
                    "skill": name,
                    "score": self.health_scores[name],
                    "reason": "health_score_below_threshold",
                }
            )
            del self.health_scores[name]
        return to_eliminate
