"""
Governance Module - Skill health management and dependency cycles

Provides:
- Health score tracking based on multiple factors
- Cycle detection in skill dependencies
- Auto-elimination of unhealthy skills
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class SkillHealthRecord:
    """Detailed health record for a skill"""

    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0
    event_publish_count: int = 0
    exception_count: int = 0
    last_success_time: float = 0
    last_failure_time: float = 0
    in_cycle: bool = False
    cycle_count: int = 0


class Governance:
    """
    Governance manager for skill health and dependency management

    Health score is computed based on:
    - Execution success/failure rate
    - Response time
    - Event publication rate
    - Cycle detection status
    - Handler exception rates
    """

    HEALTH_WEIGHTS: ClassVar[dict[str, float]] = {
        "success_rate": 0.35,
        "response_time": 0.15,
        "event_rate": 0.20,
        "cycle_penalty": 0.20,
        "exception_penalty": 0.10,
    }

    def __init__(self, skill_registry, event_bus=None):
        self.registry = skill_registry
        self.event_bus = event_bus
        self.health_scores: dict[str, float] = defaultdict(float)
        self._health_records: dict[str, SkillHealthRecord] = defaultdict(SkillHealthRecord)
        self._cycle_cache: list[list[str]] = []
        self._last_cycle_check: float = 0
        self._cycle_check_interval: float = 60.0  # Check cycles every 60 seconds

    def update_health_score(self, skill_name: str, success: bool, duration_ms: float):
        """Update health score based on skill execution result"""
        record = self._health_records[skill_name]
        old_score = self.health_scores.get(skill_name, 1.0)

        # Update record
        if success:
            record.success_count += 1
            record.last_success_time = time.time()
        else:
            record.failure_count += 1
            record.last_failure_time = time.time()
        record.total_duration_ms += duration_ms

        # Compute new score based on success and duration
        success_factor = 1.0 if success else 0.0
        time_factor = max(0, 1 - (duration_ms / 10000))
        execution_score = 0.7 * success_factor + 0.3 * time_factor

        # Apply event rate and cycle factors
        total_executions = record.success_count + record.failure_count
        if total_executions > 0:
            event_rate = record.event_publish_count / total_executions
            exception_rate = record.exception_count / total_executions
        else:
            event_rate = 0.5
            exception_rate = 0.0

        # Cycle penalty
        cycle_factor = 0.0 if record.in_cycle else 1.0

        # Exception penalty
        exception_factor = max(0, 1.0 - exception_rate)

        # Compute composite score
        new_score = (
            self.HEALTH_WEIGHTS["success_rate"] * execution_score
            + self.HEALTH_WEIGHTS["response_time"] * time_factor
            + self.HEALTH_WEIGHTS["event_rate"] * event_rate
            + self.HEALTH_WEIGHTS["cycle_penalty"] * cycle_factor
            + self.HEALTH_WEIGHTS["exception_penalty"] * exception_factor
        )

        # EMA smoothing
        self.health_scores[skill_name] = 0.9 * old_score + 0.1 * new_score

    def record_event_published(self, skill_name: str):
        """Record that a skill published an event"""
        self._health_records[skill_name].event_publish_count += 1

    def record_exception(self, skill_name: str):
        """Record an exception from a skill handler"""
        self._health_records[skill_name].exception_count += 1

    def check_dependencies(self):
        """Check for dependency cycles in skill registry"""
        graph = {}
        for name, info in self.registry.skills.items():
            graph[name] = info["meta"].get("dependencies", [])

        cycles = self._detect_cycles(graph)

        # Update cycle status in health records
        skills_in_cycles = set()
        for cycle in cycles:
            for skill_name in cycle:
                skills_in_cycles.add(skill_name)

        for skill_name in self._health_records:
            record = self._health_records[skill_name]
            was_in_cycle = record.in_cycle
            record.in_cycle = skill_name in skills_in_cycles
            if record.in_cycle and not was_in_cycle:
                record.cycle_count += 1

        self._cycle_cache = cycles
        self._last_cycle_check = time.time()
        return cycles

    def get_cycle_status(self, skill_name: str) -> bool:
        """Check if a skill is currently in a dependency cycle"""
        # Check if we need to refresh cycle info
        if time.time() - self._last_cycle_check > self._cycle_check_interval:
            self.check_dependencies()
        return self._health_records[skill_name].in_cycle

    def get_health_score(self, skill_name: str) -> float:
        """Get current health score for a skill"""
        return self.health_scores.get(skill_name, 1.0)

    def get_health_record(self, skill_name: str) -> SkillHealthRecord:
        """Get detailed health record for a skill"""
        return self._health_records.get(skill_name, SkillHealthRecord())

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """
        DFS-based cycle detection in dependency graph

        Returns list of cycles, where each cycle is a list of skill names
        forming a circular dependency.
        """
        visited = set()
        rec_stack = set()
        path = []
        cycles = []

        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle - extract the cycle portion
                    cycle_start = path.index(neighbor)
                    cycle = [*path[cycle_start:], neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node)

        return cycles

    async def auto_eliminate(self, threshold: float = 0.5):
        """
        Eliminate skills with health scores below threshold

        Args:
            threshold: Health score threshold below which skills are eliminated

        Returns:
            List of eliminated skill names
        """
        eliminated = []

        # Check and update cycles if needed
        if time.time() - self._last_cycle_check > self._cycle_check_interval:
            self.check_dependencies()

        for name, score in list(self.health_scores.items()):
            record = self._health_records[name]

            # Skip if in cycle (cycles are handled separately)
            if record.in_cycle:
                logger.warning(f"技能 '{name}' 处于依赖环中 ({score:.2f})，建议检查")
                continue

            if score < threshold:
                logger.warning(f"技能 '{name}' 健康分过低 ({score:.2f})，建议淘汰")
                eliminated.append(name)

                if self.event_bus:
                    await self.event_bus.publish(
                        "governance.eliminate",
                        {"skill": name, "score": score, "reason": "low_health_score"},
                        source="governance",
                    )

        return eliminated

    def get_system_health(self) -> dict:
        """
        Get overall system health metrics

        Returns:
            Dictionary with system health information
        """
        total_skills = len(self.health_scores)
        if total_skills == 0:
            return {
                "status": "unknown",
                "total_skills": 0,
                "avg_health_score": 0,
                "skills_below_threshold": 0,
                "cycles_detected": 0,
                "total_exceptions": 0,
            }

        avg_score = sum(self.health_scores.values()) / total_skills
        skills_below = sum(1 for s in self.health_scores.values() if s < 0.5)

        all_exceptions = sum(r.exception_count for r in self._health_records.values())

        if avg_score >= 0.8 and skills_below == 0:
            status = "healthy"
        elif avg_score >= 0.6:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "total_skills": total_skills,
            "avg_health_score": round(avg_score, 3),
            "skills_below_threshold": skills_below,
            "cycles_detected": len(self._cycle_cache),
            "total_exceptions": all_exceptions,
        }
