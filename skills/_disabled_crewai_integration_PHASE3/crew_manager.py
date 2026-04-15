"""Crew 管理器

职责：管理和执行 CrewAI 工作流
遵循规则：函数不超过 50 行
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Agent:
    """Agent 定义"""
    name: str
    role: str
    goal: str
    backstory: str
    verbose: bool = True
    allow_delegation: bool = False
    tools: List[Any] = field(default_factory=list)


@dataclass
class Task:
    """任务定义"""
    description: str
    agent: Agent
    expected_output: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None


@dataclass
class Crew:
    """Crew 定义"""
    agents: List[Agent]
    tasks: List[Task]
    verbose: bool = True
    process: str = "sequential"  # sequential, hierarchical


class CrewManager:
    """Crew 管理器
    
    提供 CrewAI 风格的接口，支持：
    - Agent 管理
    - Task 编排
    - Crew 执行
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.crews: Dict[str, Crew] = {}
        self.llm_client = llm_client
    
    # ========== Agent 管理 ==========
    
    def create_agent(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        **kwargs,
    ) -> Agent:
        """创建 Agent"""
        agent = Agent(
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            **kwargs,
        )
        self.agents[name] = agent
        return agent
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """获取 Agent"""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Agent]:
        """列出所有 Agent"""
        return list(self.agents.values())
    
    # ========== Task 管理 ==========
    
    def create_task(
        self,
        task_id: str,
        description: str,
        agent_name: str,
        expected_output: str = "",
    ) -> Task:
        """创建 Task"""
        agent = self.get_agent(agent_name)
        if agent is None:
            raise ValueError(f"Agent 不存在: {agent_name}")
        
        task = Task(
            description=description,
            agent=agent,
            expected_output=expected_output,
        )
        self.tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取 Task"""
        return self.tasks.get(task_id)
    
    # ========== Crew 管理 ==========
    
    def create_crew(
        self,
        crew_id: str,
        agent_names: List[str],
        task_ids: List[str],
        process: str = "sequential",
        **kwargs,
    ) -> Crew:
        """创建 Crew"""
        agents = [self.get_agent(name) for name in agent_names]
        agents = [a for a in agents if a is not None]
        
        tasks = [self.get_task(tid) for tid in task_ids]
        tasks = [t for t in tasks if t is not None]
        
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=process,
            **kwargs,
        )
        self.crews[crew_id] = crew
        return crew
    
    def get_crew(self, crew_id: str) -> Optional[Crew]:
        """获取 Crew"""
        return self.crews.get(crew_id)
    
    # ========== 执行 ==========
    
    async def run_crew(self, crew_id: str) -> Dict[str, Any]:
        """运行 Crew"""
        crew = self.get_crew(crew_id)
        if crew is None:
            raise ValueError(f"Crew 不存在: {crew_id}")
        
        results = {}
        
        if crew.process == "sequential":
            results = await self._run_sequential(crew)
        elif crew.process == "hierarchical":
            results = await self._run_hierarchical(crew)
        
        return results
    
    async def run_task(self, task_id: str) -> Any:
        """运行单个 Task"""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task 不存在: {task_id}")
        
        task.status = TaskStatus.IN_PROGRESS
        
        try:
            # 模拟执行
            result = await self._execute_agent_task(task.agent, task.description)
            task.result = result
            task.status = TaskStatus.COMPLETED
            return result
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            raise
    
    # ========== 内部方法 ==========
    
    async def _run_sequential(self, crew: Crew) -> Dict[str, Any]:
        """顺序执行"""
        results = {}
        
        for task in crew.tasks:
            task.status = TaskStatus.IN_PROGRESS
            
            try:
                result = await self._execute_agent_task(task.agent, task.description)
                task.result = result
                task.status = TaskStatus.COMPLETED
                results[task.agent.name] = result
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                results[task.agent.name] = {"error": str(e)}
        
        return results
    
    async def _run_hierarchical(self, crew: Crew) -> Dict[str, Any]:
        """层级执行（第一个 Agent 为主管）"""
        if not crew.agents:
            return {}
        
        manager = crew.agents[0]  # 第一个 agent 作为主管
        worker_tasks = crew.tasks[1:] if len(crew.tasks) > 1 else []
        
        results = {manager.name: "Manager orchestration complete"}
        
        # 分配任务给 workers
        for task in worker_tasks:
            try:
                result = await self._execute_agent_task(task.agent, task.description)
                results[task.agent.name] = result
            except Exception as e:
                results[task.agent.name] = {"error": str(e)}
        
        return results
    
    async def _execute_agent_task(self, agent: Agent, prompt: str) -> str:
        """执行 Agent 任务"""
        # 如果有 LLM client，使用它
        if self.llm_client:
            response = await self.llm_client.generate(
                system_prompt=agent.backstory,
                user_prompt=prompt,
            )
            return response
        else:
            # 模拟执行
            await asyncio.sleep(0.1)
            return f"[{agent.name}] Executed: {prompt[:50]}..."


# ========== 快捷函数 ==========

def quick_crew(
    workflow: str,
    agents: List[Dict],
    tasks: List[Dict],
) -> Dict[str, Any]:
    """快速创建并运行 Crew"""
    manager = CrewManager()
    
    # 创建 agents
    for agent_def in agents:
        manager.create_agent(**agent_def)
    
    # 创建 tasks
    task_ids = []
    for i, task_def in enumerate(tasks):
        task_id = f"task_{i}"
        manager.create_task(task_id, **task_def)
        task_ids.append(task_id)
    
    # 创建 crew
    agent_names = [a["name"] for a in agents]
    crew_id = "quick_crew"
    manager.create_crew(crew_id, agent_names, task_ids, process=workflow)
    
    # 运行
    return asyncio.run(manager.run_crew(crew_id))
