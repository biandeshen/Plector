#!/usr/bin/env python3
"""
校验 skill.json 是否符合 MCP Tool 格式规范
"""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "name",
    "description",
    "version",
    "tier",
    "dependencies",
    "events_produced",
    "events_consumed",
    "tools",
]

VALID_TIERS = ["tier_0_kernel", "tier_1_system", "tier_2_functional", "tier_3_tool"]

REQUIRED_TOOL_FIELDS = ["name", "description", "inputSchema"]

REQUIRED_SCHEMA_FIELDS = ["type", "properties", "required", "additionalProperties"]


def validate_skill_md(skill_dir):
    """校验 SKILL.md 文件"""
    errors = []
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        errors.append(f"{skill_dir.name}: 缺少 SKILL.md 文件")
        return errors

    content = skill_md_path.read_text(encoding="utf-8")

    # 检查 YAML frontmatter
    if not content.startswith("---"):
        errors.append(f"{skill_dir.name}/SKILL.md: 缺少 YAML frontmatter")
        return errors

    # 提取 frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{skill_dir.name}/SKILL.md: YAML frontmatter 格式错误")
        return errors

    try:
        import yaml

        frontmatter = yaml.safe_load(parts[1])
    except Exception as e:
        errors.append(f"{skill_dir.name}/SKILL.md: YAML 解析错误: {e}")
        return errors

    # 检查必选字段
    errors.extend(_validate_frontmatter_fields(skill_dir, frontmatter))

    # 检查 name 与 skill.json 一致
    errors.extend(_validate_name_consistency(skill_dir, frontmatter))

    # 检查 Markdown 内容
    markdown_content = parts[2].strip()
    if len(markdown_content) < 50:
        errors.append(f"{skill_dir.name}/SKILL.md: Markdown 内容过短（< 50 字符）")

    return errors


def _validate_frontmatter_fields(skill_dir, frontmatter):
    """校验 frontmatter 必选字段"""
    errors = []
    if not frontmatter.get("name"):
        errors.append(f"{skill_dir.name}/SKILL.md: 缺少 name 字段")
    if not frontmatter.get("description"):
        errors.append(f"{skill_dir.name}/SKILL.md: 缺少 description 字段")
    return errors


def _validate_name_consistency(skill_dir, frontmatter):
    """校验 SKILL.md name 与 skill.json name 一致"""
    errors = []
    skill_json_path = skill_dir / "skill.json"
    if skill_json_path.exists():
        try:
            with open(skill_json_path, encoding="utf-8") as f:
                skill_json = json.load(f)
            if frontmatter.get("name") != skill_json.get("name"):
                errors.append(
                    f"{skill_dir.name}: SKILL.md name ({frontmatter.get('name')}) "
                    f"与 skill.json name ({skill_json.get('name')}) 不一致"
                )
        except Exception:
            pass
    return errors


def validate_skill(data, filepath):
    """校验单个 skill.json"""
    errors = []

    # 校验顶层字段
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"[{filepath}] Missing '{field}'")

    # 校验 tier
    if data.get("tier") not in VALID_TIERS:
        errors.append(f"[{filepath}] Invalid tier '{data.get('tier')}'")

    # 校验 tools（MCP 格式）
    for tool in data.get("tools", []):
        for field in REQUIRED_TOOL_FIELDS:
            if field not in tool:
                errors.append(f"[{filepath}] Missing tool field '{field}' in tool '{tool.get('name', '?')}'")

        # 校验 inputSchema（JSON Schema）
        schema = tool.get("inputSchema", {})
        for field in REQUIRED_SCHEMA_FIELDS:
            if field not in schema:
                errors.append(f"[{filepath}] Missing inputSchema field '{field}' in tool '{tool.get('name', '?')}'")

    return errors


def main():
    skills_dir = Path("skills")
    errors = []

    # 校验 skill.json
    for skill_json in skills_dir.rglob("skill.json"):
        with open(skill_json, encoding="utf-8") as f:
            data = json.load(f)
        skill_errors = validate_skill(data, skill_json)
        for err in skill_errors:
            print(err)
        errors.extend(skill_errors)

    # 校验 SKILL.md
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_md_errors = validate_skill_md(skill_dir)
            for err in skill_md_errors:
                print(err)
            errors.extend(skill_md_errors)

    sys.exit(len(errors))


if __name__ == "__main__":
    main()
