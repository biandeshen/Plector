"""
Tests for core/content_filter.py

Covers:
- check_content, sanitize_output, filter_html, check_harmful
- Edge cases (empty input, None, special chars)
"""

from core.content_filter import (
    check_content,
    check_harmful,
    filter_html,
    sanitize_output,
)

# ─── check_content ──────────────────────────────────────


class TestCheckContent:
    def test_clean_text_passes(self):
        ok, msg = check_content("今天天气真好")
        assert ok is True
        assert msg == ""

    def test_empty_string_passes(self):
        ok, msg = check_content("")
        assert ok is True
        assert msg == ""

    def test_whitespace_only_passes(self):
        ok, msg = check_content("   \n  \t  ")
        assert ok is True
        assert msg == ""

    def test_detects_password(self):
        ok, msg = check_content("密码: 123456")
        assert ok is False
        assert "密码" in msg

    def test_detects_password_equals(self):
        ok, msg = check_content("password=qwerty123")
        assert ok is False
        assert "密码" in msg

    def test_detects_api_key(self):
        ok, msg = check_content("api_key: sk-1234567890abcdef")
        assert ok is False
        assert "API 密钥" in msg

    def test_detects_secret_key(self):
        ok, msg = check_content("SECRET_KEY=my_secret_value")
        assert ok is False
        assert "API 密钥" in msg

    def test_detects_token(self):
        ok, msg = check_content("TOKEN=ghp_xxxxxxxxxxxx")
        assert ok is False
        assert "Token" in msg

    def test_detects_bank_card(self):
        ok, msg = check_content("卡号: 6222021234567890123")
        assert ok is False
        assert "银行卡" in msg

    def test_detects_id_card(self):
        ok, msg = check_content("身份证: 110101199001011234")
        assert ok is False
        assert "身份证" in msg

    def test_detects_phone(self):
        ok, msg = check_content("手机: 13800138000")
        assert ok is False
        assert "手机" in msg

    def test_detects_mobile_english(self):
        ok, msg = check_content("mobile: 13912345678")
        assert ok is False
        assert "手机" in msg

    def test_detects_passwd(self):
        ok, msg = check_content("passwd: hunter2")
        assert ok is False
        assert "密码" in msg

    def test_case_insensitive_detection(self):
        ok, msg = check_content("PASSWORD=secret")
        assert ok is False
        assert "密码" in msg

    def test_short_number_not_detected_as_card(self):
        """Only 13+ digit numbers after card label are flagged."""
        ok, _msg = check_content("卡号: 12345")
        assert ok is True

    def test_short_phone_not_detected(self):
        """10-digit number after phone label does not match."""
        ok, _msg = check_content("phone: 1234567890")
        assert ok is True

    def test_password_without_spaces(self):
        ok, msg = check_content("password:secret")
        assert ok is False
        assert "密码" in msg

    def test_multiple_sensitive_items_first_wins(self):
        ok, _msg = check_content("password=abc api_key=xyz")
        assert ok is False


# ─── sanitize_output ────────────────────────────────────


class TestSanitizeOutput:
    def test_clean_text_unchanged(self):
        text = "今天天气真好"
        result = sanitize_output(text)
        assert result == text

    def test_empty_string(self):
        assert sanitize_output("") == ""

    def test_whitespace_only(self):
        text = "   \n  "
        assert sanitize_output(text) == text

    def test_hides_password_value(self):
        result = sanitize_output("密码: 123456")
        assert "123456" not in result
        assert "密码" in result

    def test_hides_api_key_value(self):
        result = sanitize_output("api_key=sk-12345")
        assert "sk-12345" not in result
        assert "api_key" in result

    def test_hides_token_value(self):
        result = sanitize_output("TOKEN: ghp_abc123")
        assert "ghp_abc123" not in result
        assert "TOKEN" in result

    def test_hides_bank_card(self):
        result = sanitize_output("卡号: 6222021234567890123")
        assert "6222021234567890123" not in result
        assert "卡号" in result

    def test_hides_id_card(self):
        result = sanitize_output("身份证: 110101199001011234")
        assert "110101199001011234" not in result
        assert "身份证" in result

    def test_hides_phone(self):
        result = sanitize_output("手机: 13800138000")
        assert "13800138000" not in result
        assert "手机" in result

    def test_multiple_sensitive_items_all_hidden(self):
        result = sanitize_output("密码: 123456, api_key: sk-abc, 手机: 13800138000")
        assert "123456" not in result
        assert "sk-abc" not in result
        assert "13800138000" not in result
        assert "密码" in result
        assert "api_key" in result

    def test_english_label_format(self):
        result = sanitize_output("password: supersecure123")
        assert "supersecure123" not in result
        assert "password: [已隐藏]" in result


# ─── filter_html ────────────────────────────────────────


class TestFilterHtml:
    def test_clean_text_unchanged(self):
        text = "Hello, world!"
        assert filter_html(text) == text

    def test_empty_string(self):
        assert filter_html("") == ""

    def test_removes_script_tag(self):
        text = "Hello <script>alert('xss')</script> world"
        result = filter_html(text)
        assert "alert" not in result
        assert "<script>" not in result
        assert result == "Hello  world"

    def test_removes_script_with_attributes(self):
        text = 'Hello <script type="text/javascript">evil()</script>'
        result = filter_html(text)
        assert "evil" not in result
        assert result.strip() == "Hello"

    def test_removes_event_handler(self):
        text = '<button onclick="alert(1)">Click</button>'
        result = filter_html(text)
        assert "onclick" not in result
        assert "alert" not in result

    def test_removes_multiple_event_handlers(self):
        text = '<div onmouseover="x()" onload="y()">text</div>'
        result = filter_html(text)
        assert "onmouseover" not in result
        assert "onload" not in result
        assert "text" in result

    def test_keeps_safe_html(self):
        """Non-dangerous HTML tags should be preserved."""
        text = "<b>bold</b> and <i>italic</i>"
        result = filter_html(text)
        assert result == text

    def test_script_with_newlines(self):
        """Multi-line script blocks are removed."""
        text = "before <script>\n  alert(1)\n</script> after"
        result = filter_html(text)
        assert "alert" not in result
        assert "before" in result
        assert "after" in result

    def test_nested_script_inside_html(self):
        text = "<div><script>hack()</script></div>"
        result = filter_html(text)
        assert result == "<div></div>"

    def test_case_insensitive_script_removal(self):
        text = "<SCRIPT>evil()</SCRIPT>"
        result = filter_html(text)
        assert "evil" not in result

    def test_single_quote_event_handler(self):
        text = "<img onerror='alert(1)' src=x>"
        result = filter_html(text)
        assert "onerror" not in result
        assert "alert" not in result


# ─── check_harmful ──────────────────────────────────────


class TestCheckHarmful:
    def test_clean_text_passes(self):
        ok, msg = check_harmful("正常对话内容")
        assert ok is True
        assert msg == ""

    def test_empty_string_passes(self):
        ok, msg = check_harmful("")
        assert ok is True
        assert msg == ""

    def test_harmful_patterns_empty_no_false_positives(self):
        """With empty HARMFUL_PATTERNS, everything passes."""
        assert check_harmful("any text at all") == (True, "")
        assert check_harmful("bad stuff 123") == (True, "")
