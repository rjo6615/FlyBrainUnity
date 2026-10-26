"""Check or explicitly restore three frozen artifacts' original Git bytes.

This repairs checkout representation only. No simulation or admission is run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from . import remaining_leg_admission_audit as audit


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def original_locks(root):
    """Read unchanged expected hashes from the original freeze authorities."""
    records = []
    for key, freeze in [('mechanical', 'mechanical_freeze'), ('bridge', 'bridge_freeze')]:
        path = audit.PATHS[key]
        authority = json.loads((root / audit.PATHS[freeze]).read_text(encoding='utf-8'))
        records.append((path, authority['artifacts'][Path(path).name]['sha256']))
    authority = json.loads((root / audit.PATHS['registration_manifest']).read_text(encoding='utf-8'))
    records.append((audit.PATHS['registration'], authority['result']['sha256']))
    return records


def inspect(root):
    root = Path(root).resolve()
    head = git(root, 'rev-parse', 'HEAD')
    result = []
    for path, expected in original_locks(root):
        target = root / path
        if target.is_symlink() or target.resolve() != target:
            raise ValueError('ordinary in-checkout artifact path required: ' + path)
        tracked = git(root, 'show', 'HEAD:' + path)
        indexed = git(root, 'show', ':' + path)
        staged = git(root, 'diff', '--cached', '--name-only', 'HEAD', '--', path)
        if sha(tracked) != expected or indexed != tracked or staged.strip():
            raise ValueError('original Git/freeze/index disagreement; refusing repair: ' + path)
        # Attributes must protect future checkouts as well as this repair.
        attribute = git(root, 'check-attr', '-z', 'text', '--', path).split(b'\0')
        if attribute[2] != b'unset':
            raise ValueError('byte-preserving -text attribute required: ' + path)
        raw = target.read_bytes()
        if raw != tracked and raw.replace(b'\r\n', b'\n') != tracked:
            raise ValueError('working content differs beyond CRLF conversion; refusing repair: ' + path)
        result.append(dict(path=path, expected_sha256=expected, raw=raw, tracked=tracked,
                           raw_lock_passed=sha(raw) == expected))
    if git(root, 'rev-parse', 'HEAD') != head:
        raise ValueError('HEAD changed during inspection')
    return result


def restore(root, backup_dir):
    root = Path(root).resolve()
    records = inspect(root)  # Validate ALL inputs before any backup or replacement.
    if all(row['raw_lock_passed'] for row in records):
        return records
    backup = Path(backup_dir).resolve()
    # Exclusive namespace preserves every earlier repair and failed attempt.
    backup.mkdir(parents=True, exist_ok=False)
    for row in records:
        destination = backup / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(row['raw'])
    manifest = [dict(path=r['path'], before_sha256=sha(r['raw']),
                     original_expected_sha256=r['expected_sha256']) for r in records]
    with (backup / 'backup.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    # Recheck index, HEAD, authorities and all files after backups, before writing.
    current = inspect(root)
    if current != records:
        raise ValueError('checkout changed after inspection; backups retained, repair refused')
    for row in records:
        if row['raw_lock_passed']:
            continue
        path = root / row['path']
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(row['tracked'])
            os.chmod(temporary, path.stat().st_mode)
            if path.read_bytes() != row['raw']:
                raise ValueError('file changed before replacement; backups retained: ' + row['path'])
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return inspect(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repair', action='store_true', help='restore original Git bytes after exclusive backups')
    parser.add_argument('--backup-dir', type=Path, help='new directory required when repair is needed')
    args = parser.parse_args(argv)
    if args.repair and args.backup_dir is None:
        parser.error('--repair requires --backup-dir')
    if args.backup_dir is not None and not args.repair:
        parser.error('--backup-dir requires --repair')
    try:
        records = restore(audit.ROOT, args.backup_dir) if args.repair else inspect(audit.ROOT)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print('CHECKOUT CHECK/REPAIR REFUSED:', exc)
        return 1
    passed = sum(row['raw_lock_passed'] for row in records)
    print(f'Original motor/sign/registration raw locks: {passed}/3')
    print('No motor admission changes. Checkout repair does not satisfy anatomical, neural or behavioral gates.')
    return 0 if passed == 3 else 1


if __name__ == '__main__':
    raise SystemExit(main())
