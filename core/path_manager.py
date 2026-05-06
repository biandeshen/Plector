"""
PathManager - 集中管理 Plector 项目路径

提供统一的路径访问接口，解决硬编码路径问题
"""

from pathlib import Path


class PathManager:
    """Plector 项目路径管理器"""

    PROJECT_ROOT = Path(__file__).parent.parent.resolve()

    @classmethod
    def data_dir(cls) -> Path:
        """数据目录"""
        return cls.PROJECT_ROOT / "data"

    @classmethod
    def db_path(cls) -> Path:
        """数据库文件路径"""
        return cls.data_dir() / "plector.db"

    @classmethod
    def config_dir(cls) -> Path:
        """配置目录"""
        return cls.PROJECT_ROOT / "config"

    @classmethod
    def logs_dir(cls) -> Path:
        """日志目录"""
        return cls.data_dir() / "logs"

    @classmethod
    def cache_dir(cls) -> Path:
        """缓存目录"""
        return cls.data_dir() / "cache"

    @classmethod
    def workflows_dir(cls) -> Path:
        """工作流目录"""
        p = cls.PROJECT_ROOT / "servers" / "agency-orchestrator" / "workflows"
        return p if p.exists() else cls.PROJECT_ROOT / "workflows"

    @classmethod
    def is_safe_path(cls, user_path: str, base_dir: Path | None = None) -> bool:
        """校验路径是否安全（无目录穿越）"""
        if base_dir is None:
            base_dir = cls.PROJECT_ROOT
        try:
            resolved = (base_dir / user_path).resolve()
            return resolved.is_relative_to(base_dir.resolve())
        except (ValueError, OSError):
            return False
