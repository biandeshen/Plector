#!/usr/bin/env python
"""Test import"""
import sys
sys.path.insert(0, ".")
try:
    from core.event_bus import EventBus
    print("SUCCESS: core.event_bus imported")
except ImportError as e:
    print(f"FAILED: {e}")

try:
    from core.skill_sandbox import SkillSandbox
    print("SUCCESS: core.skill_sandbox imported")
except ImportError as e:
    print(f"FAILED: {e}")
