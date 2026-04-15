"""
技能沙箱单元测试 - Plector v2.0 Phase 1
"""

import pytest
from core.skill_sandbox import (
    SandboxConfig,
    SandboxLevel,
    SkillSandbox,
    get_default_sandbox_config,
    get_dev_sandbox_config,
    get_sandbox,
)


class TestSandboxConfig:
    """测试沙箱配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = SandboxConfig()
        
        assert config.level == SandboxLevel.MODERATE
        assert config.max_memory_mb == 512
        assert config.max_cpu_seconds == 30
        assert config.timeout_seconds == 60

    def test_custom_config(self):
        """测试自定义配置"""
        config = SandboxConfig(
            level=SandboxLevel.STRICT,
            max_memory_mb=1024,
            timeout_seconds=120
        )
        
        assert config.level == SandboxLevel.STRICT
        assert config.max_memory_mb == 1024
        assert config.timeout_seconds == 120


class TestSkillSandbox:
    """测试技能沙箱"""

    @pytest.fixture
    def sandbox(self, tmp_path):
        """创建沙箱实例"""
        config = SandboxConfig(
            level=SandboxLevel.BASIC,
            allowed_paths=[str(tmp_path)],
            timeout_seconds=10
        )
        return SkillSandbox(config, base_dir=str(tmp_path))

    @pytest.fixture
    def strict_sandbox(self, tmp_path):
        """创建严格沙箱实例"""
        config = SandboxConfig(
            level=SandboxLevel.STRICT,
            blocked_paths=[str(tmp_path)],
            timeout_seconds=10
        )
        return SkillSandbox(config, base_dir=str(tmp_path))

    def test_path_safety_check(self, sandbox, tmp_path):
        """测试路径安全检查"""
        # 允许的路径
        assert sandbox._is_path_safe(str(tmp_path / "allowed.txt"))
        
        # 路径遍历攻击
        assert not sandbox._is_path_safe(str(tmp_path / ".." / "etc" / "passwd"))

    def test_path_blocking(self, strict_sandbox, tmp_path):
        """测试路径阻止"""
        # 阻止的路径
        assert not strict_sandbox._is_path_safe(str(tmp_path / "blocked.txt"))

    @pytest.mark.asyncio
    async def test_execute_python_simple(self, sandbox):
        """测试执行简单 Python 代码"""
        result = await sandbox.execute_code(
            'print("Hello from sandbox")',
            language="python"
        )
        
        assert result.success
        assert "Hello from sandbox" in result.output

    @pytest.mark.asyncio
    async def test_execute_python_error(self, sandbox):
        """测试执行 Python 错误代码"""
        result = await sandbox.execute_code(
            'raise ValueError("Test error")',
            language="python"
        )
        
        assert not result.success
        assert "Test error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_python_timeout(self, sandbox, tmp_path):
        """测试执行超时"""
        config = SandboxConfig(
            timeout_seconds=1,
            allowed_paths=[str(tmp_path)]
        )
        short_sandbox = SkillSandbox(config, base_dir=str(tmp_path))
        
        result = await short_sandbox.execute_code(
            'import time; time.sleep(10)',
            language="python"
        )
        
        assert not result.success
        assert "超时" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_python_with_output(self, sandbox):
        """测试 Python 代码输出"""
        result = await sandbox.execute_code(
            '''
result = 2 + 2
print(f"Result: {result}")
print("Done")
''',
            language="python"
        )
        
        assert result.success
        assert "Result: 4" in result.output
        assert "Done" in result.output

    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self, sandbox):
        """测试不支持的语言"""
        result = await sandbox.execute_code(
            'print("test")',
            language="unsupported"
        )
        
        assert not result.success
        assert "不支持" in result.error

    def test_temp_dir_creation(self, sandbox):
        """测试临时目录创建"""
        temp_dir = sandbox._create_temp_dir()
        
        assert temp_dir.exists()
        assert temp_dir in sandbox._temp_dirs

    def test_temp_dir_cleanup(self, sandbox):
        """测试临时目录清理"""
        temp_dir = sandbox._create_temp_dir()
        sandbox._cleanup_temp_dir(temp_dir)
        
        assert not temp_dir.exists()
        assert temp_dir not in sandbox._temp_dirs

    def test_cleanup_all(self, sandbox):
        """测试清理所有临时目录"""
        sandbox._create_temp_dir()
        sandbox._create_temp_dir()
        
        sandbox.cleanup_all()
        
        assert len(sandbox._temp_dirs) == 0

    def test_destructor_cleanup(self, sandbox):
        """测试析构函数清理"""
        sandbox._create_temp_dir()
        
        # 模拟析构
        sandbox.__del__()
        
        # 不应抛出异常


class TestPredefinedConfigs:
    """测试预定义配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = get_default_sandbox_config()
        
        assert config.level == SandboxLevel.MODERATE
        assert len(config.blocked_paths) > 0
        assert "/etc" in config.blocked_paths
        assert "/root" in config.blocked_paths

    def test_dev_config(self):
        """测试开发配置"""
        config = get_dev_sandbox_config()
        
        assert config.level == SandboxLevel.BASIC
        assert config.max_memory_mb == 1024
        assert config.timeout_seconds == 120


class TestGetSandbox:
    """测试获取沙箱实例"""

    def test_get_default_sandbox(self):
        """测试获取默认沙箱"""
        sandbox = get_sandbox()
        
        assert sandbox is not None
        assert isinstance(sandbox, SkillSandbox)

    def test_get_custom_sandbox(self):
        """测试获取自定义沙箱"""
        config = SandboxConfig(level=SandboxLevel.BASIC)
        sandbox = get_sandbox(config)
        
        assert sandbox.config.level == SandboxLevel.BASIC

    def test_singleton_for_default(self):
        """测试默认沙箱单例"""
        sandbox1 = get_sandbox()
        sandbox2 = get_sandbox()
        
        # 默认沙箱应该是单例
        assert sandbox1 is sandbox2
