#!/usr/bin/env python3
"""Apply cumulative opt2..opt7 to clean pinned android-v0.9.0 upstream."""
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1] if len(sys.argv)>1 else 'upstream').resolve()
subprocess.run([sys.executable,str(repo/'scripts/apply_opt6.py'),str(root)],check=True)
subprocess.run(['git','apply','--check',str(repo/'opt7.patch')],cwd=root,check=True)
subprocess.run(['git','apply',str(repo/'opt7.patch')],cwd=root,check=True)
print('Applied opt7 fractional presentation cadence, skipped-source history, Vulkan desired time and truthful completion counters')
