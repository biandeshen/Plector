# CrewAI 角色委派技能

## 概述
CrewAI 角色委派技能允许 Plector 与 CrewAI 框架集成，支持多智能体协作工作流。

## 功能
- 定义 CrewAI Agent 角色
- 创建和管理 Crew 工作流
- 任务委派和执行
- 结果聚合

## 使用方式
```python
from skills.crewai_integration import CrewAIIntegration

crew = CrewAIIntegration()
crew.create_crew(agents=[...], tasks=[...])
result = crew.run()
```

## 角色定义
- **Engineer**: 代码开发
- **Reviewer**: 代码审查
- **PM**: 产品管理
- **Designer**: UI/UX 设计

## 状态
- 状态: beta
- 版本: 1.0.0
