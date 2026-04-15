"""Git 状态检查"""
import subprocess
import sys

result = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True,
    text=True
)
print("=== Git Status ===")
print(result.stdout if result.stdout else "(no changes)")
print(result.stderr if result.stderr else "")

# 检查远程
result = subprocess.run(
    ["git", "log", "--oneline", "-3"],
    capture_output=True,
    text=True
)
print("\n=== Recent Commits ===")
print(result.stdout if result.stdout else "")
