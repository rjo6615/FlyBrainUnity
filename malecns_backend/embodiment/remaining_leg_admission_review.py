"""Recheck the saved 22-coordinate audit; no motor admission or simulation."""
import argparse
import json
from pathlib import Path

from . import remaining_leg_admission_audit as audit


def verify(path):
    saved=json.loads(Path(path).read_text(encoding='utf-8'))
    if (saved.get('schema')!=audit.SCHEMA or saved.get('audit_integrity_passed') is not True
            or saved.get('new_admissions')!=0 or saved.get('scientific_transitions')!=0):
        raise ValueError('complete recognized non-admitting audit required')
    now=audit.build()
    if not now['audit_integrity_passed']: raise ValueError('current source/evidence changed during audit')
    for key in ('current_motor_count','model_coordinates','remaining_count','counts','rows','lf_reference'):
        if now[key]!=saved[key]: raise ValueError('saved evidence matrix mismatch: '+key)
    for key in ('source_hashes_before','source_hashes_after'):
        if set(now[key])!=set(saved[key]) or any(now[key][p]['canonical_content_sha256']!=saved[key][p]['canonical_content_sha256'] for p in now[key]):
            raise ValueError('canonical source/evidence content mismatch')
    return saved,now


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(argv)
    saved,now=verify(args.report)
    print('AUDIT VERIFIED: current 20/42; remaining 22; newly admitted 0; CNS/physics transitions 0.')
    print(json.dumps(now['counts'],indent=2))
    print('Original raw-freeze checks at recorded audit:',saved['all_original_raw_freezes_satisfied'])
    print('Original raw-freeze checks in current checkout:',now['all_original_raw_freezes_satisfied'])
    print('Canonical Git-content correspondence does not turn a failed original raw prerequisite into a pass.')
    print('Next: reference-backed LF proximal population activation/sign and multi-axis binding prerequisites.')
    return 0


if __name__=='__main__': raise SystemExit(main())
