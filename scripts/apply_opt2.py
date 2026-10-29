#!/usr/bin/env python3
"""Apply the reviewed opt2 patch to clean upstream android-v0.9.0 source."""
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
root = Path(sys.argv[1] if len(sys.argv) > 1 else "upstream").resolve()
patch = repo / "opt2.patch"
if not (root / "port/src/gs/gs_draw.c").is_file():
    raise SystemExit("Expected a clean Tenkaichi3DecompAndroid android-v0.9.0 checkout")
subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)
subprocess.run(["git", "apply", str(patch)], cwd=root, check=True)
print("Applied opt2 native interpolation, pacing policy, thermal, cache and diagnostics patch")
