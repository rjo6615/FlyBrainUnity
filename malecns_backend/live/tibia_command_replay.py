"""Verify and review saved tibia-group, full closed-loop and full-yoke poses."""
import argparse
import gc
import json
from pathlib import Path

from . import tibia_command_dissection as study
from .tactile_motor_yoke_replay import replay_clips
from .tactile_recovery_replay import pose_only

DESCRIPTIONS=dict(T_C='Unpushed control; six tibia commands from undisturbed recording.',
    T_P='Only six tibia commands from undisturbed recording; other 14 motors closed-loop.',
    ON_P='Original closed-loop commands for all 20 motors.',
    Y_P='All motor commands from undisturbed recording.')


def load_verified(path):
    path=Path(path)
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest['protocol']!=study.PROTOCOL or set(manifest['artifacts'])!=set(study.CONDITIONS):
        raise ValueError('recognized complete tibia dissection required')
    if any(r['path']!=f'{i}.json.gz' for i,r in manifest['artifacts'].items()):
        raise ValueError('unexpected fresh artifact path')
    baseline,info=study.prerequisite()
    if info!=manifest['prerequisite']: raise ValueError('upstream evidence mismatch')
    evaluation=study.analyze(path.parent,manifest,baseline)
    if evaluation!=manifest['evaluation'] or not evaluation['integrity_passed']:
        raise ValueError('saved tibia evidence or evaluation failed')
    del baseline
    gc.collect()
    clips={}
    specs=[(i,path.parent/manifest['artifacts'][i]['path'],manifest['artifacts'][i]) for i in study.CONDITIONS]
    for identity,folder in (('ON_P','tactile-recovery-v1'),('Y_P','tactile-motor-yoke-v1')):
        old_dir=study.ROOT/'docs/evidence'/folder
        old=json.loads((old_dir/'manifest.json').read_text())
        specs.append((identity,old_dir/f'{identity}.json.gz',old['artifacts'][identity]))
    for identity,raw_path,reference in specs:
        arm,hashes=study.recovery.read_gzip(raw_path)
        if any(hashes[k]!=reference[k] for k in hashes): raise ValueError('measured clip hash mismatch')
        clips[identity]=pose_only(arm)['samples']
        del arm
        gc.collect()
    return manifest,clips


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--condition',choices=('BOTH','ALL',*DESCRIPTIONS),default='BOTH')
    parser.add_argument('--speed',type=float,default=.1)
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args(argv)
    if not 0<args.speed<=1: parser.error('--speed must be in (0,1]')
    print('Verifying saved archives and complete analyses; no CNS initialization.',flush=True)
    manifest,clips=load_verified(args.manifest)
    primary={k:v for k,v in manifest['evaluation']['primary'].items() if k!='inherited_m11_metric_labels'}
    print(json.dumps(primary,indent=2),flush=True)
    identities=('T_P','ON_P') if args.condition=='BOTH' else tuple(DESCRIPTIONS) if args.condition=='ALL' else (args.condition,)
    try: replay_clips(clips,identities,DESCRIPTIONS,speed=args.speed,loop=not args.once)
    except KeyboardInterrupt: pass
    return 0


if __name__=='__main__':
    raise SystemExit(main())
