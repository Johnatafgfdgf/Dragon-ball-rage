#!/usr/bin/env python3
"""Apply cumulative opt2..opt6 to clean pinned android-v0.9.0 upstream."""
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1] if len(sys.argv)>1 else 'upstream').resolve()
subprocess.run([sys.executable,str(repo/'scripts/apply_opt5.py'),str(root)],check=True)
subprocess.run(['git','apply','--check',str(repo/'opt6.patch')],cwd=root,check=True)
subprocess.run(['git','apply',str(repo/'opt6.patch')],cwd=root,check=True)
print('Applied opt6 pipeline observer, presentation pacing, rollback isolation and GPU quality hysteresis')
