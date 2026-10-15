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
subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root/'requirements-e2e.txt')], check=True)
print('Installation complete. Configure the verified MCP endpoint with:')
print('.venv/bin/python -m dots_request.connection configure --url YOUR_VERIFIED_MCP_URL')
