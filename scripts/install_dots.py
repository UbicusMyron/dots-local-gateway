"""Install the extracted dots client using a local Python 3.11+ environment."""
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parents[1]
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 or later is required.')
venv.EnvBuilder(with_pip=True).create(root/'.venv')
python = root/'.venv/bin/python'
subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root/'requirements.txt')], check=True)
print('Installation complete. See dots_request/README.md for client configuration.')
