"""
Tests for core.security.ssrf_guard

Tests cover:
- is_private_ip with public/private/localhost IPs
- mask_hostname for logging
- validate_url_scheme, validate_url_hostname, validate_url_no_private_ip
- resolve_and_check hostname resolution
- validate_file_path with allowed paths
- SSRFCheckResult NamedTuple
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.security.ssrf_guard import (
    MAX_FILE_SIZE,
    SUPPORTED_FORMATS,
    SSRFCheckResult,
    is_private_ip,
    mask_hostname,
    resolve_and_check,
    validate_file_path,
    validate_url_hostname,
    validate_url_no_private_ip,
    validate_url_scheme,
)

# ─── SSRFCheckResult ─────────────────────────────────────


class TestSSRFCheckResult:
    def test_create_result_safe(self):
        r = SSRFCheckResult(True, "", ["1.2.3.4"])
        assert r.safe is True
        assert r.message == ""
        assert r.safe_ips == ["1.2.3.4"]

    def test_create_result_unsafe(self):
        r = SSRFCheckResult(False, "blocked", [])
        assert r.safe is False
        assert r.message == "blocked"
        assert r.safe_ips == []

    def test_result_is_namedtuple(self):
        r = SSRFCheckResult(True, "", [])
        safe, msg, ips = r
        assert safe is True
        assert msg == ""
        assert ips == []


# ─── is_private_ip ───────────────────────────────────────


class TestIsPrivateIp:
    def test_loopback_is_private(self):
        assert is_private_ip("127.0.0.1") is True

    def test_private_10_dot(self):
        assert is_private_ip("10.0.0.1") is True

    def test_private_172_16(self):
        assert is_private_ip("172.16.0.1") is True

    def test_private_192_168(self):
        assert is_private_ip("192.168.1.1") is True

    def test_public_ip(self):
        assert is_private_ip("8.8.8.8") is False

    def test_another_public_ip(self):
        assert is_private_ip("1.1.1.1") is False

    def test_localhost_string(self):
        """The string 'localhost' should be treated as private."""
        assert is_private_ip("localhost") is True

    def test_invalid_ip_string(self):
        """An invalid IP string that is not 'localhost' should return False."""
        assert is_private_ip("not-an-ip") is False

    def test_empty_string(self):
        assert is_private_ip("") is False

    def test_ipv6_loopback_is_private(self):
        assert is_private_ip("::1") is True

    def test_ipv6_unique_local_is_private(self):
        assert is_private_ip("fd00::1") is True

    def test_ipv6_public(self):
        assert is_private_ip("2001:4860:4860::8888") is False


# ─── mask_hostname ───────────────────────────────────────


class TestMaskHostname:
    def test_empty_string(self):
        assert mask_hostname("") == "N/A"

    def test_none_value(self):
        assert mask_hostname(None) == "N/A"

    def test_ipv4_masked(self):
        result = mask_hostname("8.8.8.8")
        # Parts: ["8", "8", "8", "8"] -> "8.***.***.8"
        assert result == "8.***.***.8"

    def test_simple_domain(self):
        assert mask_hostname("example.com") == "example.com"

    def test_subdomain(self):
        """For multi-level domains, only last two parts are kept."""
        assert mask_hostname("sub.domain.example.com") == "example.com"

    def test_short_name(self):
        """Single part with length <= 4 is returned as-is."""
        assert mask_hostname("abcd") == "abcd"

    def test_long_name(self):
        """Single part with length > 4 gets middle chars replaced."""
        assert mask_hostname("abcdefgh") == "ab****gh"

    def test_single_char(self):
        assert mask_hostname("x") == "x"

    def test_two_part_local(self):
        """A name with two dot-separated parts shows both."""
        assert mask_hostname("host.example.com") == "example.com"

    def test_mask_single_part_long(self):
        """A single-part name longer than 4 chars gets middle masked."""
        result = mask_hostname("my-host")
        assert result == "my****st"

    def test_mask_single_part_short(self):
        """A single-part name <= 4 chars is unchanged."""
        assert mask_hostname("abc") == "abc"


# ─── resolve_and_check ───────────────────────────────────


class TestResolveAndCheck:
    def test_localhost_resolves_to_private(self):
        """'localhost' resolves to 127.0.0.1 which is private."""
        result = resolve_and_check("localhost")
        assert result.safe is False
        assert "内网地址" in result.message

    def test_nonexistent_hostname(self):
        """An unresolvable hostname should return unsafe."""
        result = resolve_and_check("this-hostname-does-not-exist-999999xyz.test")
        assert result.safe is False
        assert result.message in ("域名解析失败", "IP 检查出错")


# ─── validate_url_scheme ─────────────────────────────────


class TestValidateUrlScheme:
    def test_http_scheme(self):
        result = validate_url_scheme("http://example.com")
        assert result.safe is True

    def test_https_scheme(self):
        result = validate_url_scheme("https://example.com")
        assert result.safe is True

    def test_ftp_scheme_rejected(self):
        result = validate_url_scheme("ftp://example.com")
        assert result.safe is False

    def test_file_scheme_rejected(self):
        result = validate_url_scheme("file:///etc/passwd")
        assert result.safe is False

    def test_empty_string(self):
        result = validate_url_scheme("")
        assert result.safe is False

    def test_no_scheme(self):
        result = validate_url_scheme("example.com")
        assert result.safe is False


# ─── validate_url_hostname ───────────────────────────────


class TestValidateUrlHostname:
    def test_valid_hostname(self):
        result = validate_url_hostname("http://example.com/path")
        assert result.safe is True

    def test_no_hostname(self):
        result = validate_url_hostname("http:///path")
        assert result.safe is False
        assert "缺少主机名" in result.message

    def test_empty_string(self):
        result = validate_url_hostname("")
        assert result.safe is False

    def test_ip_as_hostname(self):
        result = validate_url_hostname("http://8.8.8.8/path")
        assert result.safe is True


# ─── validate_url_no_private_ip ──────────────────────────


class TestValidateUrlNoPrivateIp:
    def test_public_ip_passes(self):
        result = validate_url_no_private_ip("8.8.8.8")
        assert result.safe is True

    def test_private_ip_blocked(self):
        result = validate_url_no_private_ip("127.0.0.1")
        assert result.safe is False
        assert "内网地址" in result.message

    def test_localhost_string_blocked(self):
        result = validate_url_no_private_ip("localhost")
        assert result.safe is False

    def test_empty_string(self):
        """Empty string is not caught by is_private_ip check, so it's safe."""
        result = validate_url_no_private_ip("")
        assert result.safe is True


# ─── SUPPORTED_FORMATS / MAX_FILE_SIZE ───────────────────


class TestConstants:
    def test_supported_formats_contains_common_image_types(self):
        assert ".png" in SUPPORTED_FORMATS
        assert ".jpg" in SUPPORTED_FORMATS
        assert ".jpeg" in SUPPORTED_FORMATS
        assert ".gif" in SUPPORTED_FORMATS
        assert ".webp" in SUPPORTED_FORMATS
        assert ".bmp" in SUPPORTED_FORMATS

    def test_max_file_size_is_20mb(self):
        assert MAX_FILE_SIZE == 20 * 1024 * 1024


# ─── validate_file_path ──────────────────────────────────


@pytest.fixture
def temp_image_dir():
    """Create a temp directory with a valid image file and some invalid files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Valid PNG file
        valid_png = tmp_path / "photo.png"
        valid_png.write_bytes(b"fake png content here " * 100)

        # Empty file
        empty_file = tmp_path / "empty.png"
        empty_file.write_bytes(b"")

        # File with unsupported extension
        unsupported = tmp_path / "document.pdf"
        unsupported.write_bytes(b"fake pdf content")

        # Directory (not a file)
        subdir = tmp_path / "images"
        subdir.mkdir()

        # File with no extension
        no_ext = tmp_path / "README"
        no_ext.write_text("no extension")

        yield {
            "tmpdir": tmpdir,
            "valid_png": str(valid_png),
            "empty_file": str(empty_file),
            "unsupported": str(unsupported),
            "subdir": str(subdir),
            "no_ext": str(no_ext),
        }


class TestValidateFilePath:
    # ── With allowed_paths (directory-only check) ──────────

    def test_valid_file_in_allowed_path(self, temp_image_dir):
        """A valid image file under allowed_paths should pass."""
        result = validate_file_path(temp_image_dir["valid_png"], allowed_paths=[temp_image_dir["tmpdir"]])
        assert result.safe is True, f"Expected safe, got: {result.message}"

    def test_file_not_in_allowed_path(self, temp_image_dir):
        """A file outside allowed_paths should be rejected."""
        isolated_dir = os.path.join(tempfile.gettempdir(), "__plector_test_isolated__")
        result = validate_file_path(temp_image_dir["valid_png"], allowed_paths=[isolated_dir])
        assert result.safe is False
        # Error message mentions the directory restriction
        assert result.message != ""

    def test_nonexistent_file_in_allowed_path_passes_dir_check(self, temp_image_dir):
        """With allowed_paths, non-existent files still pass if the path is under the allowed dir.
        This is current behavior: allowed_paths only checks directory membership, not file validity."""
        result = validate_file_path(
            os.path.join(temp_image_dir["tmpdir"], "nonexistent.png"),
            allowed_paths=[temp_image_dir["tmpdir"]],
        )
        # The path is under allowed_paths, so it passes (only directory check)
        assert result.safe is True

    # ── Without allowed_paths (full validation) ────────────
    # Temp files ARE under user home, so cwd/home check passes and full validation runs.

    def test_valid_file_without_allowed_paths(self, temp_image_dir):
        """A valid image file under home passes full validation."""
        result = validate_file_path(temp_image_dir["valid_png"])
        assert result.safe is True

    def test_unsupported_extension_without_allowed_paths(self, temp_image_dir):
        result = validate_file_path(temp_image_dir["unsupported"])
        assert result.safe is False
        assert "格式" in result.message

    def test_empty_file_without_allowed_paths(self, temp_image_dir):
        result = validate_file_path(temp_image_dir["empty_file"])
        assert result.safe is False
        assert "为空" in result.message

    def test_directory_without_allowed_paths(self, temp_image_dir):
        result = validate_file_path(temp_image_dir["subdir"])
        assert result.safe is False
        assert "不是文件" in result.message

    def test_nonexistent_file_without_allowed_paths(self, temp_image_dir):
        result = validate_file_path(os.path.join(temp_image_dir["tmpdir"], "nonexistent.png"))
        assert result.safe is False

    def test_file_with_no_extension_without_allowed_paths(self, temp_image_dir):
        result = validate_file_path(temp_image_dir["no_ext"])
        assert result.safe is False

    def test_permission_error(self):
        """A path that triggers PermissionError (e.g., protected system path)."""
        result = validate_file_path("\\\\nonexistent\\share\\file.png")
        assert result.safe is False


# ─── Edge cases ──────────────────────────────────────────


class TestEdgeCases:
    def test_validate_url_scheme_malformed(self):
        """Malformed URLs should be safely handled."""
        result = validate_url_scheme("http://")
        assert result.safe is True  # scheme is ok, even if rest is empty

    def test_validate_url_hostname_ipv6(self):
        result = validate_url_hostname("http://[::1]:8080/path")
        assert result.safe is True
