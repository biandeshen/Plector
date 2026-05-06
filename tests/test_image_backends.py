"""Tests for core.image.backends — backend registry management."""

import copy

import pytest

from core.image.backends import (
    _registered_backends,
    disable_backend,
    enable_backend,
    get_available_backends,
    get_backend,
    get_best_backend,
    register_backend,
    unregister_backend,
)

# Default backend snapshot to restore after tests that mutate state
_DEFAULT_BACKENDS = copy.deepcopy(_registered_backends)


@pytest.fixture(autouse=True)
def _reset_backends():
    """Reset module-level backend registry before each test."""
    _registered_backends.clear()
    _registered_backends.update(copy.deepcopy(_DEFAULT_BACKENDS))


# ─── get_available_backends ───────────────────────────────────


def test_get_available_backends_returns_list():
    backends = get_available_backends()
    assert isinstance(backends, list)


def test_get_available_backends_includes_minimax():
    backends = get_available_backends()
    names = [b["name"] for b in backends]
    assert "minimax" in names


def test_get_available_backends_excludes_disabled():
    disable_backend("minimax")
    backends = get_available_backends()
    names = [b["name"] for b in backends]
    assert "minimax" not in names


def test_get_available_backends_each_has_name():
    backends = get_available_backends()
    for b in backends:
        assert "name" in b


# ─── get_best_backend ─────────────────────────────────────────


def test_get_best_backend_returns_minimax():
    best = get_best_backend()
    assert best is not None
    assert best["name"] == "minimax"


def test_get_best_backend_returns_highest_priority():
    register_backend("new_backend", {"type": "api", "priority": 100, "enabled": True})
    best = get_best_backend()
    assert best["name"] == "new_backend"
    assert best["priority"] == 100


def test_get_best_backend_returns_none_when_disabled():
    disable_backend("minimax")
    assert get_best_backend() is None


def test_get_best_backend_picks_highest_priority():
    register_backend("low", {"type": "api", "priority": 1, "enabled": True})
    register_backend("high", {"type": "api", "priority": 99, "enabled": True})
    best = get_best_backend()
    assert best["name"] == "high"


# ─── register_backend ─────────────────────────────────────────


def test_register_backend_adds_new():
    result = register_backend("test_backend", {"type": "api", "priority": 5, "enabled": True})
    assert result is True
    assert "test_backend" in _registered_backends


def test_register_backend_overwrites_existing():
    register_backend("minimax", {"type": "api", "priority": 5, "enabled": False})
    assert _registered_backends["minimax"]["type"] == "api"
    assert _registered_backends["minimax"]["enabled"] is False


# ─── unregister_backend ───────────────────────────────────────


def test_unregister_backend_removes():
    register_backend("temp", {"type": "api", "priority": 1})
    assert unregister_backend("temp") is True
    assert "temp" not in _registered_backends


def test_unregister_backend_missing():
    assert unregister_backend("nonexistent") is False


# ─── enable_backend / disable_backend ─────────────────────────


def test_disable_backend():
    assert disable_backend("minimax") is True
    assert _registered_backends["minimax"]["enabled"] is False


def test_disable_backend_missing():
    assert disable_backend("nonexistent") is False


def test_enable_backend():
    disable_backend("minimax")
    assert enable_backend("minimax") is True
    assert _registered_backends["minimax"]["enabled"] is True


def test_enable_backend_missing():
    assert enable_backend("nonexistent") is False


# ─── get_backend ──────────────────────────────────────────────


def test_get_backend_returns_config():
    cfg = get_backend("minimax")
    assert cfg is not None
    assert cfg["type"] == "mcp"


def test_get_backend_missing():
    assert get_backend("nonexistent") is None


def test_get_backend_returns_same_after_register():
    register_backend("custom", {"type": "skill", "priority": 50})
    cfg = get_backend("custom")
    assert cfg["type"] == "skill"
    assert cfg["priority"] == 50
