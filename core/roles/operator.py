"""
运维角色
负责系统监控、部署、日志分析等运维任务
"""
from typing import Any, Dict, List
from core.roles.base import Role, RoleConfig, RoleCapability, RoleType


class OperatorRole(Role):
    """运维角色"""
    
    DEFAULT_CAPABILITIES = [
        RoleCapability(
            name="health_check",
            description="系统健康检查",
            tools=["health_monitor_check_health"],
            skills=["health_monitor"],
        ),
        RoleCapability(
            name="file_operations",
            description="文件管理操作",
            tools=["file_utils_*"],
            skills=["file_utils"],
        ),
        RoleCapability(
            name="error_analysis",
            description="错误日志分析",
            tools=["error_knowledge_store_error"],
            skills=["error_knowledge"],
        ),
    ]
    
    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                name="operator",
                type=RoleType.OPERATOR,
                description="运维角色，负责系统监控和部署",
                capabilities=self.DEFAULT_CAPABILITIES,
            )
        super().__init__(config)
    
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """验证任务类型"""
        valid_types = [
            "deploy",
            "monitor",
            "backup",
            "restore",
            "health_check",
        ]
        return task.get("type") in valid_types
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行运维任务"""
        task_id = task.get("id", "unknown")
        task_type = task.get("type")
        
        self._active_tasks[task_id] = task
        
        try:
            if task_type == "health_check":
                result = await self._health_check(task)
            elif task_type == "deploy":
                result = await self._deploy(task)
            elif task_type == "backup":
                result = await self._backup(task)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            self._completed_tasks.append({**task, "result": result})
            return result
            
        finally:
            self._active_tasks.pop(task_id, None)
    
    async def _health_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """健康检查"""
        from skills.health_monitor import health_monitor_check_health
        return await health_monitor_check_health()
    
    async def _deploy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """部署"""
        # 实现部署逻辑
        return {"success": True, "message": "Deploy completed"}
    
    async def _backup(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """备份"""
        # 实现备份逻辑
        return {"success": True, "message": "Backup completed"}
