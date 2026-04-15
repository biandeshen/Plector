"""
角色基类定义
定义所有 AI Agent 角色的通用接口和行为规范
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoleType(str, Enum):
    """角色类型枚举"""
    ENGINEER = "engineer"          # 开发者角色
    OPERATOR = "operator"           # 运维角色
    REVIEWER = "reviewer"          # 审查角色
    ORCHESTRATOR = "orchestrator"  # 编排角色
    SPECIALIST = "specialist"       # 专家角色


class RoleCapability(BaseModel):
    """角色能力定义"""
    name: str
    description: str
    tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)


class RoleConfig(BaseModel):
    """角色配置"""
    name: str
    type: RoleType
    description: str
    capabilities: List[RoleCapability] = Field(default_factory=list)
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300


class Role(ABC):
    """AI Agent 角色基类"""
    
    def __init__(self, config: RoleConfig):
        self.config = config
        self._task_queue: List[Dict[str, Any]] = []
        self._active_tasks: Dict[str, Dict[str, Any]] = {}
        self._completed_tasks: List[Dict[str, Any]] = []
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def role_type(self) -> RoleType:
        return self.config.type
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务的抽象方法"""
        pass
    
    @abstractmethod
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """验证任务是否适合此角色"""
        pass
    
    async def can_accept_task(self) -> bool:
        """检查是否可接受新任务"""
        return len(self._active_tasks) < self.config.max_concurrent_tasks
    
    def get_status(self) -> Dict[str, Any]:
        """获取角色状态"""
        return {
            "name": self.name,
            "type": self.role_type.value,
            "active_tasks": len(self._active_tasks),
            "completed_tasks": len(self._completed_tasks),
            "can_accept": await self.can_accept_task(),
        }
