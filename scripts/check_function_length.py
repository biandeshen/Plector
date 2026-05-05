#!/usr/bin/env python3
"""
检查函数长度是否超过限制

规则：
  单个函数不超过 50 行

用法：
  python scripts/check_function_length.py
  exit code 0 = 通过，非 0 = 有违规
"""

import ast
import sys
from pathlib import Path

# Windows 编码修复
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

MAX_LINES = 50


def count_function_lines(node: ast.FunctionDef, source_lines: list) -> int:
    """计算函数的实际行数"""
    start = node.lineno
    end = node.end_lineno if hasattr(node, "end_lineno") else start
    return end - start + 1


def check_file(filepath: Path) -> list:
    """检查单个文件中的函数长度"""
    errors = []
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
            source_lines = source.splitlines()
            tree = ast.parse(source)
    except SyntaxError:
        return errors

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            length = count_function_lines(node, source_lines)
            if length > MAX_LINES:
                errors.append(f"{filepath}:{node.lineno} {node.name}() 长度 {length} 行，超过 {MAX_LINES} 行限制")
    return errors


def main():
    errors = 0
    for py_file in Path(".").rglob("*.py"):
        # 跳过第三方和虚拟环境
        if any(skip in str(py_file) for skip in ["venv", ".venv", "__pycache__", "node_modules"]):
            continue
        file_errors = check_file(py_file)
        for err in file_errors:
            print(f"❌ {err}")
        errors += len(file_errors)

    if errors == 0:
        print("✅ 函数长度检查通过")
    sys.exit(errors)


if __name__ == "__main__":
    main()
