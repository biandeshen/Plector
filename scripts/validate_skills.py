#!/usr/bin/env python3
"""
校验 skill.json 是否符合 MCP Tool 格式规范
"""
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "name", "description", "version", "tier",
    "dependencies", "events_produced", "events_consumed", "tools"
]

VALID_TIERS = ["tier_0_kernel", "tier_1_system", "tier_2_functional", "tier_3_tool"]

REQUIRED_TOOL_FIELDS = ["name", "description", "inputSchema"]

REQUIRED_SCHEMA_FIELDS = ["type", "properties", "required", "additionalProperties"]


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
    errors = 0
    for skill_json in Path("skills").rglob("skill.json"):
        with open(skill_json, encoding="utf-8") as f:
            data = json.load(f)
        skill_errors = validate_skill(data, skill_json)
        for err in skill_errors:
            print(err)
        errors += len(skill_errors)
    sys.exit(errors)


if __name__ == "__main__":
    main()
