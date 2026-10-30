#!/usr/bin/env python3
"""Apply opt2 and then the opt3 optical flow patch to pinned clean upstream."""
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1] if len(sys.argv)>1 else 'upstream').resolve()
subprocess.run([sys.executable,str(repo/'scripts/apply_opt2.py'),str(root)],check=True)
subprocess.run(['git','apply','--check',str(repo/'opt3.patch')],cwd=root,check=True)
subprocess.run(['git','apply',str(repo/'opt3.patch')],cwd=root,check=True)
print('Applied opt3: actual bidirectional GPU optical flow and image-only 2x/3x/4x presentation')
