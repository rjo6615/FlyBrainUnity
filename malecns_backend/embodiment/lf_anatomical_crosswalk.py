"""Verify exact LF identities against pinned official annotations; no admission."""
import argparse
import hashlib
import json
from pathlib import Path

from . import remaining_leg_admission_audit as audit
from . import remaining_leg_admission_review as admission

ROOT = audit.ROOT
DIRECTORY = 'docs/evidence/lf-anatomical-crosswalk-v1/'
SOURCE = DIRECTORY+'annotations.feather'
SOURCE_SHA = '2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2'
UPSTREAM = 'docs/evidence/remaining-leg-admission-audit-v1_1/audit.json'
SCHEMA = 'lf-anatomical-crosswalk-v1'
SOURCES = ('docs/LF_ANATOMICAL_CROSSWALK_V1.md',
           'malecns_backend/embodiment/lf_anatomical_crosswalk.py',
           'malecns_backend/embodiment/remaining_leg_admission_review.py',
           'fly-brain-main/scripts/prep_bodymap.py', UPSTREAM)
# Atlas sets are class-level references only, never a per-body-ID match.
ATLAS = {
    'Tergopleural/Pleural promotor MN': ('A2', [15, 16], [1, 2, 3, 4], 'DProN'),
    'Pleural remotor/abductor MN': ('A4', [18, 19], [12, 13], 'ProAN'),
    'Sternal adductor MN': ('A3', [17], [7], 'ProAN'),
    'Sternal anterior rotator MN': ('A3', [17], [5, 6], 'VProN'),
    'Sternal posterior rotator MN': ('A4', [18, 19], [8, 9, 10, 11], 'ProAN'),
}


def source_hashes():
    return {p: audit.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n')) for p in SOURCES}


def crosswalk(rows, identities):
    """Validate exhaustive source pools; retain absent matches and all original fields."""
    expected = {body: (p, dense) for p in identities
                for body, dense in zip(p['body_ids'], p['dense_indices'])}
    if len(identities) != 5 or len(expected) != 13:
        raise ValueError('five exact populations / thirteen unique neurons required')
    if {p['name'].removesuffix(' T1 left') for p in identities} != set(ATLAS):
        raise ValueError('unexpected candidate class inventory')
    selected = []
    for row in rows:
        side = row['somaSide'] if row['somaSide'] in ('L', 'R') else row['rootSide']
        if row['type'] in ATLAS and row['subclass'] == 'fl' and side == 'L':
            selected.append(row)
    if len(selected) != 13 or {r['bodyId'] for r in selected} != set(expected):
        raise ValueError('missing/extra/duplicate official LF class members')
    by_id = {r['bodyId']: r for r in selected}
    output = []
    for body, (identity, dense) in expected.items():
        row = by_id[body]
        typ = identity['name'].removesuffix(' T1 left')
        figure, pages, numbers, nerve = ATLAS[typ]
        if (type(body) is not int or row['type'] != typ or row['superclass'] != 'vnc_motor'
                or row['somaNeuromere'] != 'T1' or row['exitNerve'] != nerve):
            raise ValueError('exact annotation class/nerve/neuromere mismatch')
        match = row['mancBodyid']
        if match is not None and (not isinstance(match, (int, float)) or not 0 < match < 2**53 or int(match) != match):
            raise ValueError('non-integral MANC body match')
        output.append(dict(body_id=body, dense_index=dense, population=identity['name'],
            annotation_actuators=identity['annotation_actuators'], original_annotation=dict(row),
            recorded_manc_body_match=None if match is None else int(match),
            atlas_class_reference=dict(figure=figure, pdf_pages=pages, fanc_mn_set=numbers),
            individual_fanc_mn=None, model_tendon=None, decoder_vector=None, gain=None,
            admission_ready=False))
    return output


def build():
    before = source_hashes()
    raw = (ROOT/SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('official source raw hash mismatch; fetch the pinned LFS object')
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.feather as feather
    # Filter first in Arrow; retain complete selected records without building a brain.
    table = feather.read_table(pa.BufferReader(raw))
    relevant = table.filter(pc.is_in(table['type'], value_set=pa.array(list(ATLAS))))
    _, now = admission.verify(ROOT/UPSTREAM)
    records = crosswalk(relevant.to_pylist(), now['lf_reference']['candidate_identities'])
    if source_hashes() != before or (ROOT/SOURCE).read_bytes() != raw:
        raise ValueError('source changed during extraction')
    return dict(schema=SCHEMA, status='CLASS_REFERENCE_VERIFIED_TENDON_BINDING_UNRESOLVED',
        source_hashes=before, official_source=dict(path=SOURCE, sha256=SOURCE_SHA, size_bytes=len(raw),
            total_rows=table.num_rows, schema=[dict(name=f.name, type=str(f.type)) for f in table.schema],
            attribution='MaleCNS consortium; CC-BY; https://male-cns.janelia.org/download/'),
        neurons=records, recorded_manc_body_match_count=sum(r['recorded_manc_body_match'] is not None for r in records),
        unresolved_promotor_count=sum(r['original_annotation']['type']=='Tergopleural/Pleural promotor MN' for r in records),
        model_tendon_assignment_count=0, current_motor_count=20, model_coordinates=42,
        new_admissions=0, scientific_transitions=0,
        atlas_review=dict(url='https://faculty.washington.edu/tuthill/docs/azevedo24_appendix.pdf',
            sha256='822c298e50da9fee3ce75f1dabda040574eac9fc854fdf92837856a82c8515f6',
            review='Human text/visual inspection of page 1 and Figures A2-A4, PDF pages 15-19; not automated anatomical matching',
            limitation='Figure A2 explicitly leaves individual promotor targets uncertain; FANC is a separate specimen'),
        current_original_raw_freezes_satisfied=now['all_original_raw_freezes_satisfied'])


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    now = build()
    recorded_raw = saved.get('current_original_raw_freezes_satisfied')
    if type(recorded_raw) is not bool or saved != dict(now, current_original_raw_freezes_satisfied=recorded_raw):
        raise ValueError('saved official-source crosswalk mismatch')
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
            saved = now = build()
        except Exception as exc:
            failure = dict(schema=SCHEMA, status='INTEGRITY_ERROR', scientific_transitions=0,
                           new_admissions=0, error=f'{type(exc).__name__}: {exc}')
            (args.output_dir/'crosswalk.json').write_text(json.dumps(failure, indent=2)+'\n', encoding='utf-8')
            print(failure['error'])
            return 1
        with (args.output_dir/'crosswalk.json').open('x', encoding='utf-8') as stream:
            json.dump(saved, stream, indent=2, allow_nan=False)
            stream.write('\n')
    else:
        saved, now = verify(args.report)
    print(f"CROSSWALK VERIFIED: {len(now['neurons'])} exact neurons; {now['recorded_manc_body_match_count']} recorded MANC body matches.")
    print(f"Unresolved promotor neurons {now['unresolved_promotor_count']}; model tendon assignments 0; current 20/42.")
    print('Newly admitted 0; CNS/physics transitions 0. Atlas numbers are not MaleCNS body IDs.')
    print('Original raw-freeze checks: recorded', saved['current_original_raw_freezes_satisfied'],
          '/ current', now['current_original_raw_freezes_satisfied'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
