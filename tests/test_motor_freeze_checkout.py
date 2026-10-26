"""Real Git checkout and conservative repair tests; no physics/CNS fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from malecns_backend.embodiment import motor_freeze_checkout as checkout


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)


def repository(root, payloads, attributes):
    root.mkdir()
    git(root, 'init', '--quiet')
    git(root, 'config', 'core.autocrlf', 'false')
    (root / '.gitattributes').write_bytes(attributes)
    for name, raw in payloads.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    git(root, 'add', '--all')
    hooks = root / 'empty-hooks'
    hooks.mkdir()
    git(root, '-c', 'core.hooksPath=' + str(hooks), '-c', 'commit.gpgsign=false',
        '-c', 'user.name=Checkout test', '-c', 'user.email=checkout@example.invalid',
        'commit', '--quiet', '-m', 'Frozen originals')


@pytest.fixture
def small_repo(tmp_path, monkeypatch):
    root = tmp_path / 'fixture'
    payloads = {name: (json.dumps({'original': index}, indent=2) + '\n').encode()
                for index, name in enumerate(['a.json', 'b.json', 'c.json'])}
    repository(root, payloads, b'*.json -text\n')
    locks = [(name, hashlib.sha256(raw).hexdigest()) for name, raw in payloads.items()]
    monkeypatch.setattr(checkout, 'original_locks', lambda root: locks)
    for name, raw in payloads.items():
        (root / name).write_bytes(raw.replace(b'\n', b'\r\n'))
    return root, payloads


@pytest.mark.parametrize('autocrlf', ['true', 'input', 'false'])
def test_real_git_checkout_preserves_original_frozen_bytes(tmp_path, monkeypatch, autocrlf):
    source = checkout.audit.ROOT
    locks = checkout.original_locks(source)
    payloads = {path: git(source, 'show', 'HEAD:' + path) for path, _ in locks}
    root = tmp_path / 'checkout'
    repository(root, payloads, (source / '.gitattributes').read_bytes())
    for path in payloads:
        (root / path).unlink()  # Only disposable fixture files.
    git(root, '-c', 'core.autocrlf=' + autocrlf, 'checkout-index', '--all')
    monkeypatch.setattr(checkout, 'original_locks', lambda root: locks)
    assert all(row['raw_lock_passed'] for row in checkout.inspect(root))
    for path, expected in locks:
        assert (root / path).read_bytes() == payloads[path]
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected


def test_git_control_without_attributes_reproduces_crlf_failure(tmp_path):
    root = tmp_path / 'unprotected'
    raw = b'{\n  "frozen": true\n}\n'
    repository(root, {'frozen.json': raw}, b'')
    (root / 'frozen.json').unlink()
    git(root, '-c', 'core.autocrlf=true', 'checkout-index', '--all')
    assert (root / 'frozen.json').read_bytes() == raw.replace(b'\n', b'\r\n')
    assert checkout.sha((root / 'frozen.json').read_bytes()) != checkout.sha(raw)


def test_repair_backs_up_exact_previous_bytes_and_is_idempotent(small_repo):
    root, payloads = small_repo
    before = {name: (root / name).read_bytes() for name in payloads}
    backup = root / 'backups' / 'first'
    assert not any(row['raw_lock_passed'] for row in checkout.inspect(root))
    assert all(row['raw_lock_passed'] for row in checkout.restore(root, backup))
    for name, raw in payloads.items():
        assert (root / name).read_bytes() == raw
        assert (backup / name).read_bytes() == before[name]
    manifest = json.loads((backup / 'backup.json').read_text())
    assert len(manifest) == 3
    assert all(row['before_sha256'] == checkout.sha(before[row['path']]) for row in manifest)
    assert all(row['raw_lock_passed'] for row in checkout.restore(root, backup))
    assert git(root, 'diff', '--name-only') == b''


@pytest.mark.parametrize('defect', ['working_content', 'staged_content', 'staged_mode', 'freeze', 'attribute'])
def test_all_inputs_checked_before_any_write_or_backup(small_repo, monkeypatch, defect):
    root, payloads = small_repo
    if defect in ['working_content', 'staged_content']:
        (root / 'c.json').write_bytes(b'{"scientific_change": true}\n')
        if defect == 'staged_content':
            git(root, 'add', 'c.json')
            (root / 'c.json').write_bytes(payloads['c.json'])
    elif defect == 'staged_mode':
        git(root, 'update-index', '--chmod=+x', 'c.json')
    elif defect == 'freeze':
        monkeypatch.setattr(checkout, 'original_locks', lambda root: [('c.json', '0' * 64)])
    else:
        (root / '.gitattributes').write_bytes(b'*.json text\n')
    before = {name: (root / name).read_bytes() for name in payloads}
    backup = root / 'never-created'
    with pytest.raises(ValueError):
        checkout.restore(root, backup)
    assert not backup.exists()
    assert before == {name: (root / name).read_bytes() for name in payloads}


def test_backup_namespace_collision_never_overwrites(small_repo):
    root, payloads = small_repo
    backup = root / 'existing'
    backup.mkdir()
    (backup / 'keep').write_bytes(b'older evidence')
    before = {name: (root / name).read_bytes() for name in payloads}
    with pytest.raises(FileExistsError):
        checkout.restore(root, backup)
    assert (backup / 'keep').read_bytes() == b'older evidence'
    assert before == {name: (root / name).read_bytes() for name in payloads}


def test_change_during_backup_refuses_repair(small_repo, monkeypatch):
    root, payloads = small_repo
    original = checkout.inspect
    calls = []

    def changed_checkout(path):
        calls.append(path)
        if len(calls) == 2:
            (root / 'c.json').write_bytes(b'concurrent user edit')
        return original(path)

    monkeypatch.setattr(checkout, 'inspect', changed_checkout)
    backup = root / 'before-concurrent-edit'
    with pytest.raises(ValueError):
        checkout.restore(root, backup)
    assert (root / 'c.json').read_bytes() == b'concurrent user edit'
    for name, raw in payloads.items():
        assert (backup / name).read_bytes() == raw.replace(b'\n', b'\r\n')


def test_cli_default_is_read_only_and_repair_requires_backup(small_repo, monkeypatch, capsys):
    root, payloads = small_repo
    monkeypatch.setattr(checkout.audit, 'ROOT', root)
    assert checkout.main([]) == 1
    assert '0/3' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        checkout.main(['--repair'])
    with pytest.raises(SystemExit):
        checkout.main(['--execute'])
    assert all((root / name).read_bytes() != raw for name, raw in payloads.items())
    assert checkout.main(['--repair', '--backup-dir', str(root / 'saved')]) == 0
    assert '3/3' in capsys.readouterr().out


def test_atomic_replace_failure_retains_originals_and_backups(small_repo, monkeypatch):
    root, payloads = small_repo
    before = {name: (root / name).read_bytes() for name in payloads}

    def refused(*args):
        raise OSError('fixture replacement failure')

    monkeypatch.setattr(checkout.os, 'replace', refused)
    backup = root / 'safe-backup'
    with pytest.raises(OSError):
        checkout.restore(root, backup)
    assert before == {name: (root / name).read_bytes() for name in payloads}
    assert before == {name: (backup / name).read_bytes() for name in payloads}
    assert not list(root.glob('tmp*'))
