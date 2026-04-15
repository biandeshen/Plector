import pytest
from core.skill_registry import SkillRegistry


def test_scan_empty():
    r = SkillRegistry(skills_dir="nonexistent")
    r.scan()
    assert len(r.skills) == 0


def test_get_skill():
    r = SkillRegistry()
    assert r.get_skill("nonexistent") is None


def test_invalidate_unknown():
    r = SkillRegistry()
    r.invalidate("nonexistent")  # 不抛异常


def test_invalidate_all():
    r = SkillRegistry()
    r.invalidate_all()  # 不抛异常


def test_reload_skill_unknown():
    r = SkillRegistry()
    assert r.reload_skill("nonexistent") is False


def test_register_mcp_tool():
    r = SkillRegistry()
    r.register_mcp_tool("test_server", "test_tool", "desc", {"type": "object"})
    assert "mcp_test_server_test_tool" in r.mcp_tools
    tool = r.mcp_tools["mcp_test_server_test_tool"]
    assert tool["original_name"] == "test_tool"
    assert tool["server"] == "test_server"


def test_get_all_tools():
    r = SkillRegistry()
    r.register_mcp_tool("s", "t", "d", {"type": "object"})
    tools = r.get_all_tools()
    assert any(t["name"] == "mcp_s_t" and t["type"] == "mcp" for t in tools)
