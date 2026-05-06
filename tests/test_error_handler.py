"""
Tests for core.error_handler
"""

import pytest

from core.error_handler import (
    ErrorCategory,
    ErrorHandler,
    ErrorInfo,
    ErrorLevel,
    NotFoundError,
    PermissionError,
    PlectorError,
    StorageError,
    SystemError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
    safe_execute,
)

# ─── ErrorCategory ──────────────────────────────────────────────


class TestErrorCategory:
    def test_all_categories_have_unique_values(self):
        """Each ErrorCategory member has a distinct value."""
        values = [c.value for c in ErrorCategory]
        assert len(values) == len(set(values))

    def test_validation_member(self):
        assert ErrorCategory.VALIDATION.value == "validation"

    def test_permission_member(self):
        assert ErrorCategory.PERMISSION.value == "permission"

    def test_not_found_member(self):
        assert ErrorCategory.NOT_FOUND.value == "not_found"

    def test_timeout_member(self):
        assert ErrorCategory.TIMEOUT.value == "timeout"

    def test_network_member(self):
        assert ErrorCategory.NETWORK.value == "network"

    def test_storage_member(self):
        assert ErrorCategory.STORAGE.value == "storage"

    def test_skill_member(self):
        assert ErrorCategory.SKILL.value == "skill"

    def test_system_member(self):
        assert ErrorCategory.SYSTEM.value == "system"

    def test_unknown_member(self):
        assert ErrorCategory.UNKNOWN.value == "unknown"


# ─── ErrorLevel ────────────────────────────────────────────────


class TestErrorLevel:
    def test_all_levels_have_unique_values(self):
        values = [lvl.value for lvl in ErrorLevel]
        assert len(values) == len(set(values))

    def test_debug_member(self):
        assert ErrorLevel.DEBUG.value == "debug"

    def test_info_member(self):
        assert ErrorLevel.INFO.value == "info"

    def test_warning_member(self):
        assert ErrorLevel.WARNING.value == "warning"

    def test_error_member(self):
        assert ErrorLevel.ERROR.value == "error"

    def test_critical_member(self):
        assert ErrorLevel.CRITICAL.value == "critical"


# ─── ErrorInfo ─────────────────────────────────────────────────


class TestErrorInfo:
    def test_minimal_creation(self):
        """ErrorInfo can be created with only required fields."""
        info = ErrorInfo(
            code="ERR_TEST_001",
            message="something went wrong",
            category=ErrorCategory.SYSTEM,
            level=ErrorLevel.ERROR,
        )
        assert info.code == "ERR_TEST_001"
        assert info.message == "something went wrong"
        assert info.category == ErrorCategory.SYSTEM
        assert info.level == ErrorLevel.ERROR
        assert info.success is False

    def test_to_dict_structure(self):
        """to_dict returns the expected structured dictionary."""
        info = ErrorInfo(
            code="ERR_VAL_001",
            message="invalid input",
            category=ErrorCategory.VALIDATION,
            level=ErrorLevel.WARNING,
            detail="field X must be int",
            context={"field": "X"},
        )
        d = info.to_dict()
        assert d["success"] is False
        assert d["error"]["code"] == "ERR_VAL_001"
        assert d["error"]["message"] == "invalid input"
        assert d["error"]["category"] == "validation"
        assert d["error"]["level"] == "warning"
        assert d["error"]["detail"] == "field X must be int"
        assert d["error"]["context"] == {"field": "X"}

    def test_to_dict_none_detail_and_empty_context(self):
        """Optional fields should serialize correctly when None/empty."""
        info = ErrorInfo(
            code="ERR_NF_001",
            message="not found",
            category=ErrorCategory.NOT_FOUND,
            level=ErrorLevel.ERROR,
        )
        d = info.to_dict()
        assert d["error"]["detail"] is None
        assert d["error"]["context"] == {}

    def test_with_cause_and_traceback(self):
        """ErrorInfo can hold a cause exception and traceback string."""
        try:
            raise RuntimeError("inner failure")
        except RuntimeError as exc:
            info = ErrorInfo(
                code="ERR_SYS_001",
                message="system failure",
                category=ErrorCategory.SYSTEM,
                level=ErrorLevel.CRITICAL,
                cause=exc,
                traceback="traceback string",
            )
        assert info.cause is not None
        assert isinstance(info.cause, RuntimeError)
        assert info.traceback == "traceback string"
        assert str(info.cause) == "inner failure"

    def test_success_is_always_false(self):
        """ErrorInfo.success should always be False."""
        info = ErrorInfo(
            code="ERR_X_001",
            message="test",
            category=ErrorCategory.UNKNOWN,
            level=ErrorLevel.ERROR,
        )
        assert info.success is False


# ─── PlectorError ──────────────────────────────────────────────


class TestPlectorError:
    def test_base_plector_error_defaults(self):
        """PlectorError creates default code from UNKNOWN category."""
        err = PlectorError("base error")
        assert err.message == "base error"
        assert err.code == "ERR_UNKNOWN_001"
        assert err.detail is None
        assert err.cause is None
        assert err.context == {}
        assert err.traceback_str is None

    def test_plector_error_with_all_fields(self):
        """PlectorError accepts all optional parameters."""
        cause = ValueError("root cause")
        err = PlectorError(
            "wrapped",
            code="CUSTOM_001",
            detail="extra detail",
            cause=cause,
            foo="bar",
            count=42,
        )
        assert err.message == "wrapped"
        assert err.code == "CUSTOM_001"
        assert err.detail == "extra detail"
        assert err.cause is cause
        assert err.context == {"foo": "bar", "count": 42}

    def test_plector_error_traceback_on_cause(self):
        """traceback_str is set when a cause is provided."""
        try:
            raise ValueError("original")
        except ValueError as exc:
            err = PlectorError("wrapped", cause=exc)
        assert err.traceback_str is not None
        assert "ValueError" in err.traceback_str

    def test_to_info_conversion(self):
        """PlectorError.to_info returns a properly populated ErrorInfo."""
        err = PlectorError("test error", detail="details", foo="bar")
        info = err.to_info(level=ErrorLevel.WARNING)
        assert isinstance(info, ErrorInfo)
        assert info.code == err.code
        assert info.message == "test error"
        assert info.category == ErrorCategory.UNKNOWN
        assert info.level == ErrorLevel.WARNING
        assert info.detail == "details"
        assert info.context == {"foo": "bar"}

    def test_to_info_default_level(self):
        """to_info defaults to ERROR level."""
        err = PlectorError("test")
        info = err.to_info()
        assert info.level == ErrorLevel.ERROR


class TestPlectorErrorSubclasses:
    def test_validation_error_code(self):
        err = ValidationError("bad input")
        assert err.code == "VAL_VALIDATION_001"

    def test_permission_error_code(self):
        err = PermissionError("access denied")
        assert err.code == "PER_PERMISSION_001"

    def test_not_found_error_code(self):
        err = NotFoundError("resource missing")
        assert err.code == "NF_NOT_FOUND_001"

    def test_timeout_error_code(self):
        err = TimeoutError("timed out")
        assert err.code == "TMO_TIMEOUT_001"

    def test_storage_error_code(self):
        err = StorageError("disk full")
        assert err.code == "STO_STORAGE_001"

    def test_system_error_code(self):
        err = SystemError("internal failure")
        assert err.code == "SYS_SYSTEM_001"

    def test_subclass_category_in_error_info(self):
        """Subclass category is propagated through to_info()."""
        err = ValidationError("bad input")
        info = err.to_info()
        assert info.category == ErrorCategory.VALIDATION

    def test_subclass_to_info_preserves_context(self):
        err = PermissionError("denied", resource="/api/data")
        info = err.to_info()
        assert info.context == {"resource": "/api/data"}


# ─── ErrorHandler ──────────────────────────────────────────────


class TestErrorHandler:
    def test_handle_plector_error(self):
        """handle() processes a PlectorError and returns ErrorInfo."""
        handler = ErrorHandler()
        err = ValidationError("bad value", field="age")
        info = handler.handle(err)
        assert isinstance(info, ErrorInfo)
        assert info.category == ErrorCategory.VALIDATION
        assert "bad value" in info.message

    def test_handle_updates_stats(self):
        """handle() increments the error counter for the category."""
        handler = ErrorHandler()
        handler.handle(TimeoutError("timeout", operation="query"))
        stats = handler.get_stats()
        assert stats.get(ErrorCategory.TIMEOUT) == 1

    def test_handle_multiple_errors_increments_stats(self):
        handler = ErrorHandler()
        handler.handle(ValidationError("a"))
        handler.handle(ValidationError("b"))
        handler.handle(TimeoutError("c"))
        stats = handler.get_stats()
        assert stats.get(ErrorCategory.VALIDATION) == 2
        assert stats.get(ErrorCategory.TIMEOUT) == 1

    def test_handle_unknown_exception_timeout_classification(self):
        handler = ErrorHandler()
        info = handler.handle(ValueError("operation timed out"))
        assert info.category == ErrorCategory.TIMEOUT

    def test_handle_unknown_exception_permission_classification(self):
        handler = ErrorHandler()
        info = handler.handle(RuntimeError("permission denied"))
        assert info.category == ErrorCategory.PERMISSION

    def test_handle_unknown_exception_not_found_classification(self):
        handler = ErrorHandler()
        info = handler.handle(FileNotFoundError("file does not exist"))
        assert info.category == ErrorCategory.NOT_FOUND

    def test_handle_unknown_exception_network_classification(self):
        handler = ErrorHandler()
        info = handler.handle(ConnectionError("network connection failed"))
        assert info.category == ErrorCategory.NETWORK

    def test_handle_unknown_exception_storage_classification(self):
        handler = ErrorHandler()
        info = handler.handle(OSError("disk is full"))
        assert info.category == ErrorCategory.STORAGE

    def test_handle_unknown_exception_falls_back_to_unknown(self):
        handler = ErrorHandler()
        info = handler.handle(Exception("some random error"))
        assert info.category == ErrorCategory.UNKNOWN

    def test_handle_with_context(self):
        """handle() merges provided context into ErrorInfo."""
        handler = ErrorHandler()
        err = SystemError("fail")
        info = handler.handle(err, context={"request_id": "abc-123"})
        assert info.context.get("request_id") == "abc-123"

    def test_handle_context_merged_with_plector_context(self):
        """Provided context is merged with (not replacing) the error's own context."""
        handler = ErrorHandler()
        err = ValidationError("bad", field="age")
        info = handler.handle(err, context={"request_id": "r1"})
        assert info.context.get("field") == "age"
        assert info.context.get("request_id") == "r1"

    def test_handle_custom_level(self):
        """handle() accepts an explicit error level override."""
        handler = ErrorHandler()
        err = PlectorError("test")
        info = handler.handle(err, level=ErrorLevel.CRITICAL)
        assert info.level == ErrorLevel.CRITICAL

    def test_get_recovery_suggestion_validation(self):
        handler = ErrorHandler()
        info = ErrorInfo(code="X", message="x", category=ErrorCategory.VALIDATION, level=ErrorLevel.ERROR)
        assert "参数" in handler.get_recovery_suggestion(info)

    def test_get_recovery_suggestion_not_found(self):
        handler = ErrorHandler()
        info = ErrorInfo(code="X", message="x", category=ErrorCategory.NOT_FOUND, level=ErrorLevel.ERROR)
        assert "资源" in handler.get_recovery_suggestion(info)

    def test_get_recovery_suggestion_unknown(self):
        handler = ErrorHandler()
        info = ErrorInfo(code="X", message="x", category=ErrorCategory.UNKNOWN, level=ErrorLevel.ERROR)
        assert "日志" in handler.get_recovery_suggestion(info)

    @pytest.mark.asyncio
    async def test_handle_async_success(self):
        """handle_async returns the coroutine result on success."""
        handler = ErrorHandler()

        async def good():
            return 42

        result = await handler.handle_async(good())
        assert result == 42

    @pytest.mark.asyncio
    async def test_handle_async_failure(self):
        """handle_async returns error dict on exception."""
        handler = ErrorHandler()

        async def bad():
            raise PermissionError("denied", resource="admin")

        result = await handler.handle_async(bad())
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"]["category"] == "permission"

    @pytest.mark.asyncio
    async def test_handle_async_updates_stats_on_failure(self):
        handler = ErrorHandler()

        async def bad():
            raise TimeoutError("slow")

        await handler.handle_async(bad())
        stats = handler.get_stats()
        assert stats.get(ErrorCategory.TIMEOUT) == 1

    def test_register_handler_called(self):
        """Registered handler is invoked when an error of that category occurs."""
        handler = ErrorHandler()
        received = []

        def my_handler(info):
            received.append(info)

        handler.register_handler(ErrorCategory.VALIDATION, my_handler)
        handler.handle(ValidationError("test"))
        assert len(received) == 1
        assert received[0].category == ErrorCategory.VALIDATION

    def test_register_handler_not_called_for_different_category(self):
        handler = ErrorHandler()
        received = []

        def my_handler(info):
            received.append(info)

        handler.register_handler(ErrorCategory.VALIDATION, my_handler)
        handler.handle(TimeoutError("test"))
        assert len(received) == 0

    def test_register_handler_multiple_handlers(self):
        handler = ErrorHandler()
        calls = []

        def h1(info):
            calls.append("h1")

        def h2(info):
            calls.append("h2")

        handler.register_handler(ErrorCategory.SYSTEM, h1)
        handler.register_handler(ErrorCategory.SYSTEM, h2)
        handler.handle(SystemError("test"))
        assert calls == ["h1", "h2"]

    def test_handler_exception_does_not_propagate(self):
        """An exception in a registered handler is caught and logged."""
        handler = ErrorHandler()

        def broken(_info):
            raise ValueError("handler crashed")

        handler.register_handler(ErrorCategory.SYSTEM, broken)
        # Should not raise
        handler.handle(SystemError("test"))

    def test_classify_unknown_error_preserves_message(self):
        handler = ErrorHandler()
        info = handler._classify_unknown_error(ValueError("something broke"), {"env": "prod"})
        assert "something broke" in info.message

    def test_stats_empty_initially(self):
        handler = ErrorHandler()
        assert handler.get_stats() == {}

    def test_empty_stats_after_no_errors(self):
        handler = ErrorHandler()
        assert handler.get_stats() == {}

    def test_get_recovery_suggestion_all_categories(self):
        """Every ErrorCategory has a non-empty recovery suggestion."""
        handler = ErrorHandler()
        for cat in ErrorCategory:
            info = ErrorInfo(code="X", message="x", category=cat, level=ErrorLevel.ERROR)
            suggestion = handler.get_recovery_suggestion(info)
            assert suggestion, f"No suggestion for {cat}"


# ─── Global helpers ────────────────────────────────────────────


class TestGlobalHelpers:
    def test_get_error_handler_singleton(self):
        """get_error_handler() returns the same instance on repeated calls."""
        h1 = get_error_handler()
        h2 = get_error_handler()
        assert h1 is h2

    def test_handle_error_shortcut(self):
        """handle_error() uses the global handler and returns ErrorInfo."""
        err = ValidationError("shortcut test")
        info = handle_error(err)
        assert isinstance(info, ErrorInfo)
        assert info.category == ErrorCategory.VALIDATION

    @pytest.mark.asyncio
    async def test_safe_execute_success(self):
        """safe_execute returns the coroutine result."""

        async def good():
            return "ok"

        result = await safe_execute(good())
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_safe_execute_failure(self):
        """safe_execute returns error dict on exception."""

        async def bad():
            raise SystemError("crash")

        result = await safe_execute(bad())
        assert isinstance(result, dict)
        assert result["success"] is False
