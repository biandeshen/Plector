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
        return "\n\n".join(parts)

    def _get_skills_description(self) -> str:
        lines = []
        for name, info in self.skill_registry.skills.items():
            lines.append(f"- {name}: {info['meta']['description']}")
        return "\n".join(lines)
