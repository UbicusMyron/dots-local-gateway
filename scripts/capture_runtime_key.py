"""Administrator private input for the Tunnel runtime key."""
import getpass
import os
from pathlib import Path
import re

path = Path(__file__).resolve().parents[1]/'macmini_gateway/local/e2e/tunnel-runtime.secret'
if path.exists():
    raise SystemExit('Runtime key already saved locally; existing credential preserved. No need to enter it again.')
key = getpass.getpass('Paste the OpenAI Tunnel runtime key (hidden): ')
if not re.fullmatch(r'[!-~]{8,4096}',key):
    raise SystemExit('Invalid credential format')
try:
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
except FileExistsError:
    raise SystemExit('Runtime key already saved locally; existing credential preserved.') from None
with os.fdopen(fd,'w') as f:f.write(key+'\n')
print('Runtime key saved locally; value omitted.')
