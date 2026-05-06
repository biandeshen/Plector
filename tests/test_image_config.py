"""Tests for core.image.config — constant definitions."""

from core.image.config import (
    DNS_CACHE_MAX_SIZE,
    DNS_CACHE_TTL,
    IMAGE_BACKENDS,
    IMAGE_COMMANDS,
    MAX_FILE_SIZE,
    REDIRECT_STATUS_CODES,
    REQUEST_TIMEOUT,
    STREAM_CHUNK_SIZE,
    SUPPORTED_FORMATS,
)

# ─── SUPPORTED_FORMATS ────────────────────────────────────────


def test_supported_formats_is_set():
    assert isinstance(SUPPORTED_FORMATS, set)
    assert len(SUPPORTED_FORMATS) >= 5


def test_supported_formats_contains_common_extensions():
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        assert ext in SUPPORTED_FORMATS


# ─── MAX_FILE_SIZE ────────────────────────────────────────────


def test_max_file_size_value():
    assert MAX_FILE_SIZE == 20 * 1024 * 1024


def test_max_file_size_is_positive():
    assert MAX_FILE_SIZE > 0


# ─── HTTP CONFIG ──────────────────────────────────────────────


def test_request_timeout():
    assert REQUEST_TIMEOUT == 5


def test_stream_chunk_size():
    assert STREAM_CHUNK_SIZE == 8192


def test_redirect_status_codes():
    assert {301, 302, 303, 307, 308} == REDIRECT_STATUS_CODES


# ─── DNS CACHE CONFIG ─────────────────────────────────────────


def test_dns_cache_ttl():
    assert DNS_CACHE_TTL == 300


def test_dns_cache_max_size():
    assert DNS_CACHE_MAX_SIZE == 1000


# ─── IMAGE_COMMANDS ───────────────────────────────────────────


def test_image_commands_is_dict():
    assert isinstance(IMAGE_COMMANDS, dict)


def test_image_commands_has_expected_keys():
    expected = {"分析图片", "识别图片", "看看这张图", "图片代码", "图片架构", "图片UI", "图片错误"}
    assert set(IMAGE_COMMANDS.keys()) == expected


def test_image_commands_values_are_strings():
    for v in IMAGE_COMMANDS.values():
        assert isinstance(v, str)
        assert len(v) > 0


# ─── IMAGE_BACKENDS ───────────────────────────────────────────


def test_image_backends_is_dict():
    assert isinstance(IMAGE_BACKENDS, dict)


def test_image_backends_has_minimax():
    assert "minimax" in IMAGE_BACKENDS


def test_image_backends_minimax_structure():
    cfg = IMAGE_BACKENDS["minimax"]
    assert cfg["type"] == "mcp"
    assert cfg["server"] == "minimax"
    assert cfg["tool"] == "understand_image"
    assert cfg["priority"] == 10
    assert cfg["enabled"] is True


def test_image_backends_each_has_required_keys():
    required = {"type", "server", "skill", "tool", "priority", "enabled"}
    for name, cfg in IMAGE_BACKENDS.items():
        missing = required - set(cfg.keys())
        assert not missing, f"backend {name!r} missing keys: {missing}"
