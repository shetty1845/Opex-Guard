import subprocess
import sys

cmd = [r"d:\OpEx_Guard\venv\Scripts\python.exe", "-m", "unittest", "discover", "-s", "tests", "-q"]
proc = subprocess.run(cmd, capture_output=True, text=True)
print(proc.stdout)
print(proc.stderr)
raise SystemExit(proc.returncode)
