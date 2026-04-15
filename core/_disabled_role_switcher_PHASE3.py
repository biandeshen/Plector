"""动态角色切换

职责：支持运行时动态切换 AI Agent 角色，支持角色池管理
遵循规则：函数不超过 50 行
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading


class RoleType(Enum):
    """角色类型"""
    ENGINEER = "engineer"
    PRODUCT = "product"
    DESIGN = "design"
    TESTING = "testing"
    MARKETING = "marketing"
    SUPPORT = "support"
    CUSTOM = "custom"


@dataclass
class Role:
    """角色定义"""
    name: str
    type: RoleType
    description: str
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleContext:
    """角色上下文"""
    role: Role
    session_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=0)


class RoleSwitcher:
    """动态角色切换器"""
    
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._active_contexts: Dict[str, RoleContext] = {}
        self._role_factories: Dict[str, Callable[[], Role]] = {}
        self._lock = threading.RLock()
        
        # 注册内置角色
        self._register_builtin_roles()
    
    # ========== 角色注册 ==========
    
    def register_role(self, role: Role) -> None:
        """注册角色"""
        with self._lock:
            self._roles[role.name] = role
    
    def register_factory(self, name: str, factory: Callable[[], Role]) -> None:
        """注册角色工厂"""
        with self._lock:
            self._role_factories[name] = factory
    
    def unregister_role(self, name: str) -> None:
        """注销角色"""
        with self._lock:
            if name in self._roles:
                del self._roles[name]
    
    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        with self._lock:
            # 尝试直接获取
            if name in self._roles:
                return self._roles[name]
            
            # 尝试通过工厂创建
            if name in self._role_factories:
                role = self._role_factories[name]()
                self._roles[name] = role
                return role
            
            return None
    
    def list_roles(self, role_type: Optional[RoleType] = None) -> List[Role]:
        """列出角色"""
        with self._lock:
            roles = list(self._roles.values())
            
            if role_type:
                roles = [r for r in roles if r.type == role_type]
            
            return roles
    
    # ========== 上下文管理 ==========
    
    def activate(self, session_id: str, role_name: str) -> RoleContext:
        """激活角色上下文"""
        with self._lock:
            role = self.get_role(role_name)
            if role is None:
                raise ValueError(f"角色不存在: {role_name}")
            
            ctx = RoleContext(
                role=role,
                session_id=session_id,
                state={},
            )
            self._active_contexts[session_id] = ctx
            
            return ctx
    
    def deactivate(self, session_id: str) -> None:
        """停用角色上下文"""
        with self._lock:
            if session_id in self._active_contexts:
                del self._active_contexts[session_id]
    
    def get_context(self, session_id: str) -> Optional[RoleContext]:
        """获取角色上下文"""
        with self._lock:
            return self._active_contexts.get(session_id)
    
    def switch_role(self, session_id: str, new_role_name: str) -> RoleContext:
        """切换角色"""
        with self._lock:
            # 获取新角色
            new_role = self.get_role(new_role_name)
            if new_role is None:
                raise ValueError(f"角色不存在: {new_role_name}")
            
            # 获取或创建上下文
            ctx = self._active_contexts.get(session_id)
            if ctx:
                # 保留状态
                old_state = ctx.state
                ctx = RoleContext(
                    role=new_role,
                    session_id=session_id,
                    state=old_state,
                )
            else:
                ctx = RoleContext(
                    role=new_role,
                    session_id=session_id,
                    state={},
                )
            
            self._active_contexts[session_id] = ctx
            return ctx
    
    # ========== 状态管理 ==========
    
    def set_state(self, session_id: str, key: str, value: Any) -> None:
        """设置上下文状态"""
        with self._lock:
            ctx = self._active_contexts.get(session_id)
            if ctx is None:
                raise ValueError(f"会话上下文不存在: {session_id}")
            ctx.state[key] = value
    
    def get_state(self, session_id: str, key: str, default: Any = None) -> Any:
        """获取上下文状态"""
        with self._lock:
            ctx = self._active_contexts.get(session_id)
            if ctx is None:
                return default
            return ctx.state.get(key, default)
    
    # ========== 内置角色 ==========
    
    def _register_builtin_roles(self) -> None:
        """注册内置角色"""
        builtin_roles = [
            Role(
                name="coder",
                type=RoleType.ENGINEER,
                description="代码开发专家",
                system_prompt="你是一个经验丰富的软件工程师，擅长编写高质量的代码。",
                capabilities=["coding", "refactoring", "debugging"],
            ),
            Role(
                name="reviewer",
                type=RoleType.ENGINEER,
                description="代码审查专家",
                system_prompt="你是一个严谨的代码审查专家，注重代码质量和安全性。",
                capabilities=["code_review", "security_audit", "performance_analysis"],
            ),
            Role(
                name="pm",
                type=RoleType.PRODUCT,
                description="产品经理",
                system_prompt="你是一个优秀的产品经理，擅长需求分析和产品规划。",
                capabilities=["requirements", "planning", "prioritization"],
            ),
        ]
        
        for role in builtin_roles:
            self.register_role(role)


# ========== 角色池管理 ==========

class RolePool:
    """角色池 - 管理多个角色实例"""
    
    def __init__(self, switcher: RoleSwitcher):
        self.switcher = switcher
        self._pools: Dict[str, List[str]] = {}  # pool_name -> session_ids
    
    def assign_to_pool(self, pool_name: str, session_id: str) -> None:
        """分配会话到角色池"""
        if pool_name not in self._pools:
            self._pools[pool_name] = []
        if session_id not in self._pools[pool_name]:
            self._pools[pool_name].append(session_id)
    
    def get_pool_sessions(self, pool_name: str) -> List[str]:
        """获取角色池中的会话"""
        return self._pools.get(pool_name, [])
    
    def broadcast_to_pool(self, pool_name: str, message: Any) -> None:
        """向角色池广播消息"""
        for session_id in self.get_pool_sessions(pool_name):
            ctx = self.switcher.get_context(session_id)
            if ctx:
                self.switcher.set_state(session_id, "_pending_message", message)


# ========== 全局实例 ==========

_global_switcher: Optional[RoleSwitcher] = None


def get_switcher() -> RoleSwitcher:
    """获取全局角色切换器"""
    global _global_switcher
    if _global_switcher is None:
        _global_switcher = RoleSwitcher()
    return _global_switcher
