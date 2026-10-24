"""Review measured motor-yoked and original closed-loop push clips."""
import argparse
import gc
import json
from pathlib import Path
import time

from . import tactile_motor_yoke as experiment
from .tactile_recovery_replay import pose_only
from .tactile_replay import replay_snapshot
from .server import PoseServer


def load_verified(path):
    path=Path(path)
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest['protocol']!=experiment.PROTOCOL or set(manifest['artifacts'])!=set(experiment.CONDITIONS):
        raise ValueError('recognized complete motor-yoke manifest required')
    if any(r['path']!=f'{i}.json.gz' for i,r in manifest['artifacts'].items()):
        raise ValueError('unexpected arm path')
    baseline,info=experiment.prerequisite()
    if info!=manifest['prerequisite']:
        raise ValueError('upstream evidence mismatch')
    result=experiment.analyze(path.parent,manifest,baseline,info['closed_loop_response'])
    if result!=manifest['evaluation'] or not result['integrity_passed']:
        raise ValueError('motor-yoke evidence or saved evaluation failed')
    del baseline
    gc.collect()
    clips={}
    old_manifest=json.loads((experiment.ROOT/info['recovery_manifest_path']).read_text())
    old_path=experiment.ROOT/'docs/evidence/tactile-recovery-v1/ON_P.json.gz'
    arm,hashes=experiment.prior.read_gzip(old_path)
    if any(hashes[k]!=old_manifest['artifacts']['ON_P'][k] for k in hashes):
        raise ValueError('original closed-loop clip hash mismatch')
    clips['ON_P']=pose_only(arm)['samples']
    del arm
    gc.collect()
    for identity in experiment.CONDITIONS:
        arm,hashes=experiment.prior.read_gzip(path.parent/manifest['artifacts'][identity]['path'])
        if any(hashes[k]!=manifest['artifacts'][identity][k] for k in hashes):
            raise ValueError('yoked clip hash mismatch')
        clips[identity]=pose_only(arm)['samples']
        del arm
        gc.collect()
    return manifest,clips


def replay(clips,condition='BOTH',*,speed=.1,loop=True,server_factory=PoseServer,clock=time.monotonic,sleep=time.sleep):
    if condition not in ('BOTH','Y_C','Y_P','ON_P'): raise ValueError('unknown clip')
    identities=('Y_P','ON_P') if condition=='BOTH' else (condition,)
    descriptions={i:('Undisturbed recorded motor commands applied.' if i.startswith('Y')
                    else 'Original closed-loop motor commands applied.') for i in identities}
    return replay_clips(clips,identities,descriptions,speed=speed,loop=loop,
                        server_factory=server_factory,clock=clock,sleep=sleep)


def replay_clips(clips,identities,descriptions,*,speed=.1,loop=True,server_factory=PoseServer,clock=time.monotonic,sleep=time.sleep):
    if not 0<speed<=1: raise ValueError('speed must be in (0,1]')
    if not identities or any(i not in clips or i not in descriptions for i in identities):
        raise ValueError('measured clip and explicit description required for every identity')
    print('RECORDED motor-application control; no CNS or physics is running.',flush=True)
    with server_factory() as server:
        while True:
            for identity in identities:
                print(f'REPLAY RESET -> {identity}: saved t=0, NOT a physical jump.',flush=True)
                print('Tactile enabled. '+descriptions[identity],flush=True)
                start=clock()
                for index,sample in enumerate(clips[identity]):
                    delay=start+sample['time_s']/speed-clock()
                    if delay>0: sleep(delay)
                    if identity.endswith('_P') and index==experiment.prior.START:
                        print(f'{identity}: recorded thorax pulse begins at 500 ms.',flush=True)
                    if identity.endswith('_P') and index==experiment.prior.STOP:
                        print(f'{identity}: recorded thorax pulse ends at 520 ms.',flush=True)
                    server.publish(replay_snapshot(sample,index),now=clock())
                if loop or identity!=identities[-1]: sleep(1.)
            if not loop: break


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--condition',choices=('BOTH','Y_C','Y_P','ON_P'),default='BOTH')
    parser.add_argument('--speed',type=float,default=.1)
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args(argv)
    if not 0<args.speed<=1: parser.error('--speed must be in (0,1]')
    print('Verifying complete saved evidence and analysis; no CNS initialization.',flush=True)
    manifest,clips=load_verified(args.manifest)
    print(json.dumps(manifest['evaluation']['contrast'],indent=2),flush=True)
    try: replay(clips,args.condition,speed=args.speed,loop=not args.once)
    except KeyboardInterrupt: pass
    return 0


if __name__=='__main__':
    raise SystemExit(main())
