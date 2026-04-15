"""
Pytest 配置文件 - Plector v2.0
"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 首位
root = str(Path(__file__).parent.parent)
if root in sys.path:
    sys.path.remove(root)
sys.path.insert(0, root)
