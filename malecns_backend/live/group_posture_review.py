"""Verify saved posture analysis and print its roadmap snapshot; never run CNS."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from . import group_posture_analysis as analysis


def digest_stream(path,compressed=False):
    opener=gzip.open if compressed else open
    with opener(path,'rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def verify(path,progress=print):
    path=Path(path)
    report=json.loads(path.read_text(encoding='utf-8'))
    if (report['protocol']!=analysis.PROTOCOL or report['run_status']!='COMPLETE'
            or report['scientific_transitions']!=0 or not report['source_integrity']
            or report['sources_before']!=report['sources_after'] or report['sources_after']!=analysis.sources()):
        raise ValueError('complete recognized analysis with intact sources required')
    names={'aligned-traces.npz','posture.png','interaction.png'}
    if set(report['artifacts'])!=names: raise ValueError('all declared outputs required')
    for name in names:
        if report['artifacts'][name]!=analysis.file_record(path.parent/name):
            raise ValueError('saved analysis output hash mismatch')
    traces=analysis.read_npz(path.parent/'aligned-traces.npz')
    evaluation,_,_=analysis.analyze(traces,report['expected_frozen_responses'])
    if evaluation!=report['evaluation'] or not evaluation['integrity_passed']:
        raise ValueError('aligned analysis did not reproduce saved evaluation')
    if set(report['references'])!=set(traces): raise ValueError('all eight original references required')
    for identity,reference in report['references'].items():
        if identity=='ON_C':
            if reference['path']!='docs/evidence/matched-tactile-v1.json.gz' or reference['arm']!='ENABLED':
                raise ValueError('wrong archived baseline')
            checkpoint=json.loads((analysis.ROOT/'docs/evidence/matched-tactile-checkpoint.json').read_text())
            if any(checkpoint[k]!=reference[k] for k in ('gzip_sha256','raw_json_sha256')):
                raise ValueError('baseline checkpoint mismatch')
        else:
            policy=identity if identity in analysis.POLICIES else next(p for p,c in analysis.CONTROLS.items() if c==identity)
            folder=analysis.FOLDERS[policy]
            manifest_path=f'docs/evidence/{folder}/manifest.json'
            expected_path=f'docs/evidence/{folder}/{identity}.json.gz'
            if reference['manifest_path']!=manifest_path or reference['path']!=expected_path:
                raise ValueError('unexpected raw reference path')
            raw=(analysis.ROOT/manifest_path).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=reference['manifest_sha256']:
                raise ValueError('reference manifest changed')
            metadata=json.loads(raw)['artifacts'][identity]
            if any(metadata[k]!=reference[k] for k in ('gzip_sha256','raw_json_sha256','gzip_bytes','raw_json_bytes')):
                raise ValueError('reference metadata mismatch')
        raw_path=analysis.ROOT/reference['path']
        progress(f'Checking original compressed/raw hashes: {identity}.')
        if (raw_path.stat().st_size!=reference['gzip_bytes']
                or digest_stream(raw_path)!=reference['gzip_sha256']
                or digest_stream(raw_path,compressed=True)!=reference['raw_json_sha256']):
            raise ValueError('original frozen evidence hash mismatch')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(argv)
    report=verify(args.report,lambda message:print(message,flush=True))
    value=report['evaluation']
    print('VERIFIED saved analysis; no CNS/physics transitions.',flush=True)
    print('Motor admission: 20 / 42 coordinates. Remaining: 18 coxa + 4 middle/hind tarsus.',flush=True)
    print('Main finding: absolute posture and error from a moving control are different measures.',flush=True)
    for policy,summary in value['time_aligned'].items():
        print(f"{policy}: peak tilt {summary['absolute_tilt_peak']['value']:.3f} deg; "
              f"peak control-relative orientation {summary['relative_rotation_peak']['value']:.3f} deg.",flush=True)
    print(f"Root-vector interaction peak: {value['position_interaction']['peak_norm']['value']:.6f} model mm.",flush=True)
    for name in ('posture.png','interaction.png'): print(str(args.report.parent/name),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
