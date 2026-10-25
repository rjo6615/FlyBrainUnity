"""Official-source identity and namespace checks; no CNS/physics experiments."""
import copy
import json

import pytest

from malecns_backend.embodiment import lf_anatomical_crosswalk as cross


@pytest.fixture
def identities():
    return json.loads((cross.ROOT/cross.UPSTREAM).read_text(encoding='utf-8'))['lf_reference']['candidate_identities']


@pytest.fixture
def rows(identities):
    result = []
    for p in identities:
        typ = p['name'].removesuffix(' T1 left')
        for b in p['body_ids']:
            result.append(dict(bodyId=b, type=typ, somaSide='L', rootSide=None, subclass='fl',
                superclass='vnc_motor', somaNeuromere='T1', exitNerve=cross.ATLAS[typ][3],
                mancBodyid=None, mancGroup=99., matchingNotes=None))
    return result


def test_namespaces_and_missing_matches_remain_distinct(rows, identities):
    rows[0]['mancBodyid'] = 123.
    result = cross.crosswalk(rows, identities)
    assert len(result) == 13
    assert result[0]['recorded_manc_body_match'] == 123
    assert result[1]['recorded_manc_body_match'] is None
    assert result[1]['original_annotation']['mancGroup'] == 99.
    assert result[0]['atlas_class_reference']['fanc_mn_set'] == [1, 2, 3, 4]
    assert all(r['individual_fanc_mn'] is None and r['model_tendon'] is None
               and r['decoder_vector'] is None and r['gain'] is None and not r['admission_ready'] for r in result)


@pytest.mark.parametrize('defect', ['missing', 'extra', 'duplicate', 'class', 'nerve', 'side', 'segment', 'superclass', 'fractional_match'])
def test_inconsistent_official_records_fail(rows, identities, defect):
    if defect == 'missing': rows.pop()
    if defect == 'extra': rows.append(dict(rows[0], bodyId=999))
    if defect == 'duplicate': rows.append(copy.deepcopy(rows[0]))
    if defect == 'class': rows[0]['type'] = 'Sternal adductor MN'
    if defect == 'nerve': rows[0]['exitNerve'] = 'ProAN'
    if defect == 'side': rows[0]['somaSide'] = 'R'
    if defect == 'segment': rows[0]['somaNeuromere'] = 'T2'
    if defect == 'superclass': rows[0]['superclass'] = 'vnc_interneuron'
    if defect == 'fractional_match': rows[0]['mancBodyid'] = 12.5
    with pytest.raises(ValueError): cross.crosswalk(rows, identities)


def test_original_side_fallback_is_used(rows, identities):
    rows[0]['somaSide'] = None
    rows[0]['rootSide'] = 'L'
    assert len(cross.crosswalk(rows, identities)) == 13


def test_saved_crosswalk_reproduces_full_official_bytes_and_identity_audit():
    saved, now = cross.verify(cross.ROOT/(cross.DIRECTORY+'crosswalk.json'))
    assert now['official_source']['total_rows'] == 211577
    assert now['official_source']['size_bytes'] == 14483314
    assert now['recorded_manc_body_match_count'] == 12
    assert now['unresolved_promotor_count'] == 4
    assert now['current_motor_count'] == 20 and now['new_admissions'] == now['scientific_transitions'] == 0
    missing = [r for r in saved['neurons'] if r['recorded_manc_body_match'] is None]
    assert [r['body_id'] for r in missing] == [1050335829]
    assert missing[0]['original_annotation']['mancGroup'] == 21241.
    assert all(r['original_annotation']['mancType']=='Tergopleural/Pleural promotor MN'
        for r in saved['neurons'] if r['original_annotation']['type']=='Tergopleural/Pleural promotor MN')


def test_raw_hash_error_is_explicit_and_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(cross, 'source_hashes', lambda: {})
    monkeypatch.setattr(cross, 'ROOT', tmp_path)
    source = tmp_path/cross.SOURCE
    source.parent.mkdir(parents=True)
    source.write_bytes(b'git-lfs pointer or changed release')
    output = tmp_path/'failed'
    assert cross.main(['--output-dir', str(output)]) == 1
    raw = (output/'crosswalk.json').read_bytes()
    assert 'raw hash mismatch' in json.loads(raw)['error']
    with pytest.raises(FileExistsError): cross.main(['--output-dir', str(output)])
    assert (output/'crosswalk.json').read_bytes() == raw
    with pytest.raises(SystemExit): cross.main(['--output-dir', str(output), '--execute'])


def test_tampered_crosswalk_is_rejected(tmp_path, monkeypatch):
    record = dict(schema=cross.SCHEMA, current_original_raw_freezes_satisfied=False,
                  model_tendon_assignment_count=0, new_admissions=0)
    monkeypatch.setattr(cross, 'build', lambda: copy.deepcopy(record))
    path = tmp_path/'crosswalk.json'
    path.write_text(json.dumps(record))
    assert cross.verify(path)[0] == record
    path.write_text(json.dumps(dict(record, model_tendon_assignment_count=1)))
    with pytest.raises(ValueError): cross.verify(path)
