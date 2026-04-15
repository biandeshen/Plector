"""
统一错误处理层测试 - Plector v2.0 Phase 1
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.error_handler import (
    ErrorCategory,
    ErrorInfo,
    ErrorLevel,
    PlectorError,
    ErrorHandler,
)


class TestErrorInfo:
    """ErrorInfo 数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典格式"""
        info = ErrorInfo(
            code="ERR_VALIDATION_001",
            message="Invalid input",
            category=ErrorCategory.VALIDATION,
            level=ErrorLevel.ERROR,
            context={"field": "email"}
        )
        result = info.to_dict()
        
        assert result["success"] is False
        assert result["error"]["code"] == "ERR_VALIDATION_001"
        assert result["error"]["category"] == "validation"
        assert result["error"]["context"]["field"] == "email"


class TestPlectorError:
    """PlectorError 异常测试"""
    
    def test_basic_error(self):
        """测试基本错误创建"""
        err = PlectorError("Something went wrong")
        
        assert str(err) == "Something went wrong"
        assert err.message == "Something went wrong"
        assert err.code.startswith("ERR_")
    
    def test_error_with_cause(self):
        """测试带原异常的错误"""
        cause = ValueError("Original error")
        err = PlectorError("Handler error", cause=cause)
        
        assert err.cause is cause
        assert err.traceback_str is not None


class TestErrorHandler:
    """ErrorHandler 测试"""
    
    def test_handle_sync_error(self):
        """测试同步错误处理"""
        def failing_func():
            raise ValueError("Test error")
        
        result = ErrorHandler.execute(failing_func)
        
        assert result.success is False
        assert result.error_info is not None
        assert "ValueError" in result.error_info.message
    
    def test_handle_success(self):
        """测试成功执行"""
        def success_func():
            return {"data": "test"}
        
        result = ErrorHandler.execute(success_func)
        
        assert result.success is True
        assert result.data == {"data": "test"}
    
    def test_error_recovery(self):
        """测试错误恢复"""
        errors = []
        
        def error_func():
            errors.append(1)
            raise RuntimeError("Test")
        
        result = ErrorHandler.execute_with_recovery(
            error_func,
            retry_count=2,
            recovery_func=lambda: {"recovered": True}
        )
        
        assert result.success is True
        assert result.data["recovered"] is True
        assert len(errors) == 3  # 1次失败 + 2次重试
