"""
敏感信息加密管理器 - Plector v2.0 Phase 1
统一管理所有敏感信息（API Key、Token、密码等）的加密存储和访问
"""

import base64
import contextlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


class SecretScope(Enum):
    """敏感信息安全级别"""

    LOW = "low"  # 普通配置
    MEDIUM = "medium"  # API Key
    HIGH = "high"  # 认证凭据
    CRITICAL = "critical"  # 主密钥


@dataclass
class SecretEntry:
    """敏感信息条目"""

    key: str
    encrypted_value: str
    scope: SecretScope
    salt: str
    mask_hint: str  # 用于UI显示的掩码提示
    metadata: dict = field(default_factory=dict)


class SecretsManager:
    """
    敏感信息加密管理器

    功能：
    1. Fernet 对称加密存储
    2. PBKDF2 密钥派生
    3. 敏感信息自动脱敏
    4. 支持内存安全模式
    """

    _instance: Optional["SecretsManager"] = None

    def __init__(self, master_key: str | None = None, storage_path: str = "config/secrets.enc", auto_load: bool = True):
        self._storage_path = storage_path
        self._entries: dict[str, SecretEntry] = {}
        self._cipher: Fernet | None = None
        self._master_key = master_key or os.getenv("PLECTOR_MASTER_KEY")

        if HAS_CRYPTO and self._master_key:
            self._cipher = self._create_cipher(self._master_key, b"plector-secrets")

        if auto_load:
            self._load()

        SecretsManager._instance = self

    @classmethod
    def get_instance(cls) -> "SecretsManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _create_cipher(self, key: str, salt: bytes) -> Fernet:
        """使用 PBKDF2 派生加密密钥"""
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        derived = kdf.derive(key.encode())
        return Fernet(base64.urlsafe_b64encode(derived))

    def _encrypt(self, value: str) -> tuple[str, str]:
        """加密敏感值，返回 (加密数据, 盐)"""
        salt = os.urandom(16)
        cipher = self._create_cipher(self._master_key, salt)
        encrypted = cipher.encrypt(value.encode()).decode()
        return encrypted, base64.b64encode(salt).decode()

    def _decrypt(self, encrypted: str, salt: str) -> str:
        """解密敏感值"""
        cipher = self._create_cipher(self._master_key, base64.b64decode(salt))
        return cipher.decrypt(encrypted.encode()).decode()

    def _mask(self, value: str, scope: SecretScope) -> str:
        """生成掩码提示"""
        if scope == SecretScope.CRITICAL:
            return "••••••••••••"
        elif scope == SecretScope.HIGH:
            return f"{value[:4]}{'•' * (len(value) - 8)}{value[-4:]}" if len(value) > 8 else "••••••"
        else:
            return f"{value[:2]}{'•' * (len(value) - 4)}{value[-2:]}" if len(value) > 4 else "••••"

    def store(self, key: str, value: str, scope: SecretScope = SecretScope.MEDIUM, **metadata) -> dict:
        """
        存储敏感信息

        Args:
            key: 键名
            value: 敏感值
            scope: 安全级别
            **metadata: 额外元数据

        Returns:
            {"success": bool, "data": {"key": str, "mask_hint": str}, "error": str|None}
        """
        if not self._cipher:
            return {"success": False, "data": None, "error": "加密未初始化，缺少 master_key"}

        try:
            encrypted, salt = self._encrypt(value)
            entry = SecretEntry(
                key=key,
                encrypted_value=encrypted,
                scope=scope,
                salt=salt,
                mask_hint=self._mask(value, scope),
                metadata=metadata,
            )
            self._entries[key] = entry
            self._save()
            return {"success": True, "data": {"key": key, "mask_hint": entry.mask_hint}, "error": None}
        except Exception as e:
            logger.error(f"存储敏感信息失败: {key}, {e}")
            return {"success": False, "data": None, "error": str(e)}

    def retrieve(self, key: str, auto_decrypt: bool = True) -> dict:
        """
        获取敏感信息

        Args:
            key: 键名
            auto_decrypt: 是否自动解密

        Returns:
            {"success": bool, "data": value|None, "error": str|None}
        """
        entry = self._entries.get(key)
        if not entry:
            return {"success": False, "data": None, "error": f"未找到: {key}"}

        if not auto_decrypt:
            return {"success": True, "data": entry.mask_hint, "error": None}

        if not self._cipher:
            return {"success": False, "data": None, "error": "加密未初始化"}

        try:
            value = self._decrypt(entry.encrypted_value, entry.salt)
            return {"success": True, "data": value, "error": None}
        except Exception as e:
            logger.error(f"解密失败: {key}, {e}")
            return {"success": False, "data": None, "error": str(e)}

    def delete(self, key: str) -> dict:
        """删除敏感信息"""
        if key not in self._entries:
            return {"success": False, "data": None, "error": f"未找到: {key}"}

        del self._entries[key]
        self._save()
        return {"success": True, "data": {"key": key}, "error": None}

    def list_keys(self, scope: SecretScope | None = None) -> dict:
        """列出所有键名（掩码形式）"""
        entries = self._entries.values()
        if scope:
            entries = [e for e in entries if e.scope == scope]

        return {
            "success": True,
            "data": [{"key": e.key, "mask_hint": e.mask_hint, "scope": e.scope.value} for e in entries],
            "error": None,
        }

    @staticmethod
    def mask_sensitive_data(data: Any, patterns: list[str] = None) -> Any:
        """
        自动脱敏敏感数据

        Args:
            data: 输入数据
            patterns: 自定义匹配模式

        Returns:
            脱敏后的数据
        """
        patterns = patterns or [
            (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', "***KEY"),
            (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', "***TOKEN"),
            (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', "***PWD"),
            (r"Bearer\s+([a-zA-Z0-9\-_.]+)", "Bearer ***"),
        ]

        if isinstance(data, str):
            result = data
            for pattern, replacement in patterns:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            return result
        elif isinstance(data, dict):
            return {k: SecretsManager.mask_sensitive_data(v, patterns) for k, v in data.items()}
        elif isinstance(data, list | tuple):
            return [SecretsManager.mask_sensitive_data(item, patterns) for item in data]
        return data

    def _load(self) -> None:
        """从文件加载加密数据"""
        if not os.path.exists(self._storage_path):
            return

        try:
            with open(self._storage_path) as f:
                data = json.load(f)

            for key, entry_data in data.get("entries", {}).items():
                if "scope" in entry_data and isinstance(entry_data["scope"], str):
                    entry_data["scope"] = SecretScope(entry_data["scope"])
                self._entries[key] = SecretEntry(**entry_data)

            logger.info(f"已加载 {len(self._entries)} 条敏感信息")
        except Exception as e:
            logger.warning(f"加载敏感信息失败: {e}")

    def _save(self) -> None:
        """保存加密数据到文件"""
        os.makedirs(os.path.dirname(self._storage_path) or ".", exist_ok=True)

        data = {
            "entries": {
                key: {
                    "key": e.key,
                    "encrypted_value": e.encrypted_value,
                    "scope": e.scope,
                    "salt": e.salt,
                    "mask_hint": e.mask_hint,
                    "metadata": e.metadata,
                }
                for key, e in self._entries.items()
            }
        }

        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        with contextlib.suppress(OSError):
            os.chmod(self._storage_path, 0o600)
