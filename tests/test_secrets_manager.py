"""
敏感信息管理器单元测试 - Plector v2.0 Phase 1
"""

import os
import pytest
from core.security.secrets_manager import (
    SecretsManager,
    get_secrets_manager,
)


class TestSecretsManager:
    """测试敏感信息管理器"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建管理器实例"""
        storage_file = tmp_path / "secrets.json"
        return SecretsManager(storage_path=str(storage_file))

    def test_set_and_get(self, manager):
        """测试设置和获取"""
        manager.set("api_key", "secret123")
        
        value = manager.get("api_key")
        
        assert value == "secret123"

    def test_get_nonexistent(self, manager):
        """测试获取不存在的密钥"""
        value = manager.get("nonexistent")
        
        assert value is None

    def test_get_with_default(self, manager):
        """测试获取默认值"""
        value = manager.get("nonexistent", default="default_value")
        
        assert value == "default_value"

    def test_exists(self, manager):
        """测试密钥存在检查"""
        manager.set("test_key", "test_value")
        
        assert manager.exists("test_key")
        assert not manager.exists("nonexistent")

    def test_delete(self, manager):
        """测试删除密钥"""
        manager.set("to_delete", "value")
        
        result = manager.delete("to_delete")
        
        assert result is True
        assert not manager.exists("to_delete")

    def test_delete_nonexistent(self, manager):
        """测试删除不存在的密钥"""
        result = manager.delete("nonexistent")
        
        assert result is False

    def test_list_names(self, manager):
        """测试列出密钥名称"""
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        
        names = manager.list_names()
        
        assert "key1" in names
        assert "key2" in names
        assert len(names) == 2

    def test_verify(self, manager):
        """测试密钥验证"""
        manager.set("password", "correct_password")
        
        assert manager.verify("password", "correct_password")
        assert not manager.verify("password", "wrong_password")

    def test_persistence(self, manager, tmp_path):
        """测试持久化"""
        manager.set("persistent_key", "persistent_value")
        
        # 创建新实例
        storage_file = tmp_path / "secrets.json"
        new_manager = SecretsManager(storage_path=str(storage_file))
        
        value = new_manager.get("persistent_key")
        
        assert value == "persistent_value"

    def test_metadata(self, manager):
        """测试元数据"""
        manager.set("key", "value", metadata={"env": "test", "source": "unit_test"})
        
        entry = manager._secrets["key"]
        
        assert entry.metadata["env"] == "test"
        assert entry.metadata["source"] == "unit_test"

    def test_encryption(self, manager):
        """测试加密"""
        manager.set("sensitive", "my_secret_data")
        
        # 检查原始存储不含明文
        entry = manager._secrets["sensitive"]
        
        assert entry.encrypted_value != "my_secret_data"
        assert "my_secret_data" not in entry.encrypted_value


class TestSecretsManagerEnvFile:
    """测试环境变量文件加载"""

    @pytest.fixture
    def env_file(self, tmp_path):
        """创建临时 .env 文件"""
        env_path = tmp_path / ".env"
        env_path.write_text('''
# API Keys
OPENAI_API_KEY=sk-test-openai
ANTHROPIC_API_KEY=sk-ant-test

# Database
DB_PASSWORD=super_secret_db_password

# Comments should be ignored
# PRIVATE_KEY=should_be_ignored
''')
        return str(env_path)

    def test_load_env_file(self, manager, env_file):
        """测试加载环境文件"""
        count = manager.load_env_file(env_file)
        
        assert count == 3  # 3 个非注释的密钥
        
        assert manager.get("OPENAI_API_KEY") == "sk-test-openai"
        assert manager.get("DB_PASSWORD") == "super_secret_db_password"

    def test_load_nonexistent_env_file(self, manager):
        """测试加载不存在的环境文件"""
        count = manager.load_env_file("/nonexistent/.env")
        
        assert count == 0


class TestGetSecretsManager:
    """测试全局实例"""

    def test_singleton(self):
        """测试单例模式"""
        # 注意：需要重置全局实例
        import core.security.secrets_manager as module
        module._instance = None
        
        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()
        
        assert manager1 is manager2
