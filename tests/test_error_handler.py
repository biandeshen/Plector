"""
错误处理器单元测试 - Plector v2.0 Phase 1
"""

import pytest
from core.error_handler import (
    ErrorCategory,
    ErrorHandler,
    ErrorInfo,
    ErrorLevel,
    NetworkError,
    NotFoundError,
    PlectorError,
    SkillError,
    SystemError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
)


class TestErrorCategories:
    """测试错误分类"""

    def test_validation_error(self):
        """测试参数验证错误"""
        error = ValidationError("Invalid parameter", field="email")
        info = error.to_info()
        
        assert info.code.startswith("VAL_")
        assert info.message == "Invalid parameter"
        assert info.category == ErrorCategory.VALIDATION
        assert info.context.get("field") == "email"

    def test_not_found_error(self):
        """测试资源不存在错误"""
        error = NotFoundError("Skill not found", skill_id="test-123")
        info = error.to_info()
        
        assert info.code.startswith("NF_")
        assert info.category == ErrorCategory.NOT_FOUND
        assert info.context.get("skill_id") == "test-123"

    def test_timeout_error(self):
        """测试超时错误"""
        error = TimeoutError("Request timeout", duration=30)
        info = error.to_info()
        
        assert info.code.startswith("TMO_")
        assert info.category == ErrorCategory.TIMEOUT

    def test_network_error(self):
        """测试网络错误"""
        error = NetworkError("Connection failed", host="api.example.com")
        info = error.to_info()
        
        assert info.code.startswith("NET_")
        assert info.category == ErrorCategory.NETWORK

    def test_skill_error(self):
        """测试技能执行错误"""
        error = SkillError("Skill execution failed", skill="code_writer")
        info = error.to_info()
        
        assert info.code.startswith("SKL_")
        assert info.category == ErrorCategory.SKILL

    def test_system_error(self):
        """测试系统错误"""
        error = SystemError("Internal error", component="event_bus")
        info = error.to_info()
        
        assert info.code.startswith("SYS_")
        assert info.category == ErrorCategory.SYSTEM


class TestErrorHandler:
    """测试错误处理器"""

    def test_handle_known_error(self):
        """测试处理已知错误"""
        handler = ErrorHandler()
        error = ValidationError("Invalid input")
        
        info = handler.handle(error)
        
        assert info.category == ErrorCategory.VALIDATION
        assert info.success is not True
        assert "Invalid input" in info.message or info.detail

    def test_handle_unknown_error(self):
        """测试处理未知错误"""
        handler = ErrorHandler()
        error = ValueError("Something went wrong")
        
        info = handler.handle(error)
        
        assert info.category in ErrorCategory
        assert info.cause is error

    def test_classify_unknown_error_timeout(self):
        """测试未知错误超时分类"""
        handler = ErrorHandler()
        error = TimeoutError("timed out")
        
        info = handler.handle(error)
        
        assert info.category == ErrorCategory.TIMEOUT

    def test_stats_update(self):
        """测试统计更新"""
        handler = ErrorHandler()
        
        handler.handle(ValidationError("error 1"))
        handler.handle(ValidationError("error 2"))
        handler.handle(NotFoundError("error 3"))
        
        stats = handler.get_stats()
        
        assert stats[ErrorCategory.VALIDATION] == 2
        assert stats[ErrorCategory.NOT_FOUND] == 1

    def test_register_handler(self):
        """测试注册错误处理器"""
        handler = ErrorHandler()
        called = []
        
        def my_handler(info):
            called.append(info)
        
        handler.register_handler(ErrorCategory.VALIDATION, my_handler)
        handler.handle(ValidationError("test"))
        
        assert len(called) == 1
        assert called[0].category == ErrorCategory.VALIDATION

    def test_recovery_suggestion(self):
        """测试恢复建议"""
        handler = ErrorHandler()
        
        suggestions = {
            ErrorCategory.VALIDATION: handler.get_recovery_suggestion(
                ErrorInfo("ERR", "", ErrorCategory.VALIDATION, ErrorLevel.ERROR)
            ),
            ErrorCategory.TIMEOUT: handler.get_recovery_suggestion(
                ErrorInfo("ERR", "", ErrorCategory.TIMEOUT, ErrorLevel.ERROR)
            ),
        }
        
        assert "参数" in suggestions[ErrorCategory.VALIDATION]
        assert "超时" in suggestions[ErrorCategory.TIMEOUT] or "重试" in suggestions[ErrorCategory.TIMEOUT]


class TestErrorInfo:
    """测试错误信息结构"""

    def test_to_dict(self):
        """测试转换为字典"""
        info = ErrorInfo(
            code="TEST_001",
            message="Test error",
            category=ErrorCategory.UNKNOWN,
            level=ErrorLevel.ERROR,
            context={"key": "value"}
        )
        
        result = info.to_dict()
        
        assert result["success"] is False
        assert result["error"]["code"] == "TEST_001"
        assert result["error"]["context"]["key"] == "value"


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_handle_error_function(self):
        """测试便捷错误处理函数"""
        error = ValidationError("Quick test")
        
        info = handle_error(error)
        
        assert info.category == ErrorCategory.VALIDATION

    def test_get_error_handler_singleton(self):
        """测试单例模式"""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        
        assert handler1 is handler2


@pytest.mark.asyncio
class TestAsyncErrorHandling:
    """测试异步错误处理"""

    async def test_safe_execute_success(self):
        """测试安全执行成功"""
        handler = ErrorHandler()
        
        async def successful_coro():
            return {"result": "success"}
        
        result = await handler.handle_async(successful_coro())
        
        assert result == {"result": "success"}

    async def test_safe_execute_failure(self):
        """测试安全执行失败"""
        handler = ErrorHandler()
        
        async def failing_coro():
            raise ValueError("Async error")
        
        result = await handler.handle_async(failing_coro())
        
        assert result["success"] is False
        assert "Async error" in str(result["error"])
