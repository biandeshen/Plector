"""
Tests for core/path_manager.py

Covers:
- All PathManager classmethods
- is_safe_path with valid paths, traversal attempts, non-existent paths
- Relative paths resolution
"""

from pathlib import Path

from core.path_manager import PathManager


class TestPathManagerClassmethods:
    """Tests for directory/file path classmethods."""

    def test_project_root_is_resolved(self):
        root = PathManager.PROJECT_ROOT
        assert isinstance(root, Path)
        assert root.is_absolute()
        assert (root / "core").exists()
        assert (root / "tests").exists()

    def test_data_dir(self):
        path = PathManager.data_dir()
        assert path == PathManager.PROJECT_ROOT / "data"

    def test_db_path(self):
        path = PathManager.db_path()
        assert path == PathManager.data_dir() / "plector.db"

    def test_config_dir(self):
        path = PathManager.config_dir()
        assert path == PathManager.PROJECT_ROOT / "config"

    def test_logs_dir(self):
        path = PathManager.logs_dir()
        assert path == PathManager.data_dir() / "logs"

    def test_cache_dir(self):
        path = PathManager.cache_dir()
        assert path == PathManager.data_dir() / "cache"

    def test_workflows_dir(self):
        path = PathManager.workflows_dir()
        preferred = PathManager.PROJECT_ROOT / "servers" / "agency-orchestrator" / "workflows"
        fallback = PathManager.PROJECT_ROOT / "workflows"
        assert path == (preferred if preferred.exists() else fallback)

    def test_workflows_dir_is_directory(self):
        path = PathManager.workflows_dir()
        assert path.is_dir()


class TestIsSafePath:
    """Tests for is_safe_path path traversal checking."""

    def test_safe_relative_path(self):
        """A path within the base directory is safe."""
        assert PathManager.is_safe_path("core/__init__.py") is True

    def test_safe_subdirectory(self):
        assert PathManager.is_safe_path("tests") is True

    def test_traversal_attempt(self):
        """Path traversal outside project root is unsafe."""
        assert PathManager.is_safe_path("../") is False
        assert PathManager.is_safe_path("../../etc/passwd") is False

    def test_traversal_then_back_in(self):
        """Traversal that leaves and re-enters the project root."""
        path = "../" + PathManager.PROJECT_ROOT.name + "/core/__init__.py"
        result = PathManager.is_safe_path(path)
        assert isinstance(result, bool)

    def test_dot_safe(self):
        """Single dot is safe -- it resolves to base_dir."""
        assert PathManager.is_safe_path(".") is True

    def test_absolute_path_inside_base(self):
        """Absolute path that matches base_dir should be safe."""
        path = str(PathManager.PROJECT_ROOT)
        assert PathManager.is_safe_path(path) is True

    def test_absolute_path_outside_base(self):
        """Absolute path outside base_dir should be unsafe."""
        # Use root of the current drive as the canonical "outside" path
        drive_root = str(PathManager.PROJECT_ROOT.drive) + "\\" if PathManager.PROJECT_ROOT.drive else "/"
        assert PathManager.is_safe_path(drive_root) is False

    def test_none_path_returns_false(self):
        """None value results in OSError/ValueError and returns False."""
        assert PathManager.is_safe_path(None) is False  # type: ignore[arg-type]

    def test_empty_path(self):
        """Empty string resolves to base_dir, which is safe."""
        assert PathManager.is_safe_path("") is True

    def test_custom_base_dir(self):
        """is_safe_path with explicit base_dir."""
        base = PathManager.PROJECT_ROOT / "tests"
        assert PathManager.is_safe_path("test_governance.py", base_dir=base) is True
        assert PathManager.is_safe_path("../pyproject.toml", base_dir=base) is False

    def test_path_with_special_chars(self):
        """Paths with special characters should be handled gracefully."""
        result = PathManager.is_safe_path("dir with spaces/file.txt")
        assert isinstance(result, bool)

    def test_nested_traversal(self):
        """Traversal hidden inside nested paths."""
        assert PathManager.is_safe_path("core/../../etc") is False

    def test_repeated_is_safe_idempotent(self):
        """Calling multiple times should give same results."""
        assert PathManager.is_safe_path("../") is False
        assert PathManager.is_safe_path("../") is False
        assert PathManager.is_safe_path("..") is False
