"""
敏感信息加密管理器测试 - Plector v2.0 Phase 1
"""

import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.security.secrets_manager import (
    SecretScope,
    SecretEntry,
    SecretsManager,
)


class TestSecretsManager:
    """SecretsManager 测试"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """创建测试用 SecretsManager"""
        os.environ["PLECTOR_MASTER_KEY"] = "test-master-key-12345"
        storage = tmp_path / "secrets.enc"
        return SecretsManager(
            master_key="test-master-key-12345",
            storage_path=str(storage),
            auto_load=False
        )
    
    def test_store_and_retrieve(self, manager):
        """测试存储和检索"""
        result = manager.store("api_key", "sk-1234567890", SecretScope.MEDIUM)
        
        assert result["success"] is True
        assert result["data"]["mask_hint"] == "sk••••••••••"
    
    def test_retrieve_with_decrypt(self, manager):
        """测试解密检索"""
        manager.store("token", "secret-token-abc", SecretScope.HIGH)
        
        result = manager.retrieve("token", auto_decrypt=True)
        
        assert result["success"] is True
        assert result["data"] == "secret-token-abc"
    
    def test_retrieve_without_decrypt(self, manager):
        """测试不解密检索（返回掩码）"""
        manager.store("password", "mysecretpass", SecretScope.CRITICAL)
        
        result = manager.retrieve("password", auto_decrypt=False)
        
        assert result["success"] is True
        assert result["data"] == "••••••••••••"
    
    def test_delete(self, manager):
        """测试删除"""
        manager.store("key1", "value1", SecretScope.LOW)
        result = manager.delete("key1")
        
        assert result["success"] is True
        
        get_result = manager.retrieve("key1")
        assert get_result["success"] is False
    
    def test_list_keys(self, manager):
        """测试列出所有键"""
        manager.store("key1", "value1", SecretScope.LOW)
        manager.store("key2", "value2", SecretScope.HIGH)
        
        result = manager.list_keys()
        
        assert result["success"] is True
        assert len(result["data"]) == 2
    
    def test_mask_sensitive_data(self):
        """测试自动脱敏"""
        data = {
            "api_key": "sk-1234567890",
            "token": "Bearer abc123",
            "password": "secret123",
            "name": "test"
        }
        
        masked = SecretsManager.mask_sensitive_data(data)
        
        assert masked["api_key"] == "***KEY"
        assert masked["token"] == "Bearer ***"
        assert masked["password"] == "***PWD"
        assert masked["name"] == "test"


class TestSecretEntry:
    """SecretEntry 数据类测试"""
    
    def test_entry_creation(self):
        """测试条目创建"""
        entry = SecretEntry(
            key="test_key",
            encrypted_value="enc_data",
            scope=SecretScope.MEDIUM,
            salt="salt123",
            mask_hint="te••••••"
        )
        
        assert entry.key == "test_key"
        assert entry.scope == SecretScope.MEDIUM
