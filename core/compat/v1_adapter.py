"""V1 适配器

职责：将 V2 API 适配为 V1 兼容接口，支持遗留系统迁移
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class V1Request:
    """V1 格式请求"""
    action: str
    params: Dict[str, Any]
    session_id: Optional[str] = None


@dataclass
class V1Response:
    """V1 格式响应"""
    success: bool
    result: Any
    error: Optional[str] = None
    version: str = "v1"


class V1Adapter:
    """V1 API 适配器
    
    将 V1 格式请求转换为 V2 格式，再调用 V2 处理器
    """
    
    def __init__(self, v2_handler: Callable):
        self.v2_handler = v2_handler
        self._action_map = {
            "execute": self._adapt_execute,
            "skill.run": self._adapt_skill_run,
            "skill.list": self._adapt_skill_list,
            "event.emit": self._adapt_event_emit,
            "memory.store": self._adapt_memory_store,
            "memory.retrieve": self._adapt_memory_retrieve,
        }
    
    def handle(self, request: V1Request) -> V1Response:
        """处理 V1 请求"""
        adapter = self._action_map.get(request.action)
        
        if adapter is None:
            return V1Response(
                success=False,
                result=None,
                error=f"Unknown action: {request.action}",
            )
        
        try:
            v2_result = adapter(request)
            return V1Response(success=True, result=v2_result)
        except Exception as e:
            return V1Response(success=False, result=None, error=str(e))
    
    def _adapt_execute(self, request: V1Request) -> Any:
        """适配 execute 操作"""
        task = request.params.get("task")
        skill = request.params.get("skill")
        
        # 转换为 V2 格式
        v2_input = {
            "task": task,
            "skill": skill,
            "session_id": request.session_id,
        }
        
        return self.v2_handler(v2_input)
    
    def _adapt_skill_run(self, request: V1Request) -> Any:
        """适配 skill.run 操作"""
        skill_name = request.params.get("skill_name")
        params = request.params.get("params", {})
        
        v2_input = {
            "type": "skill_execution",
            "skill": skill_name,
            "params": params,
            "session_id": request.session_id,
        }
        
        return self.v2_handler(v2_input)
    
    def _adapt_skill_list(self, request: V1Request) -> Any:
        """适配 skill.list 操作"""
        v2_input = {
            "type": "skill_list",
            "session_id": request.session_id,
        }
        
        return self.v2_handler(v2_input)
    
    def _adapt_event_emit(self, request: V1Request) -> Any:
        """适配 event.emit 操作"""
        event_type = request.params.get("event_type")
        event_data = request.params.get("data", {})
        
        v2_input = {
            "type": "event",
            "event_type": event_type,
            "data": event_data,
        }
        
        return self.v2_handler(v2_input)
    
    def _adapt_memory_store(self, request: V1Request) -> Any:
        """适配 memory.store 操作"""
        key = request.params.get("key")
        value = request.params.get("value")
        
        v2_input = {
            "type": "memory_store",
            "key": key,
            "value": value,
        }
        
        return self.v2_handler(v2_input)
    
    def _adapt_memory_retrieve(self, request: V1Request) -> Any:
        """适配 memory.retrieve 操作"""
        key = request.params.get("key")
        
        v2_input = {
            "type": "memory_retrieve",
            "key": key,
        }
        
        return self.v2_handler(v2_input)


class V1CompatibilityLayer:
    """V1 兼容层
    
    提供 V1 风格的外壳函数，简化迁移
    """
    
    def __init__(self, adapter: V1Adapter):
        self.adapter = adapter
    
    def execute(self, task: str, **kwargs) -> Any:
        """执行任务 (V1 风格)"""
        request = V1Request(
            action="execute",
            params={"task": task, **kwargs},
        )
        response = self.adapter.handle(request)
        
        if not response.success:
            raise RuntimeError(response.error)
        
        return response.result
    
    def run_skill(self, skill_name: str, **params) -> Any:
        """运行技能 (V1 风格)"""
        request = V1Request(
            action="skill.run",
            params={"skill_name": skill_name, "params": params},
        )
        response = self.adapter.handle(request)
        
        if not response.success:
            raise RuntimeError(response.error)
        
        return response.result
    
    def emit_event(self, event_type: str, **data) -> Any:
        """发送事件 (V1 风格)"""
        request = V1Request(
            action="event.emit",
            params={"event_type": event_type, "data": data},
        )
        response = self.adapter.handle(request)
        
        if not response.success:
            raise RuntimeError(response.error)
        
        return response.result
    
    def list_skills(self) -> List[str]:
        """列出技能 (V1 风格)"""
        request = V1Request(
            action="skill.list",
            params={},
        )
        response = self.adapter.handle(request)
        
        if not response.success:
            raise RuntimeError(response.error)
        
        return response.result
