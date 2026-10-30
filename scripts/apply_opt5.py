#!/usr/bin/env python3
"""Apply opt2..opt5 to clean pinned upstream android-v0.9.0."""
from pathlib import Path
import subprocess,sys
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1] if len(sys.argv)>1 else 'upstream').resolve()
subprocess.run([sys.executable,str(repo/'scripts/apply_opt4.py'),str(root)],check=True)
subprocess.run(['git','apply','--check',str(repo/'opt5.patch')],cwd=root,check=True)
subprocess.run(['git','apply',str(repo/'opt5.patch')],cwd=root,check=True)
print('Applied opt5: retain real endpoints, DMA presentation polling, mobile optical shader and display requests')
