"""skill 命令实现

职责：处理 `plector skill` 命令
"""

from typing import Optional
from ..parser import parse_args


def skill_command(args: Optional[list] = None) -> int:
    """执行 skill 命令
    
    Args:
        args: 命令行参数列表
        
    Returns:
        退出码
    """
    parsed = args if args is not None else parse_args()
    
    action = parsed.skill_action
    
    if action == "list":
        return _list_skills(parsed)
    elif action == "load":
        return _load_skill(parsed)
    elif action == "info":
        return _skill_info(parsed)
    else:
        print("未知操作: " + str(action))
        return 1


def _list_skills(parsed) -> int:
    """列出技能"""
    # TODO: 集成 skill_registry
    print("[skill list] 功能开发中...")
    return 0


def _load_skill(parsed) -> int:
    """加载技能"""
    name = parsed.name
    print(f"[skill load] {name}")
    return 0


def _skill_info(parsed) -> int:
    """技能详情"""
    name = parsed.name
    print(f"[skill info] {name}")
    return 0


if __name__ == "__main__":
    exit(skill_command())
