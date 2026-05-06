"""Tests for core.image_handler — main image processing coordinator."""

import copy
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core import image_handler as m

# ===================================================================
# Fixtures: save/restore mutable module state
# ===================================================================


@pytest.fixture(autouse=True)
def _preserve_backends():
    """Save and restore IMAGE_BACKENDS and _dns_cache around each test."""
    orig_backends = copy.deepcopy(m.IMAGE_BACKENDS)
    yield
    m.IMAGE_BACKENDS.clear()
    m.IMAGE_BACKENDS.update(copy.deepcopy(orig_backends))
    m.clear_dns_cache()


# ===================================================================
# _mask_host
# ===================================================================


class TestMaskHost:
    def test_empty(self):
        assert m._mask_host("") == "N/A"

    def test_none(self):
        assert m._mask_host(None) == "N/A"

    def test_ipv4(self):
        assert m._mask_host("192.168.1.100") == "192.***.***.100"

    def test_domain(self):
        assert m._mask_host("example.com") == "example.com"

    def test_subdomain(self):
        assert m._mask_host("sub.internal.corp.example.com") == "example.com"

    def test_short_word(self):
        assert m._mask_host("abc") == "abc"

    def test_long_word(self):
        masked = m._mask_host("verylonghostname")
        assert "****" in masked


# ===================================================================
# validate_image_source / validate_image_path
# ===================================================================


class TestValidateImageSource:
    @patch("core.image_handler._validate_url")
    @patch("core.image_handler._validate_local_file")
    def test_url_dispatches_to_validate_url(self, mock_local, mock_url):
        mock_url.return_value = (True, "")
        ok, _msg = m.validate_image_source("https://example.com/img.png")
        assert ok is True
        mock_url.assert_called_once_with("https://example.com/img.png")
        mock_local.assert_not_called()

    @patch("core.image_handler._validate_url")
    @patch("core.image_handler._validate_local_file")
    def test_local_path_dispatches_to_validate_local(self, mock_local, mock_url):
        mock_local.return_value = (True, "")
        ok, _msg = m.validate_image_source("/path/to/img.png")
        assert ok is True
        mock_local.assert_called_once_with("/path/to/img.png")
        mock_url.assert_not_called()

    def test_empty_string(self):
        ok, _msg = m.validate_image_source("")
        assert ok is False

    def test_whitespace_only(self):
        ok, _msg = m.validate_image_source("   ")
        assert ok is False

    def test_non_string(self):
        ok, _msg = m.validate_image_source(42)
        assert ok is False

    def test_http_url(self):
        with patch("core.image_handler._validate_url", return_value=(True, "")):
            ok, _msg = m.validate_image_source("http://example.com/img.png")
            assert ok is True


def test_validate_image_path_delegates():
    """validate_image_path should be an alias for validate_image_source."""
    with patch("core.image_handler.validate_image_source", return_value=(True, "")):
        ok, _msg = m.validate_image_path("/some/path.png")
        assert ok is True


# ===================================================================
# _is_private_ip
# ===================================================================


class TestIsPrivateIp:
    def test_private(self):
        assert m._is_private_ip("10.0.0.1") is True
        assert m._is_private_ip("192.168.1.1") is True

    def test_public(self):
        assert m._is_private_ip("8.8.8.8") is False

    def test_localhost_string(self):
        assert m._is_private_ip("localhost") is True


# ===================================================================
# _validate_local_file
# ===================================================================


class TestValidateLocalFile:
    @patch("core.image_handler.Path")
    def test_valid_file(self, mock_path_class):
        """A valid local image file passes validation."""
        mock_instance = MagicMock(spec=Path)
        mock_instance.expanduser.return_value = mock_instance
        mock_instance.resolve.return_value = mock_instance
        mock_instance.exists.return_value = True
        mock_instance.is_file.return_value = True
        mock_instance.stat.return_value.st_size = 1024
        mock_instance.suffix = ".png"
        mock_instance.relative_to.return_value = None

        mock_path_class.return_value = mock_instance
        mock_path_class.cwd.return_value = mock_instance
        mock_path_class.home.return_value = MagicMock()

        ok, _msg = m._validate_local_file("/valid/image.png")
        assert ok is True

    @patch("core.image_handler.Path")
    def test_file_not_found(self, mock_path_class):
        mock_instance = MagicMock(spec=Path)
        mock_instance.expanduser.return_value = mock_instance
        mock_instance.resolve.return_value = mock_instance
        mock_instance.exists.return_value = False
        mock_instance.is_file.return_value = True
        mock_instance.suffix = ".png"
        mock_instance.relative_to.return_value = None

        mock_path_class.return_value = mock_instance
        mock_path_class.cwd.return_value = mock_instance
        mock_path_class.home.return_value = MagicMock()

        ok, msg = m._validate_local_file("/missing/image.png")
        assert ok is False
        assert "不存在" in msg

    @patch("core.image_handler.Path")
    def test_outside_allowed_dir(self, mock_path_class):
        """When the resolved file is outside both cwd and home."""
        mock_instance = MagicMock(spec=Path)
        mock_instance.expanduser.return_value = mock_instance
        mock_instance.resolve.return_value = mock_instance
        mock_instance.suffix = ".png"
        mock_instance.relative_to.side_effect = ValueError("not relative")

        mock_path_class.return_value = mock_instance
        mock_path_class.cwd.return_value = MagicMock()
        mock_path_class.home.return_value = MagicMock()

        ok, msg = m._validate_local_file("/outside/allowed/image.png")
        assert ok is False
        assert "允许的目录" in msg


# ===================================================================
# _resolve_and_check_ip
# ===================================================================


class TestResolveAndCheckIp:
    @patch("core.image_handler.socket.getaddrinfo")
    def test_public_ip(self, mock_gai):
        mock_gai.return_value = [(socket.AF_INET, 0, 0, "", ("8.8.8.8", 0))]
        safe, _msg, ips = m._resolve_and_check_ip("dns.google")
        assert safe is True
        assert "8.8.8.8" in ips

    @patch("core.image_handler.socket.getaddrinfo")
    def test_private_ip_rejected(self, mock_gai):
        mock_gai.return_value = [(socket.AF_INET, 0, 0, "", ("192.168.1.1", 0))]
        safe, msg, _ips = m._resolve_and_check_ip("internal.example")
        assert safe is False
        assert "内网地址" in msg

    @patch("core.image_handler.socket.getaddrinfo")
    def test_resolution_failure(self, mock_gai):
        mock_gai.side_effect = socket.gaierror("fail")
        safe, msg, _ips = m._resolve_and_check_ip("bad.example")
        assert safe is False
        assert "解析失败" in msg

    @patch("core.image_handler.socket.getaddrinfo")
    def test_exception_handled(self, mock_gai):
        mock_gai.side_effect = OSError("unexpected")
        safe, msg, _ips = m._resolve_and_check_ip("error.example")
        assert safe is False
        assert "检查出错" in msg


# ===================================================================
# _validate_url
# ===================================================================


class TestValidateUrl:
    def test_invalid_scheme(self):
        ok, msg = m._validate_url("ftp://example.com/img.png")
        assert ok is False
        assert "仅支持 http/https" in msg

    def test_no_hostname(self):
        ok, msg = m._validate_url("https:///path")
        assert ok is False
        assert "缺少主机名" in msg

    def test_private_ip_hostname(self):
        ok, msg = m._validate_url("https://192.168.1.1/img.png")
        assert ok is False
        assert "内网地址" in msg

    @patch("core.image_handler._resolve_and_check_ip")
    @patch("core.image_handler._fetch_image_head")
    def test_url_success_path(self, mock_fetch, mock_resolve):
        mock_resolve.return_value = (True, "", ["1.2.3.4"])
        mock_fetch.return_value = (True, "")
        ok, _msg = m._validate_url("https://example.com/img.png")
        assert ok is True

    @patch("core.image_handler._resolve_and_check_ip")
    def test_resolve_fails(self, mock_resolve):
        mock_resolve.return_value = (False, "域名解析失败", [])
        ok, msg = m._validate_url("https://example.com/img.png")
        assert ok is False
        assert "解析失败" in msg


# ===================================================================
# parse_image_command
# ===================================================================


class TestParseImageCommand:
    def test_valid_command(self):
        result = m.parse_image_command("分析图片 /path/to/img.png")
        assert result is not None
        assert result["command"] == "分析图片"
        assert result["image_path"] == "/path/to/img.png"
        assert "prompt" in result

    def test_valid_command_with_url(self):
        result = m.parse_image_command("识别图片 https://example.com/img.png")
        assert result is not None
        assert result["command"] == "识别图片"
        assert result["image_path"] == "https://example.com/img.png"

    def test_no_match(self):
        assert m.parse_image_command("你好世界") is None

    def test_non_string_input(self):
        assert m.parse_image_command(42) is None
        assert m.parse_image_command(None) is None

    def test_empty_input(self):
        assert m.parse_image_command("") is None

    def test_command_without_path(self):
        assert m.parse_image_command("分析图片") is None

    def test_ui_command(self):
        result = m.parse_image_command("图片UI /path/to/ui.png")
        assert result is not None
        assert result["command"] == "图片UI"

    def test_error_command(self):
        result = m.parse_image_command("图片错误 /path/to/error.png")
        assert result is not None
        assert result["command"] == "图片错误"

    def test_code_command(self):
        result = m.parse_image_command("图片代码 /path/to/code.png")
        assert result["command"] == "图片代码"


# ===================================================================
# get_available_backends / get_best_backend / register_backend
# ===================================================================


class TestBackendManagement:
    def test_get_available_backends_returns_sorted_list(self):
        backends = m.get_available_backends()
        assert isinstance(backends, list)
        # Should be sorted by priority descending
        priorities = [b["priority"] for b in backends]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_available_backends_excludes_disabled(self):
        # Disable all backends
        m.IMAGE_BACKENDS["minimax"]["enabled"] = False
        backends = m.get_available_backends()
        assert len(backends) == 0

    def test_get_best_backend_returns_highest_priority(self):
        best = m.get_best_backend()
        assert best is not None
        assert best["name"] == "minimax"
        assert best["priority"] == 10

    def test_get_best_backend_returns_none_when_disabled(self):
        m.IMAGE_BACKENDS["minimax"]["enabled"] = False
        assert m.get_best_backend() is None

    def test_register_backend(self):
        m.register_backend("test_backend", "mcp", server="test_server", tool="test_tool", priority=5)
        assert "test_backend" in m.IMAGE_BACKENDS
        assert m.IMAGE_BACKENDS["test_backend"]["type"] == "mcp"

    def test_register_backend_invalid_type(self):
        with pytest.raises(ValueError, match="不支持的后端类型"):
            m.register_backend("bad", "invalid_type")

    def test_register_backend_mcp_missing_server(self):
        with pytest.raises(ValueError, match="必须指定 server"):
            m.register_backend("bad", "mcp", server=None)

    def test_register_backend_skill_missing_skill(self):
        with pytest.raises(ValueError, match="必须指定 skill"):
            m.register_backend("bad", "skill", skill=None)


# ===================================================================
# DNS cache functions
# ===================================================================


class TestDnsCacheFunctions:
    def test_clear_dns_cache(self):
        m._dns_cache.set("example.com", ["1.2.3.4"])
        assert m._dns_cache.size() > 0
        m.clear_dns_cache()
        assert m._dns_cache.size() == 0

    def test_get_dns_cache_stats(self):
        m._dns_cache.set("example.com", ["1.2.3.4"])
        stats = m.get_dns_cache_stats()
        assert stats["size"] == 1
        assert stats["max_size"] > 0
        assert stats["ttl"] > 0


# ===================================================================
# _DNSCache (internal class, same logic as dns.py)
# ===================================================================


class TestInternalDNSCache:
    def test_set_and_get(self):
        cache = m._DNSCache(ttl=300)
        cache.set("example.com", ["1.2.3.4"])
        assert cache.get("example.com") == ["1.2.3.4"]

    def test_get_missing(self):
        cache = m._DNSCache(ttl=300)
        assert cache.get("nonexistent") is None

    def test_clear(self):
        cache = m._DNSCache(ttl=300)
        cache.set("a.example", ["1.1.1.1"])
        cache.clear()
        assert cache.size() == 0

    def test_lru_eviction(self):
        cache = m._DNSCache(ttl=300, max_size=2)
        cache.set("a.example", ["1.1.1.1"])
        cache.set("b.example", ["2.2.2.2"])
        cache.set("c.example", ["3.3.3.3"])
        assert cache.get("a.example") is None
        assert cache.get("b.example") == ["2.2.2.2"]
        assert cache.get("c.example") == ["3.3.3.3"]


# ===================================================================
# _PinnedResolver (internal class)
# ===================================================================


def test_pinned_resolver_matching():
    resolver = m._PinnedResolver("example.com", ["1.2.3.4"])
    results = resolver.resolve("example.com")
    assert any(r[1] == "1.2.3.4" for r in results)


def test_pinned_resolver_non_matching():
    resolver = m._PinnedResolver("example.com", ["1.2.3.4"])
    with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, 0, 0, "", ("10.0.0.1", 0))]):
        results = resolver.resolve("other.com")
        assert results == [(socket.AF_INET, 0, 0, "", ("10.0.0.1", 0))]


# ===================================================================
# get_image_help
# ===================================================================


class TestGetImageHelp:
    def test_returns_string(self):
        help_text = m.get_image_help()
        assert isinstance(help_text, str)
        assert len(help_text) > 0

    def test_contains_command_prefixes(self):
        help_text = m.get_image_help()
        for cmd in m.IMAGE_COMMANDS:
            assert cmd in help_text

    def test_contains_supported_formats(self):
        help_text = m.get_image_help()
        assert ".png" in help_text
        assert ".jpg" in help_text

    def test_contains_max_size(self):
        help_text = m.get_image_help()
        assert "20MB" in help_text

    def test_contains_available_backends(self):
        help_text = m.get_image_help()
        assert "minimax" in help_text

    @patch("core.image_handler.get_available_backends", return_value=[])
    def test_no_backends(self, mock_backends):
        """When no backends are available, the help should still work."""
        help_text = m.get_image_help()
        assert isinstance(help_text, str)

    def test_contains_examples(self):
        help_text = m.get_image_help()
        assert "示例" in help_text


# ===================================================================
# _get_httpx
# ===================================================================


def test_get_httpx_returns_module():
    """_get_httpx should return the httpx module (lazy import)."""
    httpx = m._get_httpx()
    assert httpx is not None
    # Verify it has expected attributes
    assert hasattr(httpx, "Client")
    assert hasattr(httpx, "Request")
    assert hasattr(httpx, "HTTPTransport")


def test_get_httpx_caches_result():
    """Subsequent calls should return the same module object."""
    first = m._get_httpx()
    second = m._get_httpx()
    assert first is second


# ===================================================================
# Error handling: _fetch_image_head
# ===================================================================


class TestFetchImageHead:
    def _make_mock_httpx(self):
        """Create a mock httpx module with real exception subclasses."""
        mock_httpx = MagicMock()
        mock_httpx.TimeoutException = type("TimeoutException", (Exception,), {})
        mock_httpx.RequestError = type("RequestError", (Exception,), {})
        mock_httpx.ConnectError = type("ConnectError", (Exception,), {})
        return mock_httpx

    @patch("core.image_handler._get_httpx")
    def test_timeout(self, mock_get_httpx):
        mock_httpx = self._make_mock_httpx()
        mock_get_httpx.return_value = mock_httpx
        mock_httpx.Client.side_effect = mock_httpx.TimeoutException()

        ok, msg = m._fetch_image_head("https://example.com/img.png", "example.com", ["1.2.3.4"])
        assert ok is False
        assert "超时" in msg

    @patch("core.image_handler._get_httpx")
    def test_request_error(self, mock_get_httpx):
        mock_httpx = self._make_mock_httpx()
        mock_get_httpx.return_value = mock_httpx
        mock_httpx.Client.side_effect = mock_httpx.RequestError()

        ok, msg = m._fetch_image_head("https://example.com/img.png", "example.com", ["1.2.3.4"])
        assert ok is False
        assert "请求失败" in msg


# ===================================================================
# _check_response_size
# ===================================================================


class TestCheckResponseSize:
    def test_content_length_within_limit(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "1024"}
        ok, _msg = m._check_response_size(mock_client, mock_response, "https://example.com/img.png")
        assert ok is True

    def test_content_length_exceeds_limit(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        too_big = 50 * 1024 * 1024  # 50MB
        mock_response.headers = {"content-length": str(too_big)}
        ok, msg = m._check_response_size(mock_client, mock_response, "https://example.com/img.png")
        assert ok is False
        assert "太大" in msg

    def test_content_length_negative(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "-1"}
        with patch("core.image_handler._stream_check_size", return_value=(True, "")):
            ok, _msg = m._check_response_size(mock_client, mock_response, "https://example.com/img.png")
            assert ok is True

    def test_content_length_invalid(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "not-a-number"}
        with patch("core.image_handler._stream_check_size", return_value=(True, "")):
            ok, _msg = m._check_response_size(mock_client, mock_response, "https://example.com/img.png")
            assert ok is True

    def test_no_content_length_falls_back(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.headers = {}
        with patch("core.image_handler._stream_check_size", return_value=(True, "")):
            ok, _msg = m._check_response_size(mock_client, mock_response, "https://example.com/img.png")
            assert ok is True


# ===================================================================
# _stream_check_size
# ===================================================================


class TestStreamCheckSize:
    def test_stream_within_limit(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [b"x" * 1024] * 10  # 10KB total

        mock_ctx = MagicMock().__enter__.return_value
        mock_ctx.iter_bytes.return_value = mock_response.iter_bytes.return_value
        mock_client.stream.return_value.__enter__.return_value = mock_ctx

        ok, _msg = m._stream_check_size(mock_client, "https://example.com/img.png")
        assert ok is True
        mock_client.stream.assert_called_once()

    def test_stream_exceeds_limit(self):
        mock_client = MagicMock()
        chunk = b"x" * (5 * 1024 * 1024)  # 5MB chunks
        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [chunk] * 5  # 25MB total

        mock_ctx = MagicMock().__enter__.return_value
        mock_ctx.iter_bytes.return_value = mock_response.iter_bytes.return_value
        mock_client.stream.return_value.__enter__.return_value = mock_ctx

        ok, msg = m._stream_check_size(mock_client, "https://example.com/img.png")
        assert ok is False
        assert "太大" in msg

    def test_stream_exception(self):
        mock_client = MagicMock()
        mock_client.stream.side_effect = Exception("stream error")
        ok, msg = m._stream_check_size(mock_client, "https://example.com/img.png")
        assert ok is False
        assert "流式下载检查失败" in msg

    def test_stream_early_exit_on_oversize(self):
        """When a single chunk pushes total over the limit, stop streaming."""
        mock_client = MagicMock()
        big_chunk = b"x" * (25 * 1024 * 1024)  # 25MB single chunk
        mock_ctx = MagicMock().__enter__.return_value
        mock_ctx.iter_bytes.return_value = [big_chunk]
        mock_client.stream.return_value.__enter__.return_value = mock_ctx

        ok, msg = m._stream_check_size(mock_client, "https://example.com/img.png")
        assert ok is False
        assert "太大" in msg


# ===================================================================
# core.image.__init__ exports (included here per user instruction)
# ===================================================================


class TestImageInitExports:
    """Test that core.image.__init__ exports the expected names."""

    def test_all_defined(self):
        from core.image import __all__

        expected = {
            "IMAGE_BACKENDS",
            "IMAGE_COMMANDS",
            "MAX_FILE_SIZE",
            "SUPPORTED_FORMATS",
            "ImageHandler",
            "get_available_backends",
            "get_best_backend",
            "register_backend",
            "validate_image_path",
            "validate_image_source",
        }
        assert set(__all__) == expected

    def test_import_all_members(self):
        from core.image import (
            IMAGE_BACKENDS,
            IMAGE_COMMANDS,
            MAX_FILE_SIZE,
            SUPPORTED_FORMATS,
            ImageHandler,
            get_available_backends,
            get_best_backend,
            register_backend,
            validate_image_path,
            validate_image_source,
        )

        assert isinstance(IMAGE_BACKENDS, dict)
        assert isinstance(IMAGE_COMMANDS, dict)
        assert MAX_FILE_SIZE > 0
        assert isinstance(SUPPORTED_FORMATS, set)
        assert isinstance(ImageHandler, type)
        assert callable(get_available_backends)
        assert callable(get_best_backend)
        assert callable(register_backend)
        assert callable(validate_image_path)
        assert callable(validate_image_source)
