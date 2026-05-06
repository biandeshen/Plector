"""
Tests for core.security.secrets_manager

Tests cover:
- SecretScope enum
- SecretEntry dataclass
- SecretsManager store/retrieve/delete
- Encryption guarantees
- Scope filtering
- Serialization roundtrip
- Singleton behavior
- Error handling
"""

import json
import os
import tempfile

import pytest

from core.security.secrets_manager import SecretEntry, SecretScope, SecretsManager

TEST_MASTER_KEY = "test-master-key-42"


# ─── SecretScope ─────────────────────────────────────────


class TestSecretScope:
    def test_enum_values(self):
        assert SecretScope.LOW.value == "low"
        assert SecretScope.MEDIUM.value == "medium"
        assert SecretScope.HIGH.value == "high"
        assert SecretScope.CRITICAL.value == "critical"

    def test_enum_members(self):
        assert SecretScope.LOW in SecretScope
        assert SecretScope.MEDIUM in SecretScope
        assert SecretScope.HIGH in SecretScope
        assert SecretScope.CRITICAL in SecretScope


# ─── SecretEntry ────────────────────────────────────────


class TestSecretEntry:
    def test_create_entry(self):
        entry = SecretEntry(
            key="api_key",
            encrypted_value="encrypted123",
            scope=SecretScope.HIGH,
            salt="abcd",
            mask_hint="abc******xyz",
            metadata={"source": "env"},
        )
        assert entry.key == "api_key"
        assert entry.encrypted_value == "encrypted123"
        assert entry.scope == SecretScope.HIGH
        assert entry.salt == "abcd"
        assert entry.mask_hint == "abc******xyz"
        assert entry.metadata == {"source": "env"}

    def test_create_entry_default_metadata(self):
        entry = SecretEntry(
            key="simple",
            encrypted_value="val",
            scope=SecretScope.LOW,
            salt="salt",
            mask_hint="hint",
        )
        assert entry.metadata == {}


# ─── SecretsManager ─────────────────────────────────────


@pytest.fixture
def temp_storage():
    """Provide a temporary file path for secrets storage."""
    with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def manager(temp_storage):
    """SecretsManager with a known master key and temp storage."""
    m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=temp_storage, auto_load=False)
    return m


class TestSecretsManagerInit:
    def test_init_without_key_creates_no_cipher(self, temp_storage):
        m = SecretsManager(master_key=None, storage_path=temp_storage, auto_load=False)
        assert m._cipher is None

    def test_init_with_key_creates_cipher(self, temp_storage):
        m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=temp_storage, auto_load=False)
        assert m._cipher is not None

    def test_init_loads_existing_data(self):
        """auto_load=True loads existing data from file."""
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False, mode="w") as f:
            data = {
                "entries": {
                    "existing": {
                        "key": "existing",
                        "encrypted_value": "dummy",
                        "scope": "low",
                        "salt": "salt",
                        "mask_hint": "hint",
                        "metadata": {},
                    }
                }
            }
            json.dump(data, f)
            path = f.name

        m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=path, auto_load=True)
        try:
            assert "existing" in m._entries
            assert m._entries["existing"].key == "existing"
            assert m._entries["existing"].scope == SecretScope.LOW
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_singleton(self, manager):
        """get_instance returns the last created instance."""
        instance = SecretsManager.get_instance()
        assert instance is manager

    def test_singleton_default_constructor(self, temp_storage):
        """get_instance creates a new instance if none exists."""
        m1 = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=temp_storage, auto_load=False)
        assert SecretsManager.get_instance() is m1


class TestSecretsManagerStore:
    def test_store_success(self, manager):
        result = manager.store("api_key", "sk-abc123", scope=SecretScope.MEDIUM)
        assert result["success"] is True
        assert result["data"]["key"] == "api_key"
        assert result["error"] is None
        assert "mask_hint" in result["data"]

    def test_store_fails_without_cipher(self, temp_storage):
        m = SecretsManager(master_key=None, storage_path=temp_storage, auto_load=False)
        result = m.store("some_key", "secret_value")
        assert result["success"] is False
        assert result["error"] == "加密未初始化，缺少 master_key"

    def test_store_with_metadata(self, manager):
        result = manager.store("db_pass", "s3cret!", scope=SecretScope.HIGH, env="prod", rotated_at="2025-01-01")
        assert result["success"] is True
        entry = manager._entries["db_pass"]
        assert entry.metadata["env"] == "prod"
        assert entry.metadata["rotated_at"] == "2025-01-01"

    def test_store_critical_masked(self, manager):
        manager.store("root_pw", "super-secret-password", scope=SecretScope.CRITICAL)
        entry = manager._entries["root_pw"]
        assert entry.mask_hint == "\u2022" * 12

    def test_store_overwrites_existing(self, manager):
        manager.store("key1", "value1", scope=SecretScope.LOW)
        manager.store("key1", "value2", scope=SecretScope.HIGH)
        entry = manager._entries["key1"]
        assert entry.scope == SecretScope.HIGH

    def test_encrypted_value_not_plaintext(self, manager):
        """Verify that the stored encrypted value is not equal to the original."""
        manager.store("secret", "my-sensitive-data", scope=SecretScope.MEDIUM)
        entry = manager._entries["secret"]
        assert entry.encrypted_value != "my-sensitive-data"
        # Fernet tokens are base64 encoded (alphanumeric plus - and _)
        assert len(entry.encrypted_value) > 0

    def test_store_different_keys_encrypt_differently(self, manager):
        """Two store calls with the same plaintext produce different ciphertexts."""
        manager.store("a", "same-value", scope=SecretScope.LOW)
        manager.store("b", "same-value", scope=SecretScope.LOW)
        entry_a = manager._entries["a"]
        entry_b = manager._entries["b"]
        assert entry_a.encrypted_value != entry_b.encrypted_value  # due to random salt


class TestSecretsManagerRetrieve:
    def test_retrieve_decrypts_correctly(self, manager):
        manager.store("api_key", "sk-abc123", scope=SecretScope.MEDIUM)
        result = manager.retrieve("api_key")
        assert result["success"] is True
        assert result["data"] == "sk-abc123"
        assert result["error"] is None

    def test_retrieve_nonexistent_key(self, manager):
        result = manager.retrieve("does_not_exist")
        assert result["success"] is False
        assert result["data"] is None
        assert "未找到" in result["error"]

    def test_retrieve_mask_hint(self, manager):
        """auto_decrypt=False returns the mask hint."""
        manager.store("token", "my-secret-token-42", scope=SecretScope.HIGH)
        result = manager.retrieve("token", auto_decrypt=False)
        assert result["success"] is True
        # HIGH mask: first 4 chars + bullets + last 4 chars
        value = "my-secret-token-42"
        expected_mask = value[:4] + "\u2022" * (len(value) - 8) + value[-4:]
        assert result["data"] == expected_mask

    def test_retrieve_without_cipher(self, temp_storage):
        m = SecretsManager(master_key=None, storage_path=temp_storage, auto_load=False)
        # Manually insert an entry (since store won't work without cipher)
        m._entries["key1"] = SecretEntry(
            key="key1",
            encrypted_value="dummy",
            scope=SecretScope.LOW,
            salt="salt",
            mask_hint="hint",
        )
        result = m.retrieve("key1")
        assert result["success"] is False
        assert result["error"] == "加密未初始化"

    def test_retrieve_roundtrip_unicode(self, manager):
        """Unicode values survive encryption/decryption."""
        value = "你好世界! 🎉"
        manager.store("unicode", value, scope=SecretScope.LOW)
        result = manager.retrieve("unicode")
        assert result["data"] == value


class TestSecretsManagerDelete:
    def test_delete_existing(self, manager):
        manager.store("temp_key", "temp_value")
        result = manager.delete("temp_key")
        assert result["success"] is True
        assert "temp_key" not in manager._entries

    def test_delete_nonexistent(self, manager):
        result = manager.delete("no_such_key")
        assert result["success"] is False
        assert "未找到" in result["error"]

    def test_delete_removes_from_file(self, manager):
        """After delete, the entry should not appear in the serialized file."""
        manager.store("keep", "keep_val")
        manager.store("remove", "remove_val")
        manager.delete("remove")
        # Load the file directly
        assert os.path.exists(manager._storage_path)
        with open(manager._storage_path) as f:
            data = json.load(f)
        assert "keep" in data["entries"]
        assert "remove" not in data["entries"]


class TestSecretsManagerListKeys:
    def test_list_keys_empty(self, manager):
        result = manager.list_keys()
        assert result["success"] is True
        assert result["data"] == []

    def test_list_keys_all(self, manager):
        manager.store("key1", "val1", scope=SecretScope.LOW)
        manager.store("key2", "val2", scope=SecretScope.MEDIUM)
        result = manager.list_keys()
        keys = {item["key"] for item in result["data"]}
        assert keys == {"key1", "key2"}

    def test_list_keys_filtered(self, manager):
        manager.store("low_key", "v1", scope=SecretScope.LOW)
        manager.store("med_key", "v2", scope=SecretScope.MEDIUM)
        manager.store("high_key", "v3", scope=SecretScope.HIGH)

        result = manager.list_keys(scope=SecretScope.MEDIUM)
        assert len(result["data"]) == 1
        assert result["data"][0]["key"] == "med_key"

    def test_list_keys_filter_no_match(self, manager):
        result = manager.list_keys(scope=SecretScope.CRITICAL)
        assert result["data"] == []


class TestSecretsManagerMask:
    def _mask(self, value, scope):
        """Helper to call the instance method _mask via a temporary manager."""
        import tempfile

        m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=tempfile.mktemp(suffix=".enc"), auto_load=False)
        return m._mask(value, scope)

    def test_mask_low_short_value(self):
        """LOW with value <= 4 chars returns 4 bullets."""
        result = self._mask("ab", SecretScope.LOW)
        assert result == "\u2022" * 4

    def test_mask_low_long_value(self):
        """LOW: first 2 + bullets + last 2."""
        result = self._mask("abcdefgh", SecretScope.LOW)
        assert result == "ab" + "\u2022" * 4 + "gh"

    def test_mask_high_short_value(self):
        """HIGH with value <= 8 returns 6 bullets."""
        result = self._mask("12345678", SecretScope.HIGH)
        assert result == "\u2022" * 6

    def test_mask_high_long_value(self):
        """HIGH: first 4 + bullets + last 4."""
        result = self._mask("abcdefghijklm", SecretScope.HIGH)
        assert result == "abcd" + "\u2022" * 5 + "jklm"

    def test_mask_critical(self):
        """CRITICAL always returns 12 bullets."""
        result = self._mask("anything", SecretScope.CRITICAL)
        assert result == "\u2022" * 12


class TestSecretsManagerMaskSensitiveData:
    def test_mask_string_with_api_key(self):
        data = '{"api_key": "sk-1234567890abcdef"}'
        result = SecretsManager.mask_sensitive_data(data)
        assert "sk-1234567890abcdef" not in result
        assert "***KEY" in result

    def test_mask_string_with_token(self):
        data = 'token = "mysecrettoken123"'
        result = SecretsManager.mask_sensitive_data(data)
        assert "mysecrettoken123" not in result
        assert "***TOKEN" in result

    def test_mask_string_with_password(self):
        data = 'password: "hunter2"'
        result = SecretsManager.mask_sensitive_data(data)
        assert "hunter2" not in result
        assert "***PWD" in result

    def test_mask_dict(self):
        """Dict values are recursively masked. The regex replaces the entire matched pattern."""
        data = {"config": "api_key=sk-xxx", "normal": "hello"}
        result = SecretsManager.mask_sensitive_data(data)
        assert result["config"] == "***KEY"
        assert result["normal"] == "hello"

    def test_mask_list(self):
        data = ["api_key=abc123", "other"]
        result = SecretsManager.mask_sensitive_data(data)
        assert "***KEY" in result[0]

    def test_mask_non_string_non_dict(self):
        result = SecretsManager.mask_sensitive_data(42)
        assert result == 42

    def test_mask_with_custom_patterns(self):
        data = "secret=custom_value"
        patterns = [(r"secret\s*=\s*([^\s]+)", "***CUSTOM")]
        result = SecretsManager.mask_sensitive_data(data, patterns)
        assert "custom_value" not in result
        assert "***CUSTOM" in result


class TestSecretsManagerSerialization:
    def test_store_persists_to_file(self, manager):
        manager.store("persist_key", "persist_val")
        assert os.path.exists(manager._storage_path)
        with open(manager._storage_path) as f:
            data = json.load(f)
        assert "persist_key" in data["entries"]
        assert data["entries"]["persist_key"]["scope"] == "medium"

    def test_load_restores_entries(self, manager):
        """Store data, create a new manager pointing to same file, verify load."""
        manager.store("roundtrip_key", "roundtrip_val", scope=SecretScope.HIGH)
        storage_path = manager._storage_path

        m2 = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=storage_path, auto_load=True)
        assert "roundtrip_key" in m2._entries
        assert m2._entries["roundtrip_key"].scope == SecretScope.HIGH

    def test_decrypt_after_load(self, manager):
        """Stored data can be decrypted after a fresh load from file."""
        manager.store("load_test", "hello-after-load", scope=SecretScope.MEDIUM)
        storage_path = manager._storage_path

        m2 = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=storage_path, auto_load=True)
        result = m2.retrieve("load_test")
        assert result["success"] is True
        assert result["data"] == "hello-after-load"

    def test_load_nonexistent_file_no_error(self, temp_storage):
        """Loading from a non-existent path should be a no-op."""
        m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=temp_storage, auto_load=True)
        assert m._entries == {}

    def test_load_corrupted_file_no_crash(self, temp_storage):
        """Loading a corrupted file should log warning but not crash."""
        with open(temp_storage, "w") as f:
            f.write("not valid json")
        m = SecretsManager(master_key=TEST_MASTER_KEY, storage_path=temp_storage, auto_load=True)
        assert m._entries == {}


class TestSecretsManagerEdgeCases:
    def test_store_empty_string(self, manager):
        result = manager.store("empty", "")
        assert result["success"] is True
        retrieved = manager.retrieve("empty")
        assert retrieved["data"] == ""

    def test_store_long_value(self, manager):
        long_val = "x" * 10000
        result = manager.store("long", long_val)
        assert result["success"] is True
        retrieved = manager.retrieve("long")
        assert retrieved["data"] == long_val

    def test_retrieve_wrong_key_decryption(self, manager):
        """Manually inserting wrong encrypted data should fail decryption."""
        manager.store("original", "real_value")
        # Tamper with the encrypted value
        manager._entries["original"].encrypted_value = "gAAAAABinvalid=="
        result = manager.retrieve("original")
        assert result["success"] is False
        assert result["error"] is not None
