"""
技能沙箱测试 - Plector v2.0 Phase 1
"""

import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.skill_sandbox import (
    SandboxMode,
    SandboxConfig,
    ExecutionResult,
    SkillSandbox,
    SkillSandboxFactory,
)


class TestSkillSandbox:
    """SkillSandbox 测试"""
    
    @pytest.fixture
    def sandbox(self):
        """创建测试用沙箱"""
        config = SandboxConfig(
            mode=SandboxMode.STANDARD,
            timeout_seconds=5
        )
        return SkillSandbox(config)
    
    def test_validate_skill_safe(self, sandbox):
        """测试安全代码验证"""
        code = """
def safe_function(x):
    return x * 2
"""
        result = sandbox.validate_skill("safe_skill", code)
        
        assert result["success"] is True
        assert len(result["data"]["warnings"]) == 0
    
    def test_validate_skill_dangerous(self, sandbox):
        """测试危险代码检测"""
        code = """
import os
os.system('rm -rf /')
"""
        result = sandbox.validate_skill("dangerous_skill", code)
        
        assert result["success"] is True
        assert len(result["data"]["warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_execute_sync_success(self, sandbox):
        """测试同步函数执行"""
        def add(a, b):
            return a + b
        
        result = await sandbox.execute("add_skill", add, 2, 3)
        
        assert result.success is True
        assert result.data == 5
        assert result.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_async_success(self, sandbox):
        """测试异步函数执行"""
        async def async_add(a, b):
            await asyncio.sleep(0.01)
            return a + b
        
        result = await sandbox.execute("async_add", async_add, 10, 20)
        
        assert result.success is True
        assert result.data == 30
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self, sandbox):
        """测试超时处理"""
        async def slow_func():
            await asyncio.sleep(10)
            return "done"
        
        sandbox._config.timeout_seconds = 1
        
        result = await sandbox.execute("slow", slow_func)
        
        assert result.success is False
        assert "超时" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_error(self, sandbox):
        """测试执行错误"""
        def error_func():
            raise ValueError("Test error")
        
        result = await sandbox.execute("error", error_func)
        
        assert result.success is False
        assert "Test error" in result.error
    
    def test_get_stats(self, sandbox):
        """测试统计信息"""
        stats = sandbox.get_stats()
        
        assert "total_executions" in stats
        assert "config" in stats
        assert stats["config"]["mode"] == "standard"
    
    def test_set_config(self, sandbox):
        """测试配置更新"""
        result = sandbox.set_config(timeout_seconds=60)
        
        assert result["success"] is True
        assert sandbox._config.timeout_seconds == 60


class TestSandboxConfig:
    """SandboxConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SandboxConfig()
        
        assert config.mode == SandboxMode.RESTRICTED
        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 256
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SandboxConfig(
            mode=SandboxMode.UNRESTRICTED,
            timeout_seconds=120,
            enable_network=True
        )
        
        assert config.mode == SandboxMode.UNRESTRICTED
        assert config.enable_network is True


class TestSkillSandboxFactory:
    """沙箱工厂测试"""
    
    def test_get_sandbox_singleton(self):
        """测试单例模式"""
        sb1 = SkillSandboxFactory.get_sandbox("test")
        sb2 = SkillSandboxFactory.get_sandbox("test")
        
        assert sb1 is sb2
    
    def test_create_restricted(self):
        """测试创建严格模式沙箱"""
        sandbox = SkillSandboxFactory.create_restricted("restricted_test")
        
        assert sandbox._config.mode == SandboxMode.RESTRICTED
    
    def test_create_trusted(self):
        """测试创建可信沙箱"""
        sandbox = SkillSandboxFactory.create_trusted("trusted_test")
        
        assert sandbox._config.mode == SandboxMode.UNRESTRICTED
    
    def test_list_sandboxes(self):
        """测试列出沙箱"""
        SkillSandboxFactory.get_sandbox("list_test")
        
        result = SkillSandboxFactory.list_sandboxes()
        
        assert result["success"] is True
        assert "list_test" in result["data"]


class TestExecutionResult:
    """ExecutionResult 测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ExecutionResult(
            success=True,
            data={"value": 42},
            duration_ms=100.5
        )
        
        assert result.success is True
        assert result.data["value"] == 42
    
    def test_error_result(self):
        """测试错误结果"""
        result = ExecutionResult(
            success=False,
            error="Something failed",
            duration_ms=50.0
        )
        
        assert result.success is False
        assert result.error == "Something failed"
