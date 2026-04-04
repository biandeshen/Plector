import pytest
from core.skill_registry import SkillRegistry


def test_scan_empty():
    r = SkillRegistry(skills_dir="nonexistent")
    r.scan()
    assert len(r.skills) == 0


def test_get_skill():
    r = SkillRegistry()
    assert r.get_skill("nonexistent") is None
