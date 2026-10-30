#!/usr/bin/env python3
"""Apply opt2, opt3 and the opt4 optical-budget correction to pinned upstream."""
from pathlib import Path
import subprocess, sys
repo=Path(__file__).resolve().parents[1]
root=Path(sys.argv[1] if len(sys.argv)>1 else 'upstream').resolve()
subprocess.run([sys.executable,str(repo/'scripts/apply_opt3.py'),str(root)],check=True)
subprocess.run(['git','apply','--check',str(repo/'opt4.patch')],cwd=root,check=True)
subprocess.run(['git','apply',str(repo/'opt4.patch')],cwd=root,check=True)
print('Applied opt4: separate scene/extra budgets, pacing accounting and live FG telemetry')
