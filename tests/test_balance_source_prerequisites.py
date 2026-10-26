"""Small source-identity checks, never native/CNS initialization."""
import hashlib
import io
import json
from unittest.mock import patch

import pytest

from malecns_backend.live import balance_source_prerequisites as p


def identity(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def test_stream_identity_spans_multiple_chunks_without_decoding():
    raw=b'\x00\xfforiginal graph\n'*(1024*128)
    assert p.stream_identity(io.BytesIO(raw))==identity(raw)


def test_missing_source_fails_before_any_loader_construction(tmp_path):
    result=p.check_graph(graph_path=tmp_path/'missing',expected_reader=lambda:identity(b'original'))
    assert not result['verified'] and 'FileNotFoundError' in result['error']


@pytest.mark.parametrize('changed',[b'changed',b'original\n',b'version https://git-lfs.github.com/spec/v1\n'])
def test_changed_or_pointer_bytes_never_refresh_expected_identity(tmp_path,changed):
    path=tmp_path/'graph';path.write_bytes(changed)
    result=p.check_graph(graph_path=path,expected_reader=lambda:identity(b'original'))
    assert not result['verified'] and result['expected']==identity(b'original')
    assert path.read_bytes()==changed


def test_exact_original_bytes_pass_read_only(tmp_path):
    path=tmp_path/'graph';path.write_bytes(b'original')
    assert p.check_graph(graph_path=path,expected_reader=lambda:identity(b'original'))['verified']
    assert path.read_bytes()==b'original'


def test_combined_check_does_not_promote_failed_original_prerequisite():
    from malecns_backend.live import balance_contribution as original
    with patch.object(p,'check_graph',return_value=dict(verified=True)),patch.object(original,'preflight',return_value=dict(verified=False)):
        report=p.check()
    assert not report['verified'] and not report['scientific_execution_authorized_by_this_check']
    assert report['native_constructions']==report['cns_initializations']==report['scientific_transitions']==0


def test_existing_receipt_never_overwritten_and_no_check_called(tmp_path):
    output=tmp_path/'receipt.json';output.write_text('preserved')
    with patch.object(p,'check',side_effect=AssertionError('ran check')):
        with pytest.raises(SystemExit):p.main(['--output',str(output)])
    assert output.read_text()=='preserved'


def test_original_git_authority_is_fixed_by_frozen_design():
    expected=p.original_graph_identity()
    assert expected['revision']=='2bcd10312ee64618a91ea23d6e6e586c4a93280d'
    assert expected['bytes']==63726728 and len(expected['sha256'])==64


def test_retained_attempt_reconstruction_rejects_without_native_or_cns_construction():
    from malecns_backend.live import controlled_live_balance as live
    from malecns_backend.neural import MaleCNSBrain
    folder=p.ROOT/'docs/evidence/controlled-live-balance-v1/run-desktop-01'
    if not (folder/'report.json').exists(): pytest.skip('retained failure receipt unavailable')
    report=json.loads((folder/'report.json').read_text())
    with patch.object(live.base,'audit_arm',side_effect=AssertionError('must not audit incomplete arm')), \
            patch.object(live.base,'create_session',side_effect=AssertionError('native construction forbidden')), \
            patch.object(MaleCNSBrain,'__init__',side_effect=AssertionError('CNS construction forbidden')):
        result=live.evaluate(report,folder,loader=lambda *a:pytest.fail('loaded incomplete campaign'))
    assert result==report['evaluation']
    assert not result['scientific']['accepted'] and result['scientific']['behavior'] is None
    assert report['run_status']=='INCOMPLETE' and list(report['arm_artifacts'])==['NC']


def test_retained_initialization_failure_and_zero_pose_evidence_are_unchanged():
    from malecns_backend.live import controlled_live_balance as live
    folder=p.ROOT/'docs/evidence/controlled-live-balance-v1/run-desktop-01'
    path=folder/'NC.json.gz'
    if not path.exists() or path.read_bytes().startswith(b'version https://git-lfs'):
        pytest.skip('hydrate retained raw failure via Git LFS for this check')
    receipt=json.loads((folder/'NC.done.json').read_text())
    assert receipt['artifact']['sha256']=='6ac0e14fafd70d6e49dd4a68d06ea245f5ff03fe9fce08ea3cbf825525ac5adf'
    assert receipt['display_artifact']['sha256']=='9c7414a90d28603381d2f7d35962dc8d00d1d059c345da1c99eb40237213e84d'
    arm=live.original.read_arm(folder,'NC',receipt['artifact'])
    display=live.read_display(folder,'NC',receipt['display_artifact'])
    assert arm['error']=='ValueError: MaleCNS validation failed:\n- graph_w3.bin unavailable for graph orientation source comparison'
    assert arm['samples']==arm['neural']==[] and arm['run_status']=='ERROR'
    assert arm['initialization_operations']=={'call:malecns_backend.loader.load_malecns':1}
    assert display['offers']==[] and display['sent_frames']==0
