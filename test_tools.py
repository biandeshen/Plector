#!/usr/bin/env python3
"""测试tools schema"""
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from core.tool_registry import ToolRegistry
from core.skill_registry import SkillRegistry

sr = SkillRegistry()
tr = ToolRegistry(sr)

schemas = tr.get_tool_schemas()
print("Total tools:", len(schemas))
for s in schemas[:3]:
    fn = s.get("function", {})
    print(" -", fn.get("name"), ":", fn.get("description", "")[:60])
