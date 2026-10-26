"""Exact original evidence bytes across real Git checkout newline policies."""
import hashlib
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('malecns_backend/embodiment/interface_output/tactile_motor_closed_loop_100ms.json',
     'd684f38cd50edf6f494f00678d33a67c8cd89b50a34fd4815d5af90f05611e09'),
    ('malecns_backend/embodiment/interface_output/tactile_motor_matched_control_preflight.json',
     '15e83fa88aa3e7a6206ea7bb736cd1ec446874dcf44079e0b79bcbf39c594901'),
)


@pytest.mark.parametrize('relative,expected', CASES)
@pytest.mark.parametrize('autocrlf', ('true', 'input', 'false'))
def test_original_raw_lock_survives_fresh_checkout(tmp_path, relative, expected, autocrlf):
    def git(*args):
        return subprocess.check_output(['git', '-c', f'safe.directory={tmp_path.as_posix()}', *args], cwd=tmp_path)
    original = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                                       'show', 'HEAD:' + relative], cwd=ROOT)
    assert hashlib.sha256(original).hexdigest() == expected
    attributes = (ROOT / '.gitattributes').read_text(encoding='utf-8')
    assert relative + ' -text' in attributes.splitlines()
    git('init', '-q')
    git('config', 'core.autocrlf', autocrlf)
    git('config', 'user.name', 'Checkout test')
    git('config', 'user.email', 'checkout-test@example.invalid')
    (tmp_path / '.gitattributes').write_text(attributes, encoding='utf-8')
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_bytes(original)
    # A contrasting unprotected text file demonstrates that the selected Git
    # newline policy actually takes effect in this fixture.
    (tmp_path / 'control.txt').write_bytes(b'first\nsecond\n')
    git('add', '.gitattributes', relative, 'control.txt')
    git('commit', '-qm', 'original locked bytes')
    target.unlink()
    (tmp_path / 'control.txt').unlink()
    git('checkout-index', '-f', '--', relative, 'control.txt')
    assert target.read_bytes() == original
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
    assert (tmp_path / 'control.txt').read_bytes() == (
        b'first\r\nsecond\r\n' if autocrlf == 'true' else b'first\nsecond\n')
