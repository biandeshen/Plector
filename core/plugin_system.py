"""插件系统

职责：支持动态加载和卸载插件，扩展系统功能
遵循规则：函数不超过 50 行
"""

import importlib
import importlib.util
import importlib.abc
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str = ""
    hooks: List[str] = field(default_factory=list)
    module: Optional[Any] = None


@dataclass
class PluginHook:
    """插件钩子定义"""
    name: str
    callback: Callable
    priority: int = 0  # 优先级，数值越大越先执行


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self):
        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[str, List[PluginHook]] = {}
    
    def register(self, plugin: PluginInfo) -> None:
        """注册插件"""
        if plugin.name in self._plugins:
            raise ValueError(f"插件已存在: {plugin.name}")
        self._plugins[plugin.name] = plugin
    
    def unregister(self, name: str) -> None:
        """注销插件"""
        if name not in self._plugins:
            raise KeyError(f"插件不存在: {name}")
        
        # 移除插件
        del self._plugins[name]
        
        # 移除关联的钩子
        for hook_list in self._hooks.values():
            hook_list[:] = [h for h in hook_list if h.callback.__self__ != name]
    
    def get(self, name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugins.get(name)
    
    def list_all(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self._plugins.values())
    
    def register_hook(self, plugin_name: str, hook_name: str, callback: Callable, priority: int = 0) -> None:
        """注册插件钩子"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        
        hook = PluginHook(name=plugin_name, callback=callback, priority=priority)
        self._hooks[hook_name].append(hook)
        
        # 按优先级排序
        self._hooks[hook_name].sort(key=lambda h: -h.priority)
    
    def call_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """调用钩子"""
        if hook_name not in self._hooks:
            return []
        
        results = []
        for hook in self._hooks[hook_name]:
            try:
                result = hook.callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"[Plugin] Hook {hook_name} failed: {e}")
        
        return results


class PluginLoader:
    """插件加载器"""
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self._loaders: Dict[str, Any] = {}
    
    def load_file(self, path: str | Path) -> PluginInfo:
        """从文件加载插件"""
        path = Path(path)
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载插件: {path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 获取插件信息
        plugin_info = self._extract_plugin_info(module)
        plugin_info.module = module
        
        # 注册插件
        self.registry.register(plugin_info)
        self._loaders[plugin_info.name] = module
        
        # 注册钩子
        self._register_hooks(plugin_info)
        
        return plugin_info
    
    def load_directory(self, directory: str | Path) -> List[PluginInfo]:
        """从目录批量加载插件"""
        directory = Path(directory)
        
        if not directory.exists():
            return []
        
        plugins = []
        for path in directory.glob("*.py"):
            if path.name.startswith("_"):
                continue
            try:
                plugin = self.load_file(path)
                plugins.append(plugin)
            except Exception as e:
                print(f"[PluginLoader] Failed to load {path}: {e}")
        
        return plugins
    
    def unload(self, name: str) -> None:
        """卸载插件"""
        self.registry.unregister(name)
        if name in self._loaders:
            del self._loaders[name]
    
    def _extract_plugin_info(self, module: Any) -> PluginInfo:
        """从模块提取插件信息"""
        info = PluginInfo(
            name=getattr(module, "PLUGIN_NAME", module.__name__),
            version=getattr(module, "PLUGIN_VERSION", "1.0.0"),
            description=getattr(module, "PLUGIN_DESCRIPTION", ""),
            author=getattr(module, "PLUGIN_AUTHOR", ""),
            hooks=getattr(module, "PLUGIN_HOOKS", []),
        )
        return info
    
    def _register_hooks(self, plugin: PluginInfo) -> None:
        """注册插件钩子"""
        if plugin.module is None:
            return
        
        # 查找所有以 "hook_" 开头的函数
        for attr_name in dir(plugin.module):
            if attr_name.startswith("hook_"):
                attr = getattr(plugin.module, attr_name)
                if callable(attr):
                    hook_name = attr_name[5:]  # 去掉 "hook_" 前缀
                    self.registry.register_hook(
                        plugin.name,
                        hook_name,
                        attr,
                        priority=getattr(attr, "priority", 0),
                    )


# ========== 内置钩子定义 ==========

class SystemHooks:
    """系统内置钩子"""
    
    # 生命周期钩子
    ON_STARTUP = "system.startup"
    ON_SHUTDOWN = "system.shutdown"
    
    # 事件钩子
    ON_EVENT = "event.on_event"
    ON_ERROR = "event.on_error"
    
    # 技能钩子
    SKILL_LOADED = "skill.loaded"
    SKILL_UNLOADED = "skill.unloaded"
    
    # LLM 钩子
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"


# ========== 全局实例 ==========

_global_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """获取全局插件注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def get_loader() -> PluginLoader:
    """获取全局插件加载器"""
    return PluginLoader(get_registry())
