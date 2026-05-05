import logging
from collections import defaultdict
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


class Color(Enum):
    WHITE = auto()  # 未访问
    GRAY = auto()  # 当前路径中
    BLACK = auto()  # 已完成探索


class Governance:
    def __init__(self, skill_registry):
        self.registry = skill_registry
        self.health_scores: dict[str, float] = defaultdict(float)
        self.eliminations: list[dict[str, Any]] = []

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float) -> None:
        old = self.health_scores.get(skill_name, 1.0)
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        new = 0.7 * success_factor + 0.3 * time_factor
        self.health_scores[skill_name] = 0.9 * old + 0.1 * new

    def check_dependencies(self) -> list[list[str]]:
        graph: dict[str, list[str]] = {}
        for name, info in self.registry.skills.items():
            graph[name] = info["meta"].get("dependencies", [])
        return self._detect_cycles(graph)

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """3-color DFS 循环检测，返回所有发现的循环路径。"""
        cycles: list[list[str]] = []
        color: dict[str, Color] = defaultdict(lambda: Color.WHITE)
        stack: list[str] = []

        def dfs(node: str) -> None:
            if node not in graph:
                return
            if color[node] == Color.GRAY:
                cycle_start = stack.index(node)
                cycles.append([*stack[cycle_start:], node])
                return
            if color[node] == Color.BLACK:
                return
            color[node] = Color.GRAY
            stack.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in graph:
                    logger.warning("技能 '%s' 依赖未知技能 '%s'，已跳过", node, neighbor)
                    continue
                dfs(neighbor)
            stack.pop()
            color[node] = Color.BLACK

        for node in graph:
            dfs(node)
        return cycles

    def auto_eliminate(self) -> list[str]:
        """淘汰健康分低于 0.4 的技能并记录事件。

        阈值 0.4 的设定依据：经过 5 次连续失败（success=0, duration>>10s）
        后 EMA 约降至 0.3-0.4 区间，低于此值表示技能持续不可用。
        """
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
            if name in self.registry.skills:
                del self.registry.skills[name]
                logger.info("技能 '%s' 已淘汰（健康分 %.3f）", name, self.health_scores.get(name, 0.0))
        return to_eliminate
