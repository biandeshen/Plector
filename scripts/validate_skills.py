#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "name", "description", "version", "tier",
    "dependencies", "events_produced", "events_consumed", "methods"
]

VALID_TIERS = ["tier_0_kernel", "tier_1_system", "tier_2_functional", "tier_3_tool"]

def main():
    errors = 0
    for skill_json in Path("skills").rglob("skill.json"):
        with open(skill_json, encoding="utf-8") as f:
            data = json.load(f)
        for field in REQUIRED_FIELDS:
            if field not in data:
                print(f"Missing '{field}' in {skill_json}")
                errors += 1
        if data.get("tier") not in VALID_TIERS:
            print(f"Invalid tier '{data.get('tier')}' in {skill_json}")
            errors += 1
    sys.exit(errors)

if __name__ == "__main__":
    main()
