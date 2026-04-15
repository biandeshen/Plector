"""
开发者角色
负责代码编写、调试、重构等开发任务
"""
from typing import Any, Dict, List
from core.roles.base import Role, RoleConfig, RoleCapability, RoleType


class EngineerRole(Role):
    """开发者角色"""
    
    DEFAULT_CAPABILITIES = [
        RoleCapability(
            name="code_write",
            description="编写代码文件",
            tools=["code_writer_write_code"],
            skills=["code_writer"],
        ),
        RoleCapability(
            name="code_review",
            description="审查代码质量",
            tools=[],
            skills=["agency_orchestrator"],
        ),
        RoleCapability(
            name="test_execute",
            description="运行测试",
            tools=["test_runner_run_tests"],
            skills=["test_runner"],
        ),
        RoleCapability(
            name="file_operations",
            description="文件操作",
            tools=["file_utils_*"],
            skills=["file_utils"],
        ),
    ]
    
    def __init__(self, config: Optional[RoleConfig] = None):
        if config is None:
            config = RoleConfig(
                name="engineer",
                type=RoleType.ENGINEER,
                description="开发者角色，负责代码编写和调试",
                capabilities=self.DEFAULT_CAPABILITIES,
            )
        super().__init__(config)
    
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """验证任务类型"""
        valid_types = [
            "write_code",
            "modify_code",
            "debug",
            "refactor",
            "test",
        ]
        return task.get("type") in valid_types
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行开发任务"""
        task_id = task.get("id", "unknown")
        task_type = task.get("type")
        
        self._active_tasks[task_id] = task
        
        try:
            if task_type == "write_code":
                result = await self._write_code(task)
            elif task_type == "modify_code":
                result = await self._modify_code(task)
            elif task_type == "debug":
                result = await self._debug(task)
            elif task_type == "test":
                result = await self._run_test(task)
            else:
                result = {"success": False, "error": f"Unknown task type: {task_type}"}
            
            self._completed_tasks.append({**task, "result": result})
            return result
            
        finally:
            self._active_tasks.pop(task_id, None)
    
    async def _write_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """写代码"""
        from skills.code_writer import code_writer_write_code
        return await code_writer_write_code(
            filepath=task.get("filepath"),
            code=task.get("code"),
        )
    
    async def _modify_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """改代码"""
        from skills.code_writer import code_writer_modify_code
        return await code_writer_modify_code(
            filepath=task.get("filepath"),
            old_text=task.get("old_text"),
            new_text=task.get("new_text"),
        )
    
    async def _debug(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """调试"""
        # 实现调试逻辑
        return {"success": True, "message": "Debug completed"}
    
    async def _run_test(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """运行测试"""
        from skills.test_runner import test_runner_run_tests
        return await test_runner_run_tests(path=task.get("path"))
