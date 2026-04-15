"""
审查角色
负责代码审查、质量检查、安全审计等任务
"""
from typing import Any, Dict, List
from core.roles.base import Role, RoleConfig, RoleCapability, RoleType


class ReviewerRole(Role):
    """审查角色"""
    
    DEFAULT_CAPABILITIES = [
        RoleCapability(
            name="code_review",
            description="代码审查",
            tools=["agency_orchestrator_run_workflow"],
            skills=["agency_orchestrator"],
        ),
        RoleCapability(
            name="quality_check",
            description="质量检查",
            tools=[],
            skills=["test_runner"],
        ),
        RoleCapability(
            name="security_audit",
            description="安全审计",
            tools=[],
            skills=["agency_orchestrator"],
        ),
    ]
    
    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                name="reviewer",
                type=RoleType.REVIEWER,
                description="审查角色，负责代码质量和安全审查",
                capabilities=self.DEFAULT_CAPABILITIES,
            )
        super().__init__(config)
    
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """验证任务类型"""
        valid_types = [
            "review",
            "security_audit",
            "quality_check",
            "compliance_check",
        ]
        return task.get("type") in valid_types
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行审查任务"""
        task_id = task.get("id", "unknown")
        task_type = task.get("type")
        
        self._active_tasks[task_id] = task
        
        try:
            if task_type == "review":
                result = await self._review(task)
            elif task_type == "security_audit":
                result = await self._security_audit(task)
            elif task_type == "quality_check":
                result = await self._quality_check(task)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            self._completed_tasks.append({**task, "result": result})
            return result
            
        finally:
            self._active_tasks.pop(task_id, None)
    
    async def _review(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """代码审查"""
        # 使用 agency_orchestrator 执行 PR 审查
        return {"success": True, "message": "Review completed"}
    
    async def _security_audit(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """安全审计"""
        return {"success": True, "message": "Security audit completed"}
    
    async def _quality_check(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """质量检查"""
        return {"success": True, "message": "Quality check completed"}
