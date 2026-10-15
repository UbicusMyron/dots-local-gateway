"""Exercise real GitHub through a temporary local MCP service, with safe output."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'macmini_gateway/local/e2e'


def main():
    os.umask(0o077)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    with (LOCAL / 'github-preflight.log').open('a') as log:
        process = subprocess.Popen([sys.executable, '-m', 'macmini_gateway.server',
            '--config', str(LOCAL / 'github.json'), '--caller-secret', str(LOCAL / 'caller.secret'),
            '--port', str(port)], cwd=ROOT, stdout=log, stderr=log)
        try:
            for _ in range(200):
                if process.poll() is not None:
                    raise RuntimeError('Local service startup failed')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=.1):
                        break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Local service startup timed out')
            result = subprocess.run([sys.executable, '-m', 'dots_request.e2e',
                '--url', f'http://127.0.0.1:{port}/mcp', '--caller-secret', str(LOCAL / 'caller.secret'),
                '--mode', 'github', '--org', 'CUHK-Business-School-AI-Hub', '--per-page', '5'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
            report = json.loads(result.stdout)
            # Defensive output check also covers CLI diagnostics before persisting.
            for name in ('github.secret', 'caller.secret'):
                if (LOCAL / name).read_text().strip() in result.stdout:
                    raise RuntimeError('Output isolation failed')
            (LOCAL / 'github-repositories.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(json.dumps(report, ensure_ascii=False))
            return result.returncode
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    try:
        status = main()
    except Exception:
        print('{"ok":false,"error":"PREFLIGHT_FAILED"}')
        status = 1
    sys.exit(status)
