"""
角色编排引擎
管理多个角色的协作和任务分配
"""
from typing import Any, Dict, List, Optional
from core.roles.base import Role, RoleType
from core.roles.engineer import EngineerRole
from core.roles.operator import OperatorRole
from core.roles.reviewer import ReviewerRole


class RoleOrchestrator:
    """角色编排器"""
    
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._task_queue: List[Dict[str, Any]] = []
        self._initialized = False
    
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """初始化角色系统"""
        if config is None:
            config = self._default_config()
        
        # 创建默认角色
        for role_config in config.get("roles", []):
            role_type = role_config.get("type")
            if role_type == RoleType.ENGINEER.value:
                self._roles["engineer"] = EngineerRole()
            elif role_type == RoleType.OPERATOR.value:
                self._roles["operator"] = OperatorRole()
            elif role_type == RoleType.REVIEWER.value:
                self._roles["reviewer"] = ReviewerRole()
        
        self._initialized = True
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "roles": [
                {"type": RoleType.ENGINEER.value, "name": "engineer"},
                {"type": RoleType.OPERATOR.value, "name": "operator"},
                {"type": RoleType.REVIEWER.value, "name": "reviewer"},
            ]
        }
    
    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(name)
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """列出所有角色"""
        return [role.get_status() for role in self._roles.values()]
    
    async def assign_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分配任务到合适的角色"""
        task_type = task.get("type", "")
        role = self._select_role(task_type)
        
        if role is None:
            return {"success": False, "error": "No suitable role found"}
        
        if not await role.can_accept_task():
            return {"success": False, "error": "Role is busy"}
        
        return await role.execute_task(task)
    
    def _select_role(self, task_type: str) -> Optional[Role]:
        """根据任务类型选择角色"""
        # 简单规则映射
        task_role_map = {
            "write_code": "engineer",
            "modify_code": "engineer",
            "debug": "engineer",
            "test": "engineer",
            "deploy": "operator",
            "monitor": "operator",
            "health_check": "operator",
            "review": "reviewer",
            "security_audit": "reviewer",
            "quality_check": "reviewer",
        }
        
        role_name = task_role_map.get(task_type)
        if role_name:
            return self._roles.get(role_name)
        
        # 默认选择 engineer
        return self._roles.get("engineer")
    
    async def execute_workflow(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = False
    ) -> List[Dict[str, Any]]:
        """执行工作流"""
        if parallel:
            # 并行执行
            import asyncio
            return await asyncio.gather(*[
                self.assign_task(task) for task in tasks
            ])
        else:
            # 串行执行
            results = []
            for task in tasks:
                result = await self.assign_task(task)
                results.append(result)
            return results
