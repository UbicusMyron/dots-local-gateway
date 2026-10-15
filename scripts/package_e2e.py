"""Build allowlisted delivery bundles; local configuration remains on the gateway."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
out = root / 'dist'
out.mkdir(exist_ok=True)
shared = [root/'requirements-e2e.txt', root/'docs/E2E-RUNBOOK.md', root/'docs/CONTRACTS/e2e-v1.md']
client = [p for p in (root/'dots_request').rglob('*')
          if p.is_file() and p.suffix in ('.py', '.md', '.json') and '__pycache__' not in p.parts]
gateway = [p for p in (root/'macmini_gateway').rglob('*')
           if p.is_file() and p.suffix in ('.py', '.md', '.json')
           and 'local' not in p.relative_to(root).parts and '__pycache__' not in p.parts]
scripts = list((root/'scripts').glob('*.py'))
for name, files in [('dots-request-e2e.zip', shared+client+[root/'scripts/install_dots.py']),
                    ('macmini-gateway-e2e.zip', shared+client+gateway+scripts)]:
    with ZipFile(out/name, 'w', ZIP_DEFLATED) as archive:
        for file in sorted(set(files)):
            archive.write(file, file.relative_to(root))
    print(str(out/name))
