"""Simulate installed dots -> official tunnel proxy -> stdio bridge -> resident MCP."""
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'macmini_gateway/local/bin/tunnel-client'


def wait_file(path, processes, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('A simulation process exited')
        if path.exists():
            try:
                return json.loads(path.read_text())
            except ValueError:
                pass
        time.sleep(.1)
    raise RuntimeError('Simulation readiness timed out')


def main():
    processes = []
    with tempfile.TemporaryDirectory(prefix='gateway-handoff-') as directory:
        tmp = Path(directory)
        local, installed = tmp/'runtime', tmp/'dots'
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        subprocess.run([sys.executable, 'scripts/prepare_e2e.py', '--directory', str(local), '--port', str(port)],
                       cwd=ROOT, check=True, capture_output=True)
        config = json.loads((local/'mock.json').read_text())
        config['services']['opencode_go'] = {
            'origin':'https://example.invalid', 'accounts':{'personal':{'type':'bearer','secret_file':'demo.secret'}},
            'routes':{'/inference/go/v1/chat/completions':{'method':'POST','response':'json','query':[],
                        'body_fields':['model','messages','stream','max_tokens']}}}
        config['services']['github'] = {
            'origin':'https://example.invalid', 'accounts':{'personal':{'type':'bearer','secret_file':'demo.secret'}},
            'routes':{'/orgs/example-org/repos':{'response':'json','query':['type','sort','direction','per_page','page']}}}
        (local/'mock.json').write_text(json.dumps(config))
        with ZipFile(ROOT/'dist/dots-request-e2e.zip') as z:
            z.extractall(installed)
        log = (tmp/'process.log').open('w+')
        try:
            gateway = subprocess.Popen([sys.executable,'-m','macmini_gateway.server','--config',str(local/'mock.json'),
                '--caller-secret',str(local/'caller.secret'),'--port',str(port),'--mock'],cwd=ROOT,stdout=log,stderr=log)
            processes.append(gateway)
            deadline = time.monotonic()+15
            while time.monotonic()<deadline:
                if gateway.poll() is not None: raise RuntimeError('Gateway startup failed')
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1): break
                except OSError: time.sleep(.1)
            url_file=tmp/'proxy.json'
            proxy = subprocess.Popen([str(BINARY),'dev','proxy','--mcp-command',shlex.quote(str(local/'tunnel-bridge.sh')),
                '--url-file',str(url_file),'--readiness-timeout','20s','--response-timeout','115s'],
                cwd=ROOT,stdout=log,stderr=log)
            processes.append(proxy)
            info=wait_file(url_file,processes)
            print(json.dumps({'proxy_connection_fields':list(info)}),flush=True)
            url=info['mcp_url']
            base=[sys.executable,'-m','dots_request.e2e','--url',url,'--caller-secret',str(local/'caller.secret')]
            reports=[]
            for mode,extra in [('mock',['--download',str(tmp/'download.txt')]),
                               ('opencode',['--model','fixture-model']),
                               ('github',['--org','example-org','--per-page','3'])]:
                result=subprocess.run(base+['--mode',mode]+extra,cwd=installed,capture_output=True,text=True,timeout=120)
                if result.returncode:
                    print(json.dumps({'failed_mode':mode,'diagnostic':result.stdout[:1000]}),flush=True)
                    raise RuntimeError('Installed client request failed')
                report=json.loads(result.stdout)
                if not report['ok']: raise RuntimeError('Business result failed')
                if mode=='github' and (report['total'],report['private_count'])!=(7,3):
                    raise RuntimeError('Repository fixture mismatch')
                if mode=='opencode' and report['reply']!='GATEWAY_E2E_OK':
                    raise RuntimeError('Inference fixture mismatch')
                reports.append({'mode':mode,'result':report})
            log.flush()
            raw=(tmp/'process.log').read_text()
            for name in ('caller.secret','demo.secret'):
                if (local/name).read_text().strip() in raw: raise RuntimeError('Log isolation failed')
            evidence={'ok':True,'scope':'installed client + official local tunnel proxy + stdio + authenticated gateway',
                      'reports':reports,'log_secret_check':True}
            target=ROOT/'macmini_gateway/local/e2e/full-simulation.json'
            target.write_text(json.dumps(evidence,indent=2))
            print(json.dumps(evidence))
        finally:
            for process in reversed(processes):
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait()
            log.close()


if __name__=='__main__':
    main()
