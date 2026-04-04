from collections import defaultdict

class Governance:
    def __init__(self, skill_registry):
        self.registry = skill_registry
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

    def _detect_cycles(self, graph):
        # 简化实现：暂不检测
        return []

    def auto_eliminate(self):
        for name, score in self.health_scores.items():
            if score < 0.6:
                # 发布淘汰事件（可后续实现）
                pass
