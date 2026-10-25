"""Static replay of existing identity/reference checks without live enumeration.

Reuses the original validators and source locks; does not call audit.build or
crosswalk.verify, whose inventory path constructs a FlyGym model.
"""
import json

from . import remaining_leg_admission_audit as audit
from . import lf_anatomical_crosswalk as cross


def load():
    root = audit.ROOT
    read = lambda p: json.loads((root/p).read_text(encoding='utf-8'))
    saved = read(cross.UPSTREAM)
    before = audit.snapshot()
    for phase in ('source_hashes_before', 'source_hashes_after'):
        if set(before) != set(saved[phase]) or any(before[p]['canonical_content_sha256'] !=
                saved[phase][p]['canonical_content_sha256'] for p in before):
            raise ValueError('original audit canonical source identity mismatch')
    data = {k: read(p) for k, p in audit.PATHS.items() if k != 'neurons'}
    freezes = []
    for key, freeze in (('mechanical', 'mechanical_freeze'), ('bridge', 'bridge_freeze')):
        path = audit.PATHS[key]
        freezes.append(audit.frozen_record(path, data[freeze]['artifacts'][path.rsplit('/', 1)[1]]['sha256']))
    freezes.append(audit.frozen_record(audit.PATHS['registration'], data['registration_manifest']['result']['sha256']))
    count, body_ids, *_ = audit.decode_neurons(root/audit.PATHS['neurons'])
    if count != len(body_ids) or len(set(body_ids)) != count:
        raise ValueError('neuron body-ID index is not unique')
    populations, muscles = {}, {}
    for p in data['interface']['populations']: populations.setdefault(p['name'], []).append(p)
    for p in data['bodymap']['muscles']: muscles.setdefault(p['name'], []).append(p)
    lf = audit.inspect_lf(data['registration'], data['candidates'], data['recruitment'], populations, muscles, body_ids)
    if lf != saved['lf_reference']:
        raise ValueError('original LF identity/null/covector checks differ')

    # Rebuild metadata through the original locked authority, deliberately without
    # old._inventory(), enumerate_live_actuators(), or a synthetic physical record.
    from . import _windows_m7_spontaneous_locomotion_adapter as old
    protocol = old.build_live_protocol()
    protocol, records, table = audit.v2.derive_v2(protocol, [], protocol['actuator_admission_table'])
    protocol, records, table = audit.v3.derive_v3(protocol, records, table)
    if records or [r['actuator'] for r in table] != list(audit.JOINT_NAMES):
        raise ValueError('static admission order mismatch')
    mapping = {r['actuator']: r for r in data['mapping']['per_actuator']}
    rows = [audit.row_record(mapping[r['actuator']], r, populations, muscles, body_ids, data['bridge'])
            for r in table if not r['neural_motor_admission']]
    if rows != saved['rows'] or sum(r['neural_motor_admission'] for r in table) != 20:
        raise ValueError('original remaining rows/current static admission mismatch')

    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather
    raw = (root/cross.SOURCE).read_bytes()
    if audit.sha(raw) != cross.SOURCE_SHA:
        raise ValueError('official annotation raw hash mismatch')
    source = feather.read_table(pa.BufferReader(raw))
    selected = source.filter(pc.is_in(source['type'], value_set=pa.array(list(cross.ATLAS))))
    cross_rows = cross.crosswalk(selected.to_pylist(), lf['candidate_identities'])
    saved_cross = read(cross.DIRECTORY+'crosswalk.json')
    if saved_cross['neurons'] != cross_rows:
        raise ValueError('official source crosswalk differs')
    for p, expected in saved_cross['source_hashes'].items():
        if audit.sha((root/p).read_bytes().replace(b'\r\n', b'\n')) != expected:
            raise ValueError('crosswalk canonical source mismatch: '+p)
    if audit.snapshot() != before:
        raise ValueError('original sources changed during static replay')
    return dict(registration=data['registration'], candidates=data['candidates'], lf=lf,
                static_admission_table=table, freezes=freezes,
                original_raw_freezes_satisfied=all(r['raw_lock_passed'] for r in freezes))
