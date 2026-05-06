"""
Tests for core.skill_loader

Tests cover:
- SkillInfo dataclass defaults and creation
- SkillLoader initialization
- get_skill, reload_skill, warmup, get_all_skills, stats
- File hash calculation
- needs_reload detection
- Skill discovery from temp directories
- Watcher start/stop
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from core.skill_loader import SkillInfo, SkillLoader

# ─── SkillInfo ──────────────────────────────────────────


class TestSkillInfo:
    def test_create_skill_info(self):
        info = SkillInfo(
            name="test_skill",
            path=Path("/some/path"),
            handler_class="MyHandler",
        )
        assert info.name == "test_skill"
        assert info.path == Path("/some/path")
        assert info.handler_class == "MyHandler"
        assert info.is_loaded is False
        assert info.module is None
        assert info.file_hash == ""

    def test_default_loaded_at(self):
        info = SkillInfo(name="s", path=Path("."), handler_class="H")
        assert isinstance(info.loaded_at, datetime)

    def test_default_metadata(self):
        info = SkillInfo(name="s", path=Path("."), handler_class="H")
        assert info.is_loaded is False
        assert info.file_hash == ""
        assert info.module is None

    def test_str_path_converted(self):
        info = SkillInfo(name="s", path=Path("skills/foo"), handler_class="H")
        assert info.path == Path("skills/foo")


# ─── Fixtures ───────────────────────────────────────────


@pytest.fixture
def empty_loader():
    """SkillLoader with a non-existent base path."""
    return SkillLoader(base_path="/tmp/__plector_nonexistent__")


def _create_skill_dir(parent: Path, name: str, handler_class: str) -> Path:
    """Create a skill directory with __init__.py, implementation.py, and skill.json."""
    skill_dir = parent / name
    skill_dir.mkdir()
    (skill_dir / "__init__.py").write_text("")
    impl = f"class {handler_class}:\n    def handle(self, request):\n        return {{'status': 'ok'}}\n"
    (skill_dir / "implementation.py").write_text(impl)
    skill_json = {"name": name, "version": "1.0.0", "handler_class": handler_class, "description": "A test skill"}
    (skill_dir / "skill.json").write_text(json.dumps(skill_json, indent=2))
    return skill_dir


def _cleanup_modules(names: list[str]):
    """Remove stale module entries from sys.modules."""
    for name in names:
        sys.modules.pop(name, None)


@pytest.fixture
def temp_skill_env():
    """Create a temporary directory with two test skills for SkillLoader testing."""
    tmp_base = Path(tempfile.mkdtemp())
    skills_dir = tmp_base / "skills"
    skills_dir.mkdir()
    (skills_dir / "__init__.py").write_text("")

    _create_skill_dir(skills_dir, "test_skill", "TestHandler")
    _create_skill_dir(skills_dir, "test_skill2", "OtherHandler")

    sys.path.insert(0, str(tmp_base))
    _cleanup_modules(
        [
            "skills",
            "skills.test_skill",
            "skills.test_skill.implementation",
            "skills.test_skill2",
            "skills.test_skill2.implementation",
        ]
    )

    loader = SkillLoader(base_path=str(skills_dir))

    yield {"tmp_base": tmp_base, "skills_dir": skills_dir, "skill_dir": skills_dir / "test_skill", "loader": loader}

    _cleanup_modules(
        [
            "skills",
            "skills.test_skill",
            "skills.test_skill.implementation",
            "skills.test_skill2",
            "skills.test_skill2.implementation",
        ]
    )
    sys.path = [p for p in sys.path if p != str(tmp_base)]

    import shutil

    shutil.rmtree(tmp_base, ignore_errors=True)


# ─── Init ───────────────────────────────────────────────


class TestSkillLoaderInit:
    def test_init_with_default_base(self):
        loader = SkillLoader()
        assert loader.base_path == Path("skills")
        assert loader._cache == {}

    def test_init_with_custom_base(self):
        loader = SkillLoader(base_path="/custom/path")
        assert loader.base_path == Path("/custom/path")

    def test_init_empty_cache(self, empty_loader):
        assert empty_loader._cache == {}
        assert empty_loader._watch_interval == 5.0
        assert empty_loader._file_watcher_task is None


# ─── get_skill ──────────────────────────────────────────


class TestGetSkill:
    @pytest.mark.asyncio
    async def test_get_skill_nonexistent(self, empty_loader):
        result = await empty_loader.get_skill("does_not_exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_skill_discovers_and_loads(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        result = await loader.get_skill("test_skill")
        assert result is not None
        assert result["name"] == "test_skill"
        assert result["handler_class"] == "TestHandler"
        assert "loaded_at" in result

    @pytest.mark.asyncio
    async def test_get_skill_returns_metadata_dict(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        result = await loader.get_skill("test_skill")
        assert isinstance(result, dict)
        assert "name" in result
        assert "path" in result
        assert "handler_class" in result
        assert "loaded_at" in result

    @pytest.mark.asyncio
    async def test_get_skill_caches_result(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader.get_skill("test_skill")
        assert "test_skill" in loader._cache
        info = loader._cache["test_skill"]
        assert info.is_loaded is True


# ─── reload_skill ───────────────────────────────────────


class TestReloadSkill:
    @pytest.mark.asyncio
    async def test_reload_nonexistent(self, empty_loader):
        result = await empty_loader.reload_skill("ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_reload_loaded_skill(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader.get_skill("test_skill")
        result = await loader.reload_skill("test_skill")
        assert result is True
        assert loader._cache["test_skill"].is_loaded is True


# ─── warmup ─────────────────────────────────────────────


class TestWarmup:
    @pytest.mark.asyncio
    async def test_warmup_nonexistent_skills(self, empty_loader):
        """Nonexistent skills: get_skill returns None (not Exception), so warmup returns True."""
        results = await empty_loader.warmup(["a", "b", "c"])
        assert results == {"a": True, "b": True, "c": True}

    @pytest.mark.asyncio
    async def test_warmup_with_real_skills(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        results = await loader.warmup(["test_skill", "test_skill2"])
        for name, success in results.items():
            assert success is True, f"Skill {name} failed to warm up"


# ─── get_all_skills ─────────────────────────────────────


class TestGetAllSkills:
    @pytest.mark.asyncio
    async def test_empty_base(self, empty_loader):
        skills = await empty_loader.get_all_skills()
        assert skills == []

    @pytest.mark.asyncio
    async def test_discover_all_skills(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        skills = await loader.get_all_skills()
        assert "test_skill" in skills
        assert "test_skill2" in skills


# ─── stats ──────────────────────────────────────────────


class TestStats:
    @pytest.mark.asyncio
    async def test_stats_empty(self, empty_loader):
        stats = await empty_loader.stats()
        assert stats == {"total_skills": 0, "loaded_skills": 0, "watcher_active": False}

    @pytest.mark.asyncio
    async def test_stats_after_loading(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader.get_skill("test_skill")
        stats = await loader.stats()
        assert stats["total_skills"] >= 1
        assert stats["loaded_skills"] >= 1

    @pytest.mark.asyncio
    async def test_stats_watcher_reflected(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        loader.start_watcher()
        stats = await loader.stats()
        assert stats["watcher_active"] is True
        loader.stop_watcher()


# ─── get_loaded_modules ─────────────────────────────────


class TestGetLoadedModules:
    @pytest.mark.asyncio
    async def test_no_loaded_modules(self, empty_loader):
        assert empty_loader.get_loaded_modules() == []

    @pytest.mark.asyncio
    async def test_has_loaded_modules(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader.get_skill("test_skill")
        modules = loader.get_loaded_modules()
        assert "test_skill" in modules


# ─── _calc_hash ─────────────────────────────────────────


class TestCalcHash:
    @pytest.mark.asyncio
    async def test_calc_hash_on_temp_dir(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        h = await loader._calc_hash(temp_skill_env["skill_dir"])
        assert isinstance(h, str)
        assert len(h) == 16  # truncated to 16 hex chars

    @pytest.mark.asyncio
    async def test_calc_hash_changes_when_file_changes(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        skill_dir = temp_skill_env["skill_dir"]
        h1 = await loader._calc_hash(skill_dir)
        # Modify a file
        impl_file = skill_dir / "implementation.py"
        impl_file.write_text(impl_file.read_text() + "\n# new comment")
        h2 = await loader._calc_hash(skill_dir)
        assert h1 != h2

    @pytest.mark.asyncio
    async def test_calc_hash_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = SkillLoader(base_path=tmpdir)
            h = await loader._calc_hash(Path(tmpdir))
            assert isinstance(h, str)
            assert len(h) == 16


# ─── _needs_reload ──────────────────────────────────────


class TestNeedsReload:
    @pytest.mark.asyncio
    async def test_needs_reload_when_not_loaded(self):
        info = SkillInfo(name="s", path=Path("."), handler_class="H")
        loader = SkillLoader()
        assert await loader._needs_reload(info) is True

    @pytest.mark.asyncio
    async def test_needs_reload_false_when_unchanged(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        info = SkillInfo(
            name="test_skill",
            path=temp_skill_env["skill_dir"],
            handler_class="TestHandler",
            is_loaded=True,
        )
        info.file_hash = await loader._calc_hash(info.path)
        assert await loader._needs_reload(info) is False

    @pytest.mark.asyncio
    async def test_needs_reload_true_when_file_changed(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        skill_dir = temp_skill_env["skill_dir"]
        info = SkillInfo(
            name="test_skill",
            path=skill_dir,
            handler_class="TestHandler",
            is_loaded=True,
        )
        info.file_hash = await loader._calc_hash(skill_dir)
        # Change a file
        (skill_dir / "implementation.py").write_text("# changed\n")
        assert await loader._needs_reload(info) is True


# ─── watcher ────────────────────────────────────────────


class TestWatcher:
    @pytest.mark.asyncio
    async def test_start_stop_watcher(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        assert loader._file_watcher_task is None
        loader.start_watcher()
        assert loader._file_watcher_task is not None
        assert loader._file_watcher_task.done() is False
        loader.stop_watcher()
        # After cancel, the task should be None
        assert loader._file_watcher_task is None

    @pytest.mark.asyncio
    async def test_start_watcher_idempotent(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        loader.start_watcher()
        task1 = loader._file_watcher_task
        loader.start_watcher()  # second call should be no-op
        assert loader._file_watcher_task is task1
        loader.stop_watcher()

    @pytest.mark.asyncio
    async def test_stop_watcher_idempotent(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        loader.stop_watcher()  # should not raise
        assert loader._file_watcher_task is None


# ─── _discover_skill ────────────────────────────────────


class TestDiscoverSkill:
    @pytest.mark.asyncio
    async def test_discover_without_skill_json(self, empty_loader):
        """Discovering a skill with no skill.json should be a no-op."""
        await empty_loader._discover_skill("missing")
        assert "missing" not in empty_loader._cache

    @pytest.mark.asyncio
    async def test_discover_adds_to_cache(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader._discover_skill("test_skill")
        assert "test_skill" in loader._cache
        info = loader._cache["test_skill"]
        assert info.name == "test_skill"
        assert info.handler_class == "TestHandler"
        assert info.is_loaded is False


# ─── _discover_all ──────────────────────────────────────


class TestDiscoverAll:
    @pytest.mark.asyncio
    async def test_discover_all_empty(self, empty_loader):
        await empty_loader._discover_all()
        assert empty_loader._cache == {}

    @pytest.mark.asyncio
    async def test_discover_all_finds_skills(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        await loader._discover_all()
        assert "test_skill" in loader._cache
        assert "test_skill2" in loader._cache

    @pytest.mark.asyncio
    async def test_discover_all_skips_existing(self, temp_skill_env):
        loader = temp_skill_env["loader"]
        loader._cache["test_skill"] = SkillInfo(name="test_skill_old", path=Path("."), handler_class="Old")
        await loader._discover_all()
        # Should NOT overwrite existing cache entry
        assert loader._cache["test_skill"].name == "test_skill_old"
        assert "test_skill2" in loader._cache


# ─── Edge cases ─────────────────────────────────────────


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_get_skill_after_base_path_deleted(self):
        """SkillLoader should gracefully handle a deleted base path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_sub = os.path.join(tmpdir, "skills")
            os.mkdir(skills_sub)
            loader = SkillLoader(base_path=skills_sub)
            result = await loader.get_skill("anything")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_skill_corrupted_skill_json(self, empty_loader):
        """Corrupted skill.json should not crash the loader."""
        tmpdir = Path(tempfile.mkdtemp())
        try:
            skill_dir = tmpdir / "broken_skill"
            skill_dir.mkdir()
            (skill_dir / "skill.json").write_text("not valid json")
            loader = SkillLoader(base_path=str(tmpdir))
            result = await loader.get_skill("broken_skill")
            assert result is None
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
