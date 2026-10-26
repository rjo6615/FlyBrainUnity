"""Reconstruct distal annotation leads; never assigns a motor or runs a CNS."""
import argparse
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import re

from . import lf_anatomical_crosswalk as official
from . import lf_force_static_reference as static
from ..codec import decode_neurons

ROOT = official.ROOT
BASE = 'docs/evidence/distal-tarsus-reference-v1/'
SCHEMA = 'distal-tarsus-reference-v1.3'
SCOPE = re.compile(r'(?:tarsus|Ta)[ _](?:levator|depressor)(?:[ _]|$)', re.I)
LOCKS = {
    BASE+'banc_888_meta.feather': '86ccf5df0c67419f8c5f43e93a7ed38d23a080e9f7fde26737290252f3780098',
    BASE+'malecns_09_meta.feather': '1a75ae60fca67f76a97b95bab6c384f65b4f9115afd4834648146d16d46c75a4',
    official.SOURCE: official.SOURCE_SHA,
}
INPUTS = (*LOCKS, BASE+'source-provenance.json', 'docs/DISTAL_TARSUS_REFERENCE_V1.md',
          'docs/DISTAL_TARSUS_REFERENCE_V1_1.md',
          'docs/DISTAL_TARSUS_REFERENCE_V1_2.md',
          'docs/DISTAL_TARSUS_REFERENCE_V1_3.md',
          'malecns_backend/embodiment/distal_tarsus_reference.py',
          'malecns_backend/embodiment/lf_force_static_reference.py',
          'fly-brain-main/public/data/neurons.flyn', 'fly-brain-main/public/data/bodymap.json')
SEGMENTS = {'T1': ('fl', 'front_leg_motor_neuron', 'ProLN', 'prothoracic'),
            'T2': ('ml', 'middle_leg_motor_neuron', 'MesoLN', 'mesothoracic'),
            'T3': ('hl', 'hind_leg_motor_neuron', 'MetaLN', 'metathoracic')}


def snapshot():
    return {p: official.audit.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n')
                                 if p.endswith(('.py', '.md', '.json'))
                                 else (ROOT/p).read_bytes()) for p in INPUTS}


def reference_id(value):
    """Only exact canonical decimal strings; no float coercion or list selection."""
    if type(value) is str and re.fullmatch(r'[1-9][0-9]*', value):
        return int(value)
    return None


def json_safe(value):
    """Preserve IEEE non-finites distinctly from Arrow null; never impute data."""
    if isinstance(value, datetime):
        return {'__arrow_datetime_iso8601__': value.isoformat()}
    if isinstance(value, float) and not math.isfinite(value):
        tag = 'NaN' if math.isnan(value) else '+Infinity' if value > 0 else '-Infinity'
        return {'__arrow_nonfinite_float__': tag}
    if isinstance(value, dict): return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    return value


def selected(row):
    return any(SCOPE.search(str(value)) for key, value in row.items()
               if 'type' in key or 'class' in key)


def records(rows, old_rows, current_rows, runtime_ids, muscles):
    if len(runtime_ids) != len(set(runtime_ids)) or any(type(b) is not int for b in runtime_ids):
        raise ValueError('unique exact runtime body IDs required')
    dense = {body: index for index, body in enumerate(runtime_ids)}
    old, current = {}, {}
    for row in old_rows:
        old.setdefault(reference_id(row['malecns_09_id']), []).append(row)
    for row in current_rows:
        current.setdefault(row['bodyId'], []).append(row)
    scoped = sorted((r for r in rows if selected(r)), key=lambda r: r['banc_888_id'])
    ids = [r['banc_888_id'] for r in scoped]
    if any(reference_id(b) is None for b in ids) or len(ids) != len(set(ids)):
        raise ValueError('unique exact string BANC IDs required')
    counts = Counter(reference_id(r.get('malecns_match')) for r in scoped)
    output = []
    for row in scoped:
        body = reference_id(row.get('malecns_match'))
        previous = old.get(body, []) if body is not None else []
        present = current.get(body, []) if body is not None else []
        original = present[0] if len(present) == 1 else None
        prior = previous[0] if len(previous) == 1 else None
        segment = row.get('neuromere')
        side = row.get('side')
        expected = SEGMENTS.get(segment)
        soma_side = (original['somaSide'] if original and original['somaSide'] in ('L', 'R')
                     else original.get('rootSide') if original else None)
        aliases = [dict(m) for m in muscles if body in dense and dense[body] in m['idx']]
        flags = []
        if body is None:
            flags.append('MISSING_OR_NONSCALAR_MALECNS_REFERENCE')
        else:
            if counts[body] > 1: flags.append('MANY_BANC_ROWS_SHARE_REFERENCE')
            if len(previous) != 1: flags.append('V09_IDENTITY_MISSING_OR_DUPLICATE')
            if len(present) != 1: flags.append('V10_IDENTITY_MISSING_OR_DUPLICATE')
            if body not in dense: flags.append('NOT_IN_RUNTIME')
        if original:
            if side not in ('left', 'right') or soma_side != {'left': 'L', 'right': 'R'}.get(side):
                flags.append('SIDE_DISAGREEMENT_OR_MISSING')
            if (expected is None or original['somaNeuromere'] != segment
                    or original['subclass'] != expected[0] or original['exitNerve'] != expected[2]
                    or row.get('cell_sub_class') != expected[1]):
                flags.append('SEGMENT_CLASS_OR_NERVE_DISAGREEMENT')
            if original['superclass'] != 'vnc_motor': flags.append('NOT_CURRENT_MOTOR_ANNOTATION')
            if prior and prior.get('cell_type') != original['type']:
                flags.append('V09_V10_TYPE_DISAGREEMENT')
            if prior and (prior.get('side') != side or expected is None
                          or prior.get('nerve') != f'{side}_{expected[3]}_leg_nerve'):
                flags.append('V09_SIDE_OR_NERVE_DISAGREEMENT')
            current_type = str(original['type'])
            if not SCOPE.search(current_type): flags.append('CURRENT_TYPE_HAS_NO_TARSUS_ACTION_LABEL')
            elif (('levator' in str(row.get('cell_type')) and 'depressor' in current_type)
                  or ('depressor' in str(row.get('cell_type')) and 'levator' in current_type)):
                flags.append('ACTION_LABEL_DISAGREEMENT')
            recorded_manc = original.get('mancBodyid')
            banc_manc = reference_id(row.get('manc_match'))
            if recorded_manc is not None and banc_manc is not None and recorded_manc != banc_manc:
                flags.append('MANC_MATCH_CYCLE_DISAGREEMENT')
            if aliases: flags.append('EXISTING_ACTUATOR_ANNOTATIONS_RETAINED')
        if (row.get('flow') != 'efferent' or row.get('super_class') != 'motor'
                or row.get('cell_class') != 'leg_motor_neuron'):
            flags.append('BANC_NOT_LEG_MOTOR_ANNOTATION')
        if expected and row.get('nerve') != f'{side}_{expected[3]}_leg_nerve':
            flags.append('BANC_SIDE_OR_NERVE_DISAGREEMENT')
        if not str(row.get('cell_type')).startswith(('tarsus_levator', 'tarsus_depressor')):
            flags.append('EXTERNAL_LABEL_CONTROL_NOT_BANC_TARSUS_CLASS')
        if row.get('malecns_nblast_match') != row.get('malecns_match'):
            flags.append('NBLAST_REFERENCE_DIFFERS')
        output.append(dict(banc_original=row, malecns_reference_body_id=body,
            v09_original_rows=previous, v10_original_rows=present,
            runtime_dense_index=dense.get(body), existing_actuator_annotations=aliases,
            flags=sorted(flags), match_authority='UNVALIDATED_CROSS_DATASET_REFERENCE_LEAD',
            proposed_population=None, actuator_assignment=None, decoder_sign=None, gain=None,
            admission_ready=False))
    return output


def build():
    before = snapshot()
    for path, expected in LOCKS.items():
        if before[path] != expected: raise ValueError('pinned raw source mismatch: '+path)
    import pyarrow.feather as feather
    banc = feather.read_table(ROOT/(BASE+'banc_888_meta.feather'))
    old = feather.read_table(ROOT/(BASE+'malecns_09_meta.feather'))
    current = feather.read_table(ROOT/official.SOURCE)
    count, body_ids, *_ = decode_neurons(ROOT/'fly-brain-main/public/data/neurons.flyn')
    if count != len(body_ids): raise ValueError('runtime ID count mismatch')
    muscles = json.loads((ROOT/'fly-brain-main/public/data/bodymap.json').read_text())['muscles']
    result = records(banc.to_pylist(), old.to_pylist(), current.to_pylist(), list(body_ids), muscles)
    now = static.load()
    if snapshot() != before: raise ValueError('reference inputs changed during extraction')
    return json_safe(dict(schema=SCHEMA, status='REFERENCE_LEADS_RECORDED_ADMISSION_BLOCKED',
        source_hashes=before, source_rows=dict(banc=banc.num_rows, malecns_v09=old.num_rows,
                                             malecns_v10=current.num_rows),
        source_schemas={name: [dict(name=f.name, type=str(f.type)) for f in table.schema]
                        for name, table in [('banc', banc), ('malecns_v09', old), ('malecns_v10', current)]},
        records=result, scoped_rows=len(result),
        flag_counts=dict(sorted(Counter(f for r in result for f in r['flags']).items())),
        current_motor_count=sum(r['neural_motor_admission'] for r in now['static_admission_table']),
        new_admissions=0, scientific_transitions=0,
        current_three_original_raw_locks=now['original_raw_freezes_satisfied'],
        limitation='ID correspondence and retained annotations do not establish homologous function or a complete actuator population; no confidence inferred from ID-valued match fields.'))


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    now = build()
    recorded_raw = saved.get('current_three_original_raw_locks')
    if type(recorded_raw) is not bool or saved != dict(now, current_three_original_raw_locks=recorded_raw):
        raise ValueError('saved distal reference differs from complete reconstruction')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path)
    mode.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        try:
            report = build()
            serialized = json.dumps(report, indent=2, allow_nan=False)+'\n'
        except Exception as exc:
            (args.output_dir/'error.json').write_text(json.dumps(dict(status='EXTRACTION_FAILED',
                error=str(exc), new_admissions=0, scientific_transitions=0), indent=2)+'\n')
            raise
        with (args.output_dir/'reference.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(serialized)
    else:
        _, report = verify(args.report)
    print(f"DISTAL REFERENCE VERIFIED: {report['scoped_rows']} source rows; current {report['current_motor_count']}/42; admissions0; CNS/physics0.")
    print('Cross-dataset reference leads only; anatomy, complete membership and action mapping remain unresolved.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
