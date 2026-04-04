from pathlib import Path

from .skill_registry import SkillRegistry


class ContextBuilder:
    def __init__(self, skill_registry: SkillRegistry, profiles_dir: Path = Path("config/profiles")):
        self.skill_registry = skill_registry
        self.profiles_dir = profiles_dir

    def build_system_prompt(self) -> str:
        parts = []
        for filename in ["AGENTS.md", "SOUL.md", "USER.md"]:
            file_path = self.profiles_dir / filename
            if file_path.exists():
                parts.append(file_path.read_text(encoding="utf-8"))
        skills_desc = self._get_skills_description()
        parts.append(f"\n## 可用技能\n{skills_desc}")
        parts.append(self._get_tool_usage_guide())
        return "\n\n".join(parts)

    def _get_skills_description(self) -> str:
        lines = []
        for name, info in self.skill_registry.skills.items():
            lines.append(f"- {name}: {info['meta']['description']}")
        return "\n".join(lines)

    def _get_tool_usage_guide(self) -> str:
        """工具使用指南，强化 tool calling 提示"""
        return """

## 工具调用指南

**重要：当用户询问系统健康、CPU、内存、磁盘状态时，必须调用 `health_monitor.check_health` 工具！**

当用户报告错误时，必须调用 `error_knowledge.store_error` 工具！

**不要自己编造答案，必须调用工具获取真实数据。**

示例：
- 用户："系统健康吗" → 调用 health_monitor.check_health
- 用户："CPU 多少" → 调用 health_monitor.check_health
- 用户："报错了" → 调用 error_knowledge.store_error
"""
