"""
Skill Router - 技能智能路由服务

根据用户请求智能路由到合适的技能。

架构约束：
- 不能直接 import 其他技能的 implementation.py
- 必须通过 self._skill_handler.execute("技能名", "方法", {参数}) 调用
- event_bus 使用 core.event_bus_v2
"""

import asyncio
import logging
import re
from typing import Any, Optional

from core.event_bus_v2 import EventBusV2, Event

logger = logging.getLogger(__name__)


class SkillRouter:
    """技能路由处理器"""

    def __init__(self, skill_handler=None, event_bus: EventBusV2 = None):
        """
        初始化技能路由

        Args:
            skill_handler: SkillHandler 实例，用于调用其他技能
            event_bus: EventBusV2 实例，用于事件通信
        """
        self._skill_handler = skill_handler
        self._event_bus = event_bus or EventBusV2()
        self._name = "skill_router"

        # 路由规则表：关键词 -> 技能名
        self._route_rules = {
            # 记忆相关
            r"(记住|存储|保存|回忆|之前.*说)": "memory",
            r"(偏好|设置|我的.*喜欢)": "memory",
            r"(知识|学到|记住.*内容)": "memory",

            # 健康检查
            r"(健康|状态|cpu|内存|磁盘)": "health_monitor",
            r"(系统.*如何|运行.*正常)": "health_monitor",

            # 代码相关
            r"(写代码|编写|创建.*文件|修改)": "code_writer",
            r"(代码|程序|函数|类)": "code_writer",

            # 文件操作
            r"(复制|移动|删除|列出|列表.*文件)": "file_utils",
            r"(文件.*操作|目录)": "file_utils",

            # 测试相关
            r"(测试|运行.*测试|pytest)": "test_runner",

            # 网页搜索
            r"(搜索|查找|查询|找.*信息)": "web_search",

            # 错误相关
            r"(报错|错误|异常|失败)": "error_knowledge",

            # 上下文保鲜
            r"(继续.*之前|之前.*任务|上下文)": "context_refresher",

            # 自动开发
            r"(开发|实现|需求|功能)": "auto_developer",

            # 工作流编排
            r"(工作流|编排|编排.*任务|多.*智能体)": "agency_orchestrator",
        }

    async def route(self, user_input: str, context: dict = None) -> dict:
        """
        根据用户输入路由到合适的技能

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            路由结果，包含目标技能和执行结果
        """
        context = context or {}

        # 发布路由开始事件
        await self._publish_event("skill_router.route.started", {
            "user_input": user_input,
            "context": context
        })

        # 匹配路由规则
        skill_name = self._match_skill(user_input)

        if not skill_name:
            await self._publish_event("skill_router.route.failed", {
                "user_input": user_input,
                "reason": "no_matching_skill"
            })
            return {
                "success": False,
                "error": f"无法为输入找到合适的技能: {user_input[:50]}...",
                "skill": None
            }

        # 确定要调用的方法
        method = self._determine_method(user_input, skill_name)

        # 构建参数
        params = self._build_params(user_input, context, skill_name, method)

        # 通过 SkillHandler 执行技能
        if self._skill_handler:
            result = await self._skill_handler.execute(skill_name, method, params)
        else:
            result = {"error": "SkillHandler 未初始化"}

        # 发布路由完成事件
        await self._publish_event("skill_router.route.completed", {
            "skill": skill_name,
            "method": method,
            "result": result
        })

        return {
            "success": True,
            "skill": skill_name,
            "method": method,
            "result": result
        }

    def _match_skill(self, user_input: str) -> Optional[str]:
        """
        根据用户输入匹配技能

        Args:
            user_input: 用户输入文本

        Returns:
            匹配的技能名，如果没有匹配则返回 None
        """
        for pattern, skill_name in self._route_rules.items():
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.info(f"Matched pattern '{pattern}' -> skill '{skill_name}'")
                return skill_name

        # 默认回退：检查是否有 agency_orchestrator 可用
        return "agency_orchestrator"

    def _determine_method(self, user_input: str, skill_name: str) -> str:
        """
        确定要调用的技能方法

        Args:
            user_input: 用户输入文本
            skill_name: 技能名

        Returns:
            方法名
        """
        method_map = {
            "memory": self._get_memory_method(user_input),
            "health_monitor": "check_health",
            "code_writer": self._get_code_method(user_input),
            "file_utils": self._get_file_method(user_input),
            "test_runner": "run_tests",
            "web_search": "search",
            "error_knowledge": "store_error",
            "context_refresher": "preserve",
            "auto_developer": "develop",
            "agency_orchestrator": "run_workflow",
        }

        return method_map.get(skill_name, "execute")

    def _get_memory_method(self, user_input: str) -> str:
        """根据输入确定 memory 技能的方法"""
        if re.search(r"(记住|存储|保存)", user_input):
            return "save_conversation"
        elif re.search(r"(偏好|设置.*喜欢)", user_input):
            return "save_preference"
        elif re.search(r"(知识)", user_input):
            return "save_knowledge"
        elif re.search(r"(搜索|查找)", user_input):
            return "semantic_search"
        else:
            return "get_conversation_history"

    def _get_code_method(self, user_input: str) -> str:
        """根据输入确定 code_writer 技能的方法"""
        if re.search(r"(修改|更新|编辑)", user_input):
            return "modify_code"
        elif re.search(r"(读取|查看)", user_input):
            return "read_code"
        else:
            return "write_code"

    def _get_file_method(self, user_input: str) -> str:
        """根据输入确定 file_utils 技能的方法"""
        if re.search(r"(复制|copy)", user_input):
            return "copy_file"
        elif re.search(r"(移动|重命名)", user_input):
            return "move_file"
        elif re.search(r"(删除)", user_input):
            return "delete_file"
        elif re.search(r"(列出|列表)", user_input):
            return "list_files"
        else:
            return "list_files"

    def _build_params(
        self,
        user_input: str,
        context: dict,
        skill_name: str,
        method: str
    ) -> dict:
        """
        根据技能和方法构建参数

        Args:
            user_input: 用户输入文本
            context: 上下文信息
            skill_name: 技能名
            method: 方法名

        Returns:
            参数字典
        """
        params = {"user_input": user_input}

        # 根据不同技能添加特定参数
        if skill_name == "memory":
            params["session_id"] = context.get("session_id", "default")
            if method == "save_conversation":
                params["role"] = "user"
                params["content"] = user_input
            elif method == "save_preference":
                params["key"] = self._extract_key(user_input)
                params["value"] = self._extract_value(user_input)
            elif method == "save_knowledge":
                params["topic"] = self._extract_topic(user_input)
                params["content"] = user_input
                params["source"] = "user_input"

        elif skill_name == "health_monitor":
            pass  # check_health 不需要参数

        elif skill_name == "code_writer":
            params["filepath"] = self._extract_filepath(user_input)
            if method == "write_code":
                params["code"] = self._extract_code(user_input)
            elif method == "modify_code":
                params["old_text"] = self._extract_old_text(user_input)
                params["new_text"] = self._extract_new_text(user_input)

        elif skill_name == "file_utils":
            params["path"] = self._extract_path(user_input)
            if method == "copy_file":
                params["source"] = self._extract_source(user_input)
                params["destination"] = self._extract_destination(user_input)
            elif method == "move_file":
                params["source"] = self._extract_source(user_input)
                params["destination"] = self._extract_destination(user_input)

        elif skill_name == "test_runner":
            params["path"] = context.get("test_path", "tests/")

        elif skill_name == "web_search":
            params["query"] = self._extract_search_query(user_input)
            params["count"] = 5

        elif skill_name == "error_knowledge":
            params["error"] = user_input

        elif skill_name == "context_refresher":
            params["conversation_history"] = context.get("history", [])
            params["session_id"] = context.get("session_id", "default")

        elif skill_name == "auto_developer":
            params["requirement"] = user_input
            params["project_dir"] = context.get("project_dir", ".")

        elif skill_name == "agency_orchestrator":
            params["path"] = context.get("workflow_path", "")
            params["inputs"] = context.get("workflow_inputs", {})

        return params

    # 辅助方法：提取各种参数
    def _extract_key(self, text: str) -> str:
        match = re.search(r"偏好.*?[:：]\s*(\w+)", text)
        return match.group(1) if match else "default"

    def _extract_value(self, text: str) -> str:
        match = re.search(r"[:：]\s*(.+?)(?:$|\n)", text)
        return match.group(1).strip() if match else text

    def _extract_topic(self, text: str) -> str:
        match = re.search(r"关于[“\"']?(.+?)[“\"']?", text)
        return match.group(1) if match else "general"

    def _extract_filepath(self, text: str) -> str:
        match = re.search(r"[`\"']([^\"`']+\.py)[`\"']", text)
        return match.group(1) if match else "temp.py"

    def _extract_code(self, text: str) -> str:
        match = re.search(r"```(?:python)?\n?(.*?)```", text, re.DOTALL)
        return match.group(1).strip() if match else text

    def _extract_old_text(self, text: str) -> str:
        match = re.search(r"旧的[:：]\s*(.+?)(?:新的|$)", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_new_text(self, text: str) -> str:
        match = re.search(r"新的[:：]\s*(.+?)$", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_path(self, text: str) -> str:
        match = re.search(r"[`\"']([^\"`']+)[\"`']", text)
        return match.group(1) if match else "."

    def _extract_source(self, text: str) -> str:
        match = re.search(r"源[文件路径]?[:：]\s*[`\"']?([^\"`'\s]+)[`\"']?", text)
        return match.group(1) if match else ""

    def _extract_destination(self, text: str) -> str:
        match = re.search(r"目标[文件路径]?[:：]\s*[`\"']?([^\"`'\s]+)[`\"']?", text)
        return match.group(1) if match else ""

    def _extract_search_query(self, text: str) -> str:
        match = re.search(r"搜索[关于]?\s*[`\"']?(.+?)[`\"']?$", text)
        return match.group(1).strip() if match else text

    async def _publish_event(self, event_type: str, data: dict):
        """发布事件到 event_bus"""
        event = Event(
            source="skill_router",
            type=event_type,
            data=data
        )
        await self._event_bus.publish(event)
        logger.debug(f"Published event: {event_type}", extra={"data": data})

    async def list_skills(self) -> dict:
        """列出所有可用技能及其路由规则"""
        skills = list(set(self._route_rules.values()))
        return {
            "success": True,
            "skills": sorted(skills),
            "total": len(skills)
        }

    async def add_route_rule(self, pattern: str, skill_name: str) -> dict:
        """
        添加路由规则

        Args:
            pattern: 匹配模式（正则表达式）
            skill_name: 目标技能名

        Returns:
            操作结果
        """
        self._route_rules[pattern] = skill_name
        await self._publish_event("skill_router.rule.added", {
            "pattern": pattern,
            "skill": skill_name
        })
        return {
            "success": True,
            "message": f"Added rule: {pattern} -> {skill_name}"
        }
