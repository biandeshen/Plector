"""CrewAI 角色委派集成

职责：与 CrewAI 框架集成，支持多智能体协作
遵循规则：函数不超过 50 行
"""

from .crew_manager import CrewManager, Agent, Task, Crew
from .role_definitions import (
    get_engineer_role,
    get_reviewer_role,
    get_pm_role,
    get_designer_role,
    get_all_roles,
)

__all__ = [
    "CrewManager",
    "Agent",
    "Task", 
    "Crew",
    "get_engineer_role",
    "get_reviewer_role",
    "get_pm_role",
    "get_designer_role",
    "get_all_roles",
]
