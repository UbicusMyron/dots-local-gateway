"""Install the official, checksum-verified tunnel client in the local runtime directory."""
import hashlib
import io
import json
from pathlib import Path
import platform
import ssl
import urllib.request
from zipfile import ZipFile
import certifi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'macmini_gateway/local/bin'


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gateway-e2e-setup'}),
                                context=ssl.create_default_context(cafile=certifi.where()), timeout=120) as response:
        return response.read()


def main():
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise SystemExit('This installer targets the test Mac (Darwin arm64).')
    release = json.loads(fetch('https://api.github.com/repos/openai/tunnel-client/releases/latest'))
    name = f"tunnel-client-{release['tag_name']}-darwin-arm64.zip"
    asset = next(a for a in release['assets'] if a['name'] == name)
    payload = fetch(asset['browser_download_url'])
    digest = 'sha256:' + hashlib.sha256(payload).hexdigest()
    if asset.get('digest') != digest:
        raise SystemExit('Release checksum verification failed')
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    with ZipFile(io.BytesIO(payload)) as archive:
        candidates = [n for n in archive.namelist() if Path(n).name == 'tunnel-client']
        if len(candidates) != 1:
            raise SystemExit('Expected exactly one tunnel-client executable')
        target = OUT / 'tunnel-client'
        if target.exists():
            raise SystemExit('Existing tunnel-client preserved; choose an explicit upgrade workflow')
        target.write_bytes(archive.read(candidates[0]))
        target.chmod(0o700)
    (OUT / 'release.json').write_text(json.dumps({'version': release['tag_name'], 'asset': name, 'sha256': digest}))
    print('Installed verified official tunnel-client ' + release['tag_name'])


if __name__ == '__main__':
    main()
