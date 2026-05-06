"""Tests for core.image.validator — image path/URL validation."""

from unittest.mock import MagicMock, patch

from core.image.validator import (
    _http_check_url,
    validate_image_path,
    validate_image_source,
    validate_image_url,
)

# ===================================================================
# validate_image_path
# ===================================================================


class TestValidateImagePath:
    def test_valid_path(self):
        mock_result = MagicMock()
        mock_result.safe = True
        mock_result.message = ""
        with patch("core.image.validator.validate_file_path", return_value=mock_result):
            ok, msg = validate_image_path("/path/to/image.png")
            assert ok is True
            assert msg == ""

    def test_invalid_path(self):
        mock_result = MagicMock()
        mock_result.safe = False
        mock_result.message = "文件不存在"
        with patch("core.image.validator.validate_file_path", return_value=mock_result):
            ok, msg = validate_image_path("/nonexistent/image.png")
            assert ok is False
            assert msg == "文件不存在"


# ===================================================================
# validate_image_url
# ===================================================================


class TestValidateImageUrl:
    def test_valid_url(self):
        with (
            patch("core.image.validator.validate_url_scheme") as mock_scheme,
            patch("core.image.validator.validate_url_hostname") as mock_hostname,
            patch("core.image.validator.validate_url_no_private_ip") as mock_no_private,
            patch("core.image.validator.validate_url_dns") as mock_dns,
            patch("core.image.validator._http_check_url", return_value=(True, "")),
        ):
            mock_scheme.return_value = MagicMock(safe=True, message="")
            mock_hostname.return_value = MagicMock(safe=True, message="")
            mock_no_private.return_value = MagicMock(safe=True, message="")
            mock_dns.return_value = MagicMock(safe=True, message="", safe_ips=["1.2.3.4"])

            ok, _msg = validate_image_url("https://example.com/image.jpg")
            assert ok is True

    def test_invalid_scheme(self):
        with patch("core.image.validator.validate_url_scheme") as mock_scheme:
            mock_scheme.return_value = MagicMock(safe=False, message="仅支持 http/https 协议")
            ok, msg = validate_image_url("ftp://example.com/image.jpg")
            assert ok is False
            assert "仅支持" in msg

    def test_missing_hostname(self):
        with (
            patch("core.image.validator.validate_url_scheme") as mock_scheme,
            patch("core.image.validator.validate_url_hostname") as mock_hostname,
        ):
            mock_scheme.return_value = MagicMock(safe=True, message="")
            mock_hostname.return_value = MagicMock(safe=False, message="URL 缺少主机名")
            ok, msg = validate_image_url("https:///path")
            assert ok is False
            assert "缺少主机名" in msg

    def test_private_ip_rejected(self):
        with (
            patch("core.image.validator.validate_url_scheme") as mock_scheme,
            patch("core.image.validator.validate_url_hostname") as mock_hostname,
            patch("core.image.validator.validate_url_no_private_ip") as mock_no_private,
        ):
            mock_scheme.return_value = MagicMock(safe=True, message="")
            mock_hostname.return_value = MagicMock(safe=True, message="")
            mock_no_private.return_value = MagicMock(safe=False, message="禁止访问内网地址")
            ok, msg = validate_image_url("https://192.168.1.1/image.jpg")
            assert ok is False
            assert "禁止访问" in msg

    def test_dns_failure(self):
        with (
            patch("core.image.validator.validate_url_scheme") as mock_scheme,
            patch("core.image.validator.validate_url_hostname") as mock_hostname,
            patch("core.image.validator.validate_url_no_private_ip") as mock_no_private,
            patch("core.image.validator.validate_url_dns") as mock_dns,
        ):
            mock_scheme.return_value = MagicMock(safe=True, message="")
            mock_hostname.return_value = MagicMock(safe=True, message="")
            mock_no_private.return_value = MagicMock(safe=True, message="")
            mock_dns.return_value = MagicMock(safe=False, message="域名解析失败", safe_ips=[])
            ok, msg = validate_image_url("https://nonexistent.example/image.jpg")
            assert ok is False
            assert "解析失败" in msg

    def test_http_check_called_with_safe_ips(self):
        with (
            patch("core.image.validator.validate_url_scheme") as mock_scheme,
            patch("core.image.validator.validate_url_hostname") as mock_hostname,
            patch("core.image.validator.validate_url_no_private_ip") as mock_no_private,
            patch("core.image.validator.validate_url_dns") as mock_dns,
            patch("core.image.validator._http_check_url") as mock_http,
        ):
            mock_scheme.return_value = MagicMock(safe=True, message="")
            mock_hostname.return_value = MagicMock(safe=True, message="")
            mock_no_private.return_value = MagicMock(safe=True, message="")
            mock_dns.return_value = MagicMock(safe=True, message="", safe_ips=["1.2.3.4"])
            mock_http.return_value = (True, "")

            validate_image_url("https://example.com/image.jpg")

            # _http_check_url should be called with the URL, hostname, and safe_ips
            mock_http.assert_called_once()
            args = mock_http.call_args[0]
            assert args[0] == "https://example.com/image.jpg"
            assert args[1] == "example.com"
            assert args[2] == ["1.2.3.4"]


# ===================================================================
# validate_image_source
# ===================================================================


class TestValidateImageSource:
    def test_empty_source(self):
        ok, msg = validate_image_source("")
        assert ok is False
        assert "为空" in msg

    def test_empty_after_strip(self):
        ok, _msg = validate_image_source("   ")
        assert ok is False

    def test_url_source(self):
        with (
            patch("core.image.validator.validate_image_url") as mock_url,
        ):
            mock_url.return_value = (True, "")
            ok, _msg = validate_image_source("https://example.com/img.png")
            assert ok is True
            mock_url.assert_called_once_with("https://example.com/img.png")

    def test_local_path_source(self):
        with (
            patch("core.image.validator.validate_image_path") as mock_path,
        ):
            mock_path.return_value = (True, "")
            ok, _msg = validate_image_source("/path/to/img.png")
            assert ok is True
            mock_path.assert_called_once_with("/path/to/img.png")

    def test_http_source_dispatches_to_url(self):
        with patch("core.image.validator.validate_image_url") as mock_url:
            mock_url.return_value = (True, "")
            validate_image_source("http://example.com/img.png")
            mock_url.assert_called_once()

    def test_ftp_source_dispatches_to_url(self):
        with patch("core.image.validator.validate_image_url") as mock_url:
            mock_url.return_value = (True, "")
            validate_image_source("ftp://example.com/img.png")
            mock_url.assert_called_once()

    def test_local_path_with_tilde(self):
        with patch("core.image.validator.validate_image_path") as mock_path:
            mock_path.return_value = (True, "")
            ok, _msg = validate_image_source("~/Pictures/img.png")
            assert ok is True
            mock_path.assert_called_once_with("~/Pictures/img.png")


# ===================================================================
# _http_check_url
# ===================================================================


class TestHttpCheckUrl:
    @patch("core.image.validator._get_httpx")
    @patch("core.image.validator.check_http_status")
    @patch("core.image.validator.check_http_redirect")
    def test_success_path(self, mock_redirect, mock_status, mock_get_httpx):
        mock_httpx = MagicMock()
        mock_get_httpx.return_value = mock_httpx

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_redirect.return_value = MagicMock(safe=True)
        mock_status.return_value = MagicMock(safe=True)

        mock_client = MagicMock().__enter__.return_value
        mock_client.head.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client

        ok, _msg = _http_check_url("https://example.com/img.png", "example.com", ["1.2.3.4"])
        assert ok is True

    @patch("core.image.validator._get_httpx")
    @patch("core.image.validator.check_http_redirect")
    def test_redirect_failure(self, mock_redirect, mock_get_httpx):
        mock_httpx = MagicMock()
        mock_get_httpx.return_value = mock_httpx

        mock_response = MagicMock()
        mock_redirect.return_value = MagicMock(safe=False, message="禁止重定向（SSRF 防护）")

        mock_client = MagicMock().__enter__.return_value
        mock_client.head.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client

        ok, msg = _http_check_url("https://example.com/img.png", "example.com", ["1.2.3.4"])
        assert ok is False
        assert "重定向" in msg

    @patch("core.image.validator._get_httpx")
    @patch("core.image.validator.check_http_status")
    @patch("core.image.validator.check_http_redirect")
    def test_status_failure(self, mock_redirect, mock_status, mock_get_httpx):
        mock_httpx = MagicMock()
        mock_get_httpx.return_value = mock_httpx

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_redirect.return_value = MagicMock(safe=True)
        mock_status.return_value = MagicMock(safe=False, message="URL 不可达 (HTTP 404)")

        mock_client = MagicMock().__enter__.return_value
        mock_client.head.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client

        ok, msg = _http_check_url("https://example.com/img.png", "example.com", ["1.2.3.4"])
        assert ok is False
        assert "404" in msg

    @patch("core.image.validator._get_httpx")
    @patch("core.image.validator.check_http_status")
    @patch("core.image.validator.check_http_redirect")
    def test_non_image_content_type_logs_warning(self, mock_redirect, mock_status, mock_get_httpx, caplog):
        mock_httpx = MagicMock()
        mock_get_httpx.return_value = mock_httpx

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_redirect.return_value = MagicMock(safe=True)
        mock_status.return_value = MagicMock(safe=True)

        mock_client = MagicMock().__enter__.return_value
        mock_client.head.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client

        import logging

        with caplog.at_level(logging.WARNING):
            ok, _msg = _http_check_url("https://example.com/img.png", "example.com", ["1.2.3.4"])
            assert ok is True
            assert "Content-Type 不是图片" in caplog.text
