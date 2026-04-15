"""CLI 参数解析器

职责：统一管理所有命令行参数解析
遵循规则：函数不超过 50 行
"""

import argparse
from pathlib import Path
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """创建主解析器"""
    parser = argparse.ArgumentParser(
        prog="plector",
        description="Plector - 事件驱动的 AI Agent 引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # 全局参数
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--version", action="store_true", help="显示版本")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    _add_run_parser(subparsers)
    _add_skill_parser(subparsers)
    _add_workflow_parser(subparsers)
    _add_agent_parser(subparsers)
    
    return parser


def _add_run_parser(subparsers) -> None:
    """添加 run 子命令"""
    run_parser = subparsers.add_parser("run", help="运行任务")
    run_parser.add_argument("task", type=str, help="任务描述")
    run_parser.add_argument("--skill", type=str, help="指定技能")
    run_parser.add_argument("--async", action="store_true", help="异步执行")


def _add_skill_parser(subparsers) -> None:
    """添加 skill 子命令"""
    skill_parser = subparsers.add_parser("skill", help="技能管理")
    skill_sub = skill_parser.add_subparsers(dest="skill_action")
    
    # skill list
    list_parser = skill_sub.add_parser("list", help="列出所有技能")
    list_parser.add_argument("--installed", action="store_true")
    
    # skill load
    load_parser = skill_sub.add_parser("load", help="加载技能")
    load_parser.add_argument("name", type=str)
    
    # skill info
    info_parser = skill_sub.add_parser("info", help="技能详情")
    info_parser.add_argument("name", type=str)


def _add_workflow_parser(subparsers) -> None:
    """添加 workflow 子命令"""
    wf_parser = subparsers.add_parser("workflow", help="工作流管理")
    wf_sub = wf_parser.add_subparsers(dest="wf_action")
    
    # workflow list
    wf_sub.add_parser("list", help="列出工作流")
    
    # workflow run
    run_parser = wf_sub.add_parser("run", help="运行工作流")
    run_parser.add_argument("path", type=str)
    run_parser.add_argument("--inputs", type=str, help="输入变量 JSON")
    
    # workflow validate
    val_parser = wf_sub.add_parser("validate", help="验证工作流")
    val_parser.add_argument("path", type=str)


def _add_agent_parser(subparsers) -> None:
    """添加 agent 子命令"""
    agent_parser = subparsers.add_parser("agent", help="智能体管理")
    agent_sub = agent_parser.add_subparsers(dest="agent_action")
    
    agent_sub.add_parser("list", help="列出智能体")
    status_parser = agent_sub.add_parser("status", help="智能体状态")
    status_parser.add_argument("name", type=str, nargs="?")


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    """解析参数"""
    parser = create_parser()
    return parser.parse_args(args)
