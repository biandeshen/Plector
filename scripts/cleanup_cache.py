#!/usr/bin/env python3
import shutil
from pathlib import Path

# Clean cache directories
for cache in ['.pytest_cache', '.ruff_cache', '__pycache__']:
    p = Path(cache)
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
        print(f"Removed {cache}")

# Find and clean all __pycache__ directories
for pycache in Path('.').rglob('__pycache__'):
    shutil.rmtree(pycache, ignore_errors=True)
    print(f"Removed {pycache}")

print("Cache cleanup complete")
