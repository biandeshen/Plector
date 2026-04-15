"""
协作协议定义
定义角色之间的通信和协作规范
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MessageType(str, Enum):
    """消息类型"""
    TASK_REQUEST = "task_request"       # 任务请求
    TASK_RESPONSE = "task_response"     # 任务响应
    STATUS_UPDATE = "status_update"     # 状态更新
    ERROR_REPORT = "error_report"       # 错误报告
    COORDINATION = "coordination"       # 协调消息


class Priority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    """协作消息"""
    id: str
    type: MessageType
    sender: str
    receiver: Optional[str] = None
    content: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    timestamp: datetime = Field(default_factory=datetime.now)


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    role: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class CollaborationProtocol:
    """协作协议"""
    
    @staticmethod
    def create_task_message(
        sender: str,
        receiver: str,
        task: Dict[str, Any],
        priority: Priority = Priority.NORMAL
    ) -> Message:
        """创建任务消息"""
        return Message(
            id=f"msg_{datetime.now().timestamp()}",
            type=MessageType.TASK_REQUEST,
            sender=sender,
            receiver=receiver,
            content={"task": task},
            priority=priority,
        )
    
    @staticmethod
    def create_response_message(
        sender: str,
        receiver: str,
        result: TaskResult
    ) -> Message:
        """创建响应消息"""
        return Message(
            id=f"msg_{datetime.now().timestamp()}",
            type=MessageType.TASK_RESPONSE,
            sender=sender,
            receiver=receiver,
            content={"result": result.model_dump()},
        )
    
    @staticmethod
    def create_status_message(
        sender: str,
        status: Dict[str, Any]
    ) -> Message:
        """创建状态消息"""
        return Message(
            id=f"msg_{datetime.now().timestamp()}",
            type=MessageType.STATUS_UPDATE,
            sender=sender,
            content={"status": status},
        )
    
    @staticmethod
    def create_error_message(
        sender: str,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Message:
        """创建错误消息"""
        return Message(
            id=f"msg_{datetime.now().timestamp()}",
            type=MessageType.ERROR_REPORT,
            sender=sender,
            content={"error": error, "context": context or {}},
            priority=Priority.HIGH,
        )
