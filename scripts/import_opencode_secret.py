"""Import one administrator-selected .env entry locally, without displaying it."""
import argparse
import os
from pathlib import Path
import re
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--variable', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    try:
        value = dotenv_values(args.env_file, interpolate=False).get(args.variable)
        if not isinstance(value, str) or not re.fullmatch(r'[!-~]{8,4096}', value):
            raise ValueError
        fd = os.open(args.destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value + '\n')
    except Exception:
        parser.exit(1, 'Import failed; check the selected variable, local file and destination.\n')
    print('Credential imported to a new 0600 local file; value omitted.')


if __name__ == '__main__':
    main()
