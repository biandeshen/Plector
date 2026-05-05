from pathlib import Path

from core.context_builder import ContextBuilder
from core.skill_registry import SkillRegistry


def test_build_includes_profile_content(tmp_path):
    """build_system_prompt should read and include content from AGENTS.md / SOUL.md / USER.md."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "AGENTS.md").write_text("## Agent Identity\nYou are a helpful assistant.", encoding="utf-8")
    (profiles_dir / "SOUL.md").write_text("## Core Values\nPrefer clarity over cleverness.", encoding="utf-8")

    registry = SkillRegistry()
    builder = ContextBuilder(registry, profiles_dir=profiles_dir)
    result = builder.build_system_prompt()

    assert "## Agent Identity" in result
    assert "You are a helpful assistant." in result
    assert "## Core Values" in result
    assert "Prefer clarity over cleverness." in result


def test_build_handles_missing_profile_dir():
    """build_system_prompt should not crash when the profiles directory does not exist."""
    registry = SkillRegistry()
    builder = ContextBuilder(registry, profiles_dir=Path("/nonexistent/profiles/dir"))
    result = builder.build_system_prompt()

    # Must still contain the skill guide and tool usage guide sections
    assert "## 可用技能" in result
    assert "## 工具调用指南" in result
    assert "## 技能详细说明" in result


def test_build_with_skill_registry_info():
    """build_system_prompt should include skill names and descriptions from the registry."""
    registry = SkillRegistry()
    registry.skills = {
        "health_monitor": {
            "meta": {"name": "health_monitor", "description": "System health checking tool"},
        },
        "error_knowledge": {
            "meta": {"name": "error_knowledge", "description": "Error knowledge base management"},
        },
    }
    builder = ContextBuilder(registry, profiles_dir=Path("/nonexistent/profiles/dir"))
    result = builder.build_system_prompt()

    assert "health_monitor" in result
    assert "System health checking tool" in result
    assert "error_knowledge" in result
    assert "Error knowledge base management" in result
