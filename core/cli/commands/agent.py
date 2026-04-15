"""agent 命令实现

职责：处理 `plector agent` 命令
"""

from typing import Optional
from ..parser import parse_args


def agent_command(args: Optional[list] = None) -> int:
    """执行 agent 命令"""
    parsed = args if args is not None else parse_args()
    
    action = parsed.agent_action
    
    if action == "list":
        return _list_agents()
    elif action == "status":
        return _agent_status(parsed)
    else:
        print("未知操作: " + str(action))
        return 1


def _list_agents() -> int:
    """列出智能体"""
    # TODO: 集成 agent_registry
    print("[agent list] 功能开发中...")
    return 0


def _agent_status(parsed) -> int:
    """智能体状态"""
    name = parsed.name or "all"
    print(f"[agent status] {name}")
    return 0


if __name__ == "__main__":
    exit(agent_command())
