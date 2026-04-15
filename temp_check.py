#!/usr/bin/env python3
import re
with open("skills/context_refresher/implementation.py", "r", encoding="utf-8") as f:
    content = f.read()
    
# Find the function and its indentation
pattern = r'    def build_injected_context\([^)]+\)[^:]*?:\s*""".*?"""'
match = re.search(pattern, content, re.DOTALL)
if match:
    print(f"Found at position {match.start()}-{match.end()}")
    print("=" * 60)
    print(repr(match.group()))
else:
    print("Pattern not found")
