#!/usr/bin/env python3
"""
检查依赖方向是否违规

规则：
  core/     → 不依赖 skills/、tools/
  skills/   → 可依赖 core/，不依赖其他 skills/
  tools/    → 不依赖 skills/、core/

用法：
  python scripts/check_dependencies.py
  exit code 0 = 通过，非 0 = 有违规
"""
import ast
import sys
from pathlib import Path

# Windows 编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 依赖方向规则
RULES = {
    "core": {"forbidden": ["skills", "tools"]},
    "skills": {"forbidden": ["skills"]},  # skills 不依赖其他 skills
    "tools": {"forbidden": ["skills", "core"]},
}


def get_imports(filepath: Path) -> list:
    """从 Python 文件中提取顶层 import"""
    imports = []
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


def check_file(filepath: Path, module: str) -> list:
    """检查单个文件的依赖是否违规"""
    errors = []
    imports = get_imports(filepath)
    forbidden = RULES.get(module, {}).get("forbidden", [])
    for imp in imports:
        if imp in forbidden:
            errors.append(f"{filepath}: 不允许导入 {imp}/（{module}/ 不应依赖 {imp}/）")
    return errors


def main():
    errors = 0
    for module in ["core", "skills", "tools"]:
        module_dir = Path(module)
        if not module_dir.exists():
            continue
        for py_file in module_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            file_errors = check_file(py_file, module)
            for err in file_errors:
                print(f"❌ {err}")
            errors += len(file_errors)

    if errors == 0:
        print("✅ 依赖方向检查通过")
    sys.exit(errors)


if __name__ == "__main__":
    main()
