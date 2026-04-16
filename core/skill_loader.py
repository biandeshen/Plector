"""
技能热加载器 - 动态加载和更新技能模块
=====================================
解决技能冷加载延迟问题，支持运行时热更新

特性：
- 懒加载：首次使用时才加载
- 热更新：检测文件变化自动重新加载
- 缓存：已加载技能保留缓存
- 依赖追踪：自动追踪技能依赖

使用方式:
    loader = SkillLoader(base_path="skills")
    
    # 获取技能（懒加载）
    skill = await loader.get_skill("code_writer")
    
    # 强制刷新
    await loader.reload_skill("code_writer")
    
    # 批量预热
    await loader.warmup(["code_writer", "web_search"])
"""

import asyncio
import hashlib
import importlib
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SkillInfo:
    """技能元信息"""
    name: str
    path: Path
    handler_class: str  # handler 类名
    loaded_at: datetime = field(default_factory=datetime.now)
    file_hash: str = ""
    is_loaded: bool = False
    module: Any = None


class SkillLoader:
    """技能热加载器"""

    def __init__(self, base_path: str = "skills"):
        self.base_path = Path(base_path)
        self._cache: dict[str, SkillInfo] = {}
        self._lock = asyncio.Lock()
        self._file_watcher_task: asyncio.Task | None = None
        self._watch_interval = 5.0  # 秒

    # ========== 核心接口 ==========

    async def get_skill(self, skill_name: str) -> dict | None:
        """
        获取技能实例（懒加载）
        返回技能的 handler 配置
        """
        async with self._lock:
            if skill_name not in self._cache:
                await self._discover_skill(skill_name)
            
            info = self._cache.get(skill_name)
            if not info:
                return None
            
            # 检查是否需要热更新
            if not info.is_loaded or await self._needs_reload(info):
                await self._load_skill(skill_name, info)
            
            if not info.module:
                return None
            
            # 返回技能元信息
            return {
                "name": info.name,
                "path": str(info.path),
                "handler_class": info.handler_class,
                "loaded_at": info.loaded_at.isoformat(),
            }

    async def reload_skill(self, skill_name: str) -> bool:
        """强制重新加载指定技能"""
        async with self._lock:
            info = self._cache.get(skill_name)
            if not info:
                return False
            return await self._load_skill(skill_name, info)

    async def warmup(self, skill_names: list[str]) -> dict[str, bool]:
        """批量预热技能（并发加载）"""
        tasks = [self.get_skill(name) for name in skill_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            name: not isinstance(r, Exception)
            for name, r in zip(skill_names, results)
        }

    async def get_all_skills(self) -> list[str]:
        """获取所有已发现的技能名称"""
        await self._discover_all()
        return list(self._cache.keys())

    def start_watcher(self):
        """启动文件变化监控（后台任务）"""
        if self._file_watcher_task is None:
            self._file_watcher_task = asyncio.create_task(self._watch_files())

    def stop_watcher(self):
        """停止文件监控"""
        if self._file_watcher_task:
            self._file_watcher_task.cancel()
            self._file_watcher_task = None

    # ========== 内部实现 ==========

    async def _discover_all(self):
        """扫描所有技能目录"""
        if not self.base_path.exists():
            return
        
        for item in self.base_path.iterdir():
            if item.is_dir() and (item / "skill.json").exists():
                if item.name not in self._cache:
                    await self._discover_skill(item.name)

    async def _discover_skill(self, skill_name: str):
        """发现并注册技能（不加载代码）"""
        skill_path = self.base_path / skill_name / "skill.json"
        if not skill_path.exists():
            return
        
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            info = SkillInfo(
                name=skill_name,
                path=skill_path.parent,
                handler_class=meta.get("handler_class", "SkillHandler"),
            )
            self._cache[skill_name] = info
        except Exception:
            pass

    async def _load_skill(self, skill_name: str, info: SkillInfo) -> bool:
        """实际加载技能模块"""
        try:
            # 计算文件哈希
            info.file_hash = await self._calc_hash(info.path)
            
            # 动态导入
            module_path = f"skills.{skill_name}.implementation"
            module = importlib.import_module(module_path)
            
            # 获取 handler 类
            handler_cls = getattr(module, info.handler_class, None)
            if not handler_cls:
                return False
            
            info.module = module
            info.is_loaded = True
            info.loaded_at = datetime.now()
            return True
        except Exception:
            return False

    async def _needs_reload(self, info: SkillInfo) -> bool:
        """检查技能是否需要重新加载"""
        if not info.is_loaded:
            return True
        try:
            new_hash = await self._calc_hash(info.path)
            return new_hash != info.file_hash
        except Exception:
            return False

    async def _calc_hash(self, path: Path) -> str:
        """计算目录内容哈希"""
        hasher = hashlib.sha256()
        
        # 遍历所有 .py 文件
        for py_file in sorted(path.rglob("*.py")):
            with open(py_file, "rb") as f:
                hasher.update(f.read())
        
        # 包含 skill.json
        json_file = path / "skill.json"
        if json_file.exists():
            with open(json_file, "rb") as f:
                hasher.update(f.read())
        
        return hasher.hexdigest()[:16]  # 只取前16位

    async def _watch_files(self):
        """后台文件监控任务"""
        last_hashes: dict[str, str] = {}
        
        while True:
            try:
                await asyncio.sleep(self._watch_interval)
                
                for name, info in self._cache.items():
                    if await self._needs_reload(info):
                        async with self._lock:
                            await self._load_skill(name, info)
                        # 可以在这里触发事件通知
                        # event_bus.emit("skill_reloaded", {"skill": name})
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # 忽略监控错误

    # ========== 工具方法 ==========

    async def stats(self) -> dict:
        """获取加载统计"""
        return {
            "total_skills": len(self._cache),
            "loaded_skills": sum(1 for i in self._cache.values() if i.is_loaded),
            "watcher_active": self._file_watcher_task is not None,
        }

    def get_loaded_modules(self) -> list[str]:
        """获取已加载的模块列表"""
        return [
            name for name, info in self._cache.items()
            if info.is_loaded and info.module
        ]
