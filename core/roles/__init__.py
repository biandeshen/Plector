"""
Plector 角色系统
定义 AI Agent 角色、职责和协作协议
"""
from core.roles.base import Role, RoleType
from core.roles.engineer import EngineerRole
from core.roles.operator import OperatorRole
from core.roles.reviewer import ReviewerRole

__all__ = [
    "Role",
    "RoleType",
    "EngineerRole",
    "OperatorRole",
    "ReviewerRole",
]
