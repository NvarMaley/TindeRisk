"""Restore the four large local inputs from checked, lossless gzip chunks."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path


def restore(verify_only=False):
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'data/archive_parts/manifest.json').read_text())
    for entry in manifest:
        target = root / entry['path']
        if target.exists() and not verify_only:
            with target.open('rb') as source:
                actual = hashlib.file_digest(source, 'sha256').hexdigest()
            if actual != entry['sha256']:
                raise ValueError(f'Existing file differs; move it before restoring: {target}')
            print(f'Already restored: {entry["path"]}', flush=True)
            continue
        temporary = target.with_name(target.name + '.restoring')
        digest = hashlib.sha256()
        size = 0
        output = None
        try:
            if not verify_only:
                target.parent.mkdir(parents=True, exist_ok=True)
                output = temporary.open('xb')
            for part in entry['parts']:
                with gzip.open(root / part, 'rb') as source:
                    while block := source.read(1024 * 1024):
                        digest.update(block)
                        size += len(block)
                        if output:
                            output.write(block)
            if size != entry['size'] or digest.hexdigest() != entry['sha256']:
                raise ValueError(f'Archive integrity failure: {entry["path"]}')
            if output:
                output.close()
                output = None
                os.replace(temporary, target)
            print(f'{"Verified" if verify_only else "Restored"}: {entry["path"]}', flush=True)
        finally:
            if output:
                output.close()
            if not verify_only and temporary.exists():
                temporary.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true', help='Check archives without writing originals')
    restore(parser.parse_args().verify_only)
