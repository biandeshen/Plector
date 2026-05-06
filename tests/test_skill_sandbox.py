"""
Tests for core.skill_sandbox — skill execution isolation, path validation, security scanning.
"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest

from core.skill_sandbox import (
    SandboxConfig,
    SandboxMode,
    SkillSandbox,
    SkillSandboxFactory,
    create_isolated_sandbox,
    get_default_sandbox_config,
    get_sandbox,
)

# ─── Helper functions used in execute tests ────────────────────────


def sync_echo(*args, **kwargs):
    """Simple synchronous function returning its arguments."""
    return {"args": args, "kwargs": kwargs}


async def async_echo(*args, **kwargs):
    """Simple async function returning its arguments."""
    return {"args": args, "kwargs": kwargs}


# ─── SandboxConfig ─────────────────────────────────────────────────


class TestSandboxConfig:
    def test_defaults(self):
        cfg = SandboxConfig()
        assert cfg.mode == SandboxMode.RESTRICTED
        assert cfg.timeout_seconds == 30
        assert cfg.max_memory_mb == 256
        assert cfg.allowed_paths == []
        assert "/etc" in cfg.denied_paths
        assert cfg.enable_network is False

    def test_custom_values(self):
        cfg = SandboxConfig(mode=SandboxMode.UNRESTRICTED, timeout_seconds=5)
        assert cfg.mode == SandboxMode.UNRESTRICTED
        assert cfg.timeout_seconds == 5


# ─── SandboxMode enum ──────────────────────────────────────────────


class TestSandboxMode:
    def test_values(self):
        assert SandboxMode.RESTRICTED.value == "restricted"
        assert SandboxMode.STANDARD.value == "standard"
        assert SandboxMode.UNRESTRICTED.value == "unrestricted"


# ─── Path validation ───────────────────────────────────────────────


class TestValidatePath:
    def test_unrestricted_mode_bypasses(self):
        """UNRESTRICTED mode always returns valid."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.UNRESTRICTED))
        ok, msg = sandbox.validate_path("/etc/shadow", "read")
        assert ok is True
        assert msg == ""

    def test_restricted_denied_path(self):
        """RESTRICTED mode blocks denied paths."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED, denied_paths=["/etc"]))
        ok, msg = sandbox.validate_path("/etc/shadow", "read")
        assert ok is False
        assert "禁止目录" in msg

    def test_restricted_allowed_path_whitelist(self):
        """Path under allowed_paths is OK."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED, allowed_paths=["/tmp/work"]))
        ok, _msg = sandbox.validate_path("/tmp/work/data.txt", "read")
        assert ok is True

    def test_restricted_path_not_in_whitelist(self):
        """Path not under any allowed path is rejected."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED, allowed_paths=["/tmp/work"]))
        ok, msg = sandbox.validate_path("/other/file.txt", "read")
        assert ok is False
        assert "不在允许的目录内" in msg

    def test_standard_mode_blocks_outside_cwd_and_home(self, tmp_path):
        """STANDARD mode only permits cwd/home subdirectories."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.STANDARD))
        with (
            patch.object(Path, "cwd", return_value=tmp_path),
            patch.object(Path, "home", return_value=tmp_path / "home"),
        ):
            ok, _msg = sandbox.validate_path(str(tmp_path / "data" / "file.txt"), "read")
            assert ok is True

    def test_standard_mode_blocks_outside(self, tmp_path):
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.STANDARD))
        with (
            patch.object(Path, "cwd", return_value=tmp_path),
            patch.object(Path, "home", return_value=tmp_path / "home"),
        ):
            ok, _msg = sandbox.validate_path("/etc/outside", "read")
            assert ok is False

    def test_restricted_no_whitelist_default_cwd_or_home(self, tmp_path):
        """Without allowed_paths, default allows cwd and home."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED))
        with (
            patch.object(Path, "cwd", return_value=tmp_path),
            patch.object(Path, "home", return_value=tmp_path / "home"),
        ):
            ok, _msg = sandbox.validate_path(str(tmp_path / "valid.txt"), "read")
            assert ok is True

    def test_path_with_traversal_attempt(self):
        """Directory traversal via .. is caught."""
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED, allowed_paths=["/safe"]))
        ok, _msg = sandbox.validate_path("/safe/../etc/passwd", "read")
        assert ok is False

    def test_permission_error_handled(self):
        sandbox = SkillSandbox()
        with patch("pathlib.Path.resolve", side_effect=PermissionError("denied")):
            ok, msg = sandbox.validate_path("/restricted", "read")
            assert ok is False
            assert "没有权限" in msg

    def test_general_exception_handled(self):
        sandbox = SkillSandbox()
        with patch("pathlib.Path.resolve", side_effect=OSError("bad path")):
            ok, _msg = sandbox.validate_path("/bad", "read")
            assert ok is False


# ─── validate_skill (security scanning) ────────────────────────────


class TestValidateSkill:
    def test_clean_code(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("safe", "def greet(): return 'hello'")
        assert result["success"] is True
        assert result["data"]["warnings"] == []
        assert len(result["data"]["hash"]) == 16

    def test_detects_eval(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "eval('danger')")
        assert any("eval" in w for w in result["data"]["warnings"])

    def test_detects_exec(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "exec('danger')")
        assert any("exec" in w for w in result["data"]["warnings"])

    def test_detects_subprocess(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "import subprocess")
        assert any("子进程" in w for w in result["data"]["warnings"])

    def test_detects_os_system(self):
        sandbox = SkillSandbox()
        code = "import os; os.system('ls')"
        result = sandbox.validate_skill("bad", code)
        assert any("代码执行" in w for w in result["data"]["warnings"])

    def test_detects_file_write(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "open('/tmp/x', 'w')")
        assert any("文件写入" in w for w in result["data"]["warnings"])

    def test_detects_rm_rf(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "rm -rf /")
        assert any("危险系统命令" in w for w in result["data"]["warnings"])

    def test_multiple_warnings(self):
        sandbox = SkillSandbox()
        result = sandbox.validate_skill("bad", "eval('x'); exec('y')")
        assert len(result["data"]["warnings"]) >= 2

    def test_different_code_different_hash(self):
        sandbox = SkillSandbox()
        r1 = sandbox.validate_skill("s", "print(1)")
        r2 = sandbox.validate_skill("s", "print(2)")
        assert r1["data"]["hash"] != r2["data"]["hash"]


# ─── _check_path_access ────────────────────────────────────────────


class TestCheckPathAccess:
    def test_unrestricted_allows_anything(self):
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.UNRESTRICTED))
        ok, _msg = sandbox._check_path_access("/etc/shadow")
        assert ok is True

    def test_restricted_delegates_to_validate_path(self):
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.RESTRICTED, denied_paths=["/etc"]))
        ok, _msg = sandbox._check_path_access("/etc/hosts")
        assert ok is False

    def test_standard_mode(self, tmp_path):
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.STANDARD))
        with (
            patch.object(Path, "cwd", return_value=tmp_path),
            patch.object(Path, "home", return_value=tmp_path / "home"),
        ):
            ok, _ = sandbox._check_path_access(str(tmp_path / "data" / "x.txt"))
            assert ok is True


# ─── execute ───────────────────────────────────────────────────────


class TestExecute:
    @pytest.mark.asyncio
    async def test_sync_function(self):
        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=5))
        result = await sandbox.execute("echo", sync_echo, "a", key="b")
        assert result.success is True
        assert result.data == {"args": ("a",), "kwargs": {"key": "b"}}

    @pytest.mark.asyncio
    async def test_async_function(self):
        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=5))
        result = await sandbox.execute("aecho", async_echo, "x", key="y")
        assert result.success is True
        assert result.data == {"args": ("x",), "kwargs": {"key": "y"}}

    @pytest.mark.asyncio
    async def test_timeout(self):
        async def slow():
            await asyncio.sleep(100)

        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=0.1))
        result = await sandbox.execute("slow", slow)
        assert result.success is False
        assert "超时" in result.error

    @pytest.mark.asyncio
    async def test_function_raising_exception(self):
        def crash():
            raise ValueError("boom")

        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=5))
        result = await sandbox.execute("crash", crash)
        assert result.success is False
        assert "boom" in result.error

    @pytest.mark.asyncio
    async def test_execution_result_has_duration(self):
        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=5))
        result = await sandbox.execute("echo", sync_echo, "hello")
        assert result.duration_ms >= 0
        assert result.stats["total_executions"] >= 1

    @pytest.mark.asyncio
    async def test_execution_counts(self):
        sandbox = SkillSandbox(SandboxConfig(timeout_seconds=5))
        assert sandbox._execution_count == 0
        await sandbox.execute("e1", sync_echo)
        await sandbox.execute("e2", sync_echo)
        assert sandbox._execution_count == 2


# ─── cancel ────────────────────────────────────────────────────────


class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel_active(self):
        sandbox = SkillSandbox()

        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(sandbox.execute("long", long_running, execution_id="exec-1"))
        await asyncio.sleep(0.05)

        result = sandbox.cancel("exec-1")
        assert result["success"] is True

        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    def test_cancel_nonexistent(self):
        sandbox = SkillSandbox()
        result = sandbox.cancel("no-such-id")
        assert result["success"] is False
        assert "不存在" in result["error"]


# ─── stats / config ────────────────────────────────────────────────


class TestStatsAndConfig:
    def test_get_stats(self):
        sandbox = SkillSandbox(SandboxConfig(mode=SandboxMode.STANDARD))
        stats = sandbox.get_stats()
        assert stats["total_executions"] == 0
        assert stats["active_executions"] == 0
        assert stats["config"]["mode"] == "standard"

    def test_set_config(self):
        sandbox = SkillSandbox()
        result = sandbox.set_config(mode=SandboxMode.UNRESTRICTED, timeout_seconds=10)
        assert result["success"] is True
        assert sandbox._config.mode == SandboxMode.UNRESTRICTED
        assert sandbox._config.timeout_seconds == 10

    def test_set_config_unknown_key_ignored(self):
        sandbox = SkillSandbox()
        result = sandbox.set_config(nonexistent_key=True)
        assert result["success"] is True
        assert not hasattr(sandbox._config, "nonexistent_key")

    def test_add_allowed_path(self, tmp_path):
        sandbox = SkillSandbox()
        result = sandbox.add_allowed_path(str(tmp_path))
        assert result["success"] is True
        assert str(tmp_path.resolve()) in sandbox._config.allowed_paths

    def test_add_allowed_path_dedup(self, tmp_path):
        sandbox = SkillSandbox()
        sandbox.add_allowed_path(str(tmp_path))
        sandbox.add_allowed_path(str(tmp_path))
        assert sandbox._config.allowed_paths.count(str(tmp_path.resolve())) == 1

    def test_remove_allowed_path(self, tmp_path):
        sandbox = SkillSandbox()
        sandbox.add_allowed_path(str(tmp_path))
        result = sandbox.remove_allowed_path(str(tmp_path))
        assert result["success"] is True
        assert str(tmp_path.resolve()) not in sandbox._config.allowed_paths

    def test_remove_nonexistent_path(self, tmp_path):
        sandbox = SkillSandbox()
        result = sandbox.remove_allowed_path(str(tmp_path / "nonexistent"))
        assert result["success"] is True


# ─── SkillSandboxFactory ───────────────────────────────────────────


class TestSkillSandboxFactory:
    def setup_method(self):
        SkillSandboxFactory._sandboxes.clear()

    def test_get_sandbox_singleton(self):
        sb1 = SkillSandboxFactory.get_sandbox("default")
        sb2 = SkillSandboxFactory.get_sandbox("default")
        assert sb1 is sb2

    def test_get_sandbox_different_names(self):
        sb1 = SkillSandboxFactory.get_sandbox("a")
        sb2 = SkillSandboxFactory.get_sandbox("b")
        assert sb1 is not sb2

    def test_create_restricted(self):
        sb = SkillSandboxFactory.create_restricted("restricted-1", ["/tmp"])
        assert sb._config.mode == SandboxMode.RESTRICTED
        assert len(sb._config.allowed_paths) >= 1

    def test_create_standard(self):
        sb = SkillSandboxFactory.create_standard("standard-1")
        assert sb._config.mode == SandboxMode.STANDARD

    def test_create_trusted(self):
        sb = SkillSandboxFactory.create_trusted("trusted-1")
        assert sb._config.mode == SandboxMode.UNRESTRICTED

    def test_list_sandboxes(self):
        SkillSandboxFactory._sandboxes.clear()
        SkillSandboxFactory.create_standard("s1")
        SkillSandboxFactory.create_trusted("s2")
        listing = SkillSandboxFactory.list_sandboxes()
        assert listing["success"] is True
        assert "s1" in listing["data"]
        assert "s2" in listing["data"]


# ─── Convenience functions ─────────────────────────────────────────


class TestConvenienceFunctions:
    def setup_method(self):
        SkillSandboxFactory._sandboxes.clear()

    def test_get_sandbox_func(self):
        sb = get_sandbox("mybox")
        assert sb is SkillSandboxFactory.get_sandbox("mybox")

    def test_get_default_sandbox_config(self):
        cfg = get_default_sandbox_config()
        assert isinstance(cfg, SandboxConfig)
        assert cfg.mode == SandboxMode.RESTRICTED

    def test_create_isolated_sandbox(self):
        paths = ["/tmp/work"]
        sb = create_isolated_sandbox("isolated", paths)
        assert sb._config.mode == SandboxMode.RESTRICTED
        assert len(sb._config.allowed_paths) >= 1
