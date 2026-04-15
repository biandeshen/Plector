"""CrewAI 角色定义

职责：预定义常用的 AI Agent 角色
"""

from typing import Dict, List
from .crew_manager import Agent


def get_engineer_role() -> Agent:
    """获取工程师角色"""
    return Agent(
        name="Engineer",
        role="Software Engineer",
        goal="Write clean, efficient, and maintainable code",
        backstory=(
            "You are a senior software engineer with 10+ years of experience. "
            "You specialize in Python, clean code architecture, and best practices."
        ),
        verbose=True,
        allow_delegation=False,
    )


def get_reviewer_role() -> Agent:
    """获取代码审查角色"""
    return Agent(
        name="Reviewer",
        role="Code Reviewer",
        goal="Ensure code quality, security, and performance",
        backstory=(
            "You are an expert code reviewer with deep knowledge of security "
            "vulnerabilities and performance optimization."
        ),
        verbose=True,
        allow_delegation=False,
    )


def get_pm_role() -> Agent:
    """获取产品经理角色"""
    return Agent(
        name="PM",
        role="Product Manager",
        goal="Define clear requirements and prioritize features",
        backstory=(
            "You are an experienced product manager who bridges technical "
            "feasibility and business needs."
        ),
        verbose=True,
        allow_delegation=True,
    )


def get_designer_role() -> Agent:
    """获取设计师角色"""
    return Agent(
        name="Designer",
        role="UI/UX Designer",
        goal="Create intuitive and beautiful user interfaces",
        backstory=(
            "You are a creative UI/UX designer focused on user experience "
            "and accessibility."
        ),
        verbose=True,
        allow_delegation=False,
    )


def get_qa_role() -> Agent:
    """获取 QA 角色"""
    return Agent(
        name="QA",
        role="Quality Assurance Engineer",
        goal="Ensure product quality through comprehensive testing",
        backstory=(
            "You are a QA engineer who believes in test-driven development "
            "and automated testing."
        ),
        verbose=True,
        allow_delegation=False,
    )


def get_researcher_role() -> Agent:
    """获取研究员角色"""
    return Agent(
        name="Researcher",
        role="Research Analyst",
        goal="Gather and analyze information to support decision making",
        backstory=(
            "You are a research analyst with strong analytical skills "
            "and attention to detail."
        ),
        verbose=True,
        allow_delegation=False,
    )


def get_all_roles() -> Dict[str, Agent]:
    """获取所有预定义角色"""
    return {
        "engineer": get_engineer_role(),
        "reviewer": get_reviewer_role(),
        "pm": get_pm_role(),
        "designer": get_designer_role(),
        "qa": get_qa_role(),
        "researcher": get_researcher_role(),
    }


def create_custom_role(
    name: str,
    role: str,
    goal: str,
    backstory: str,
    verbose: bool = True,
    allow_delegation: bool = False,
) -> Agent:
    """创建自定义角色"""
    return Agent(
        name=name,
        role=role,
        goal=goal,
        backstory=backstory,
        verbose=verbose,
        allow_delegation=allow_delegation,
    )
