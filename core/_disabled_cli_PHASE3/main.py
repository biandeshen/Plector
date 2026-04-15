"""CLI 主入口

职责：统一命令行入口，协调各子命令
"""

import sys
from typing import Optional, List
from .parser import parse_args
from .commands import run_command, skill_command, workflow_command, agent_command


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主函数
    
    Args:
        argv: 命令行参数列表，默认为 sys.argv
        
    Returns:
        退出码
    """
    args = parse_args(argv)
    
    # 处理全局参数
    if args.version:
        print("Plector v2.0.0")
        return 0
    
    if args.verbose:
        print("[DEBUG] verbose mode enabled")
    
    # 分发到具体命令
    command = args.command
    
    if command is None:
        print("错误: 未指定命令")
        print("使用 'plector --help' 查看帮助")
        return 1
    
    # 命令路由
    command_map = {
        "run": run_command,
        "skill": skill_command,
        "workflow": workflow_command,
        "agent": agent_command,
    }
    
    handler = command_map.get(command)
    if handler is None:
        print(f"错误: 未知命令 '{command}'")
        return 1
    
    return handler(argv)


if __name__ == "__main__":
    exit(main())
