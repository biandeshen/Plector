import json
from pathlib import Path
from typing import Dict, Optional

class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, dict] = {}

    def scan(self):
        if not self.skills_dir.exists():
            return
        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            json_file = skill_path / "skill.json"
            if json_file.exists():
                with open(json_file, encoding="utf-8") as f:
                    meta = json.load(f)
                self.skills[meta["name"]] = {
                    "path": skill_path,
                    "meta": meta,
                    "module": None
                }

    def get_skill(self, name: str) -> Optional[dict]:
        return self.skills.get(name)
