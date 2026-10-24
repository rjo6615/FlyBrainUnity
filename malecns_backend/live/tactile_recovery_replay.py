"""Clearly labelled recorded disturbance clips for the existing Unity LiveFly scene."""
import argparse
import gc
import json
from pathlib import Path
import time

from . import tactile_recovery as recovery
from .tactile_replay import replay_snapshot
from .server import PoseServer


def pose_only(arm):
    return dict(samples=[dict(time_s=s['time_s'],qpos=s['qpos'][:7],joint_positions=s['joint_positions'])
                         for s in arm['samples']])


def load_verified(manifest_path):
    path=Path(manifest_path)
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('protocol')!=recovery.PROTOCOL or set(manifest.get('artifacts',{}))!=set(recovery.FRESH):
        raise ValueError('complete recognized recovery manifest required')
    reference=manifest['prerequisite']['baseline']
    if reference['path']!='docs/evidence/matched-tactile-v1.json.gz' or reference['arm']!='ENABLED':
        raise ValueError('unexpected archived no-push control')
    for identity,record in manifest['artifacts'].items():
        if record['path']!=f'{identity}.json.gz':
            raise ValueError('unexpected fresh artifact path')
    pair,hashes=recovery.read_gzip(recovery.ROOT/reference['path'])
    if any(hashes[k]!=reference[k] for k in hashes):
        raise ValueError('archived control hash mismatch')
    baseline=pair['arms']['ENABLED']
    del pair
    gc.collect()
    evaluation=recovery.analyze(path.parent,manifest,baseline)
    if evaluation!=manifest['evaluation'] or not evaluation['integrity_passed']:
        raise ValueError('raw recovery evidence or saved integrity evaluation failed')
    return manifest,pose_only(baseline)


def selected_conditions(condition):
    if condition=='PUSHED': return ('OFF_P','ON_P')
    if condition=='ALL': return recovery.CONDITIONS
    if condition not in recovery.CONDITIONS: raise ValueError('unknown recorded condition')
    return (condition,)


def replay(manifest_path,manifest,baseline,condition,*,speed=.1,loop=True,
           server_factory=PoseServer,clock=time.monotonic,sleep=time.sleep):
    if not 0<speed<=1:
        raise ValueError('replay speed must be in (0,1]')
    if not manifest.get('evaluation',{}).get('integrity_passed'):
        raise ValueError('verified recorded experiment required')
    conditions=selected_conditions(condition)
    print('RECORDED recovery review: no CNS or physics is running.',flush=True)
    print(json.dumps(manifest['evaluation']['contrast'],indent=2),flush=True)
    cached={'ON_C':baseline['samples']}
    with server_factory() as server:
        while True:
            for identity in conditions:
                if identity not in cached:
                    arm=recovery.read_gzip(Path(manifest_path).parent/manifest['artifacts'][identity]['path'])[0]
                    cached[identity]=pose_only(arm)['samples']
                    del arm
                    gc.collect()
                print(f'REPLAY RESET -> {identity}: returning to saved t=0; this is NOT a simulated jump.',flush=True)
                print('Tactile is enabled until 500.0 ms; '+
                      ('then withheld from 500.5 ms.' if identity.startswith('OFF') else 'continues throughout.'),flush=True)
                start=clock()
                for index,sample in enumerate(cached[identity]):
                    wait=start+sample['time_s']/speed-clock()
                    if wait>0: sleep(wait)
                    if identity.endswith('_P') and index==recovery.START:
                        print(f'{identity}: recorded force pulse begins at 500 ms.',flush=True)
                    if identity.startswith('OFF') and index==(recovery.WITHDRAW_INDEX+1)*5:
                        print(f'{identity}: recorded tactile delivery is now withheld.',flush=True)
                    if identity.endswith('_P') and index==recovery.STOP:
                        print(f'{identity}: recorded force pulse ends at 520 ms.',flush=True)
                    server.publish(replay_snapshot(sample,index),now=clock())
                if loop or identity!=conditions[-1]: sleep(1.)
            if not loop: break


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--condition',choices=(*recovery.CONDITIONS,'PUSHED','ALL'),default='PUSHED')
    parser.add_argument('--speed',type=float,default=.1)
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args(argv)
    if not 0<args.speed<=1: parser.error('--speed must be in (0,1]')
    print('Validating saved control, full traces and recovery analysis; no CNS initialization.',flush=True)
    manifest,baseline=load_verified(args.manifest)
    try:
        replay(args.manifest,manifest,baseline,args.condition,speed=args.speed,loop=not args.once)
    except KeyboardInterrupt:
        pass
    return 0


if __name__=='__main__':
    raise SystemExit(main())
