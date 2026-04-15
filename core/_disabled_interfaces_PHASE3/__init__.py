"""
模块间接口定义
定义 Plector 核心模块之间的标准接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from pydantic import BaseModel


# ============ 统一响应格式 ============
class Response(BaseModel):
    """统一响应格式"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    
    @classmethod
    def ok(cls, data: Any = None) -> "Response":
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str) -> "Response":
        return cls(success=False, error=error)


# ============ LLM 接口 ============
class LLMInterface(ABC):
    """LLM 客户端接口"""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Response:
        """发送对话请求"""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话"""
        pass


# ============ 技能接口 ============
class SkillInterface(ABC):
    """技能接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """技能描述"""
        pass
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Response:
        """执行技能"""
        pass
    
    @abstractmethod
    async def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        pass


# ============ 记忆接口 ============
class MemoryInterface(ABC):
    """记忆存储接口"""
    
    @abstractmethod
    async def save(self, key: str, value: Any) -> Response:
        """保存数据"""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Response:
        """获取数据"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> Response:
        """语义搜索"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> Response:
        """删除数据"""
        pass


# ============ 工作流接口 ============
class WorkflowInterface(ABC):
    """工作流引擎接口"""
    
    @abstractmethod
    async def execute(
        self,
        workflow_id: str,
        inputs: Dict[str, Any]
    ) -> Response:
        """执行工作流"""
        pass
    
    @abstractmethod
    async def get_status(self, execution_id: str) -> Response:
        """获取执行状态"""
        pass
    
    @abstractmethod
    async def cancel(self, execution_id: str) -> Response:
        """取消执行"""
        pass


# ============ 角色接口 ============
class RoleInterface(ABC):
    """角色接口"""
    
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Response:
        """执行任务"""
        pass
    
    @abstractmethod
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """验证任务"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        pass


# ============ 工具接口 ============
class ToolInterface(ABC):
    """工具接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @abstractmethod
    async def call(self, params: Dict[str, Any]) -> Response:
        """调用工具"""
        pass
