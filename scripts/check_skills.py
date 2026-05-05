#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main():
    errors = 0
    for impl in Path("skills").rglob("implementation.py"):
        result = subprocess.run([sys.executable, "-m", "py_compile", str(impl)], capture_output=True)
        if result.returncode != 0:
            print(f"Syntax error in {impl}:")
            print(result.stderr.decode())
            errors += 1
    sys.exit(errors)


if __name__ == "__main__":
    main()
