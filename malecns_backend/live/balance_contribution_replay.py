"""Integrity-gated saved balance poses through the existing Unity pose transport."""
import argparse
from array import array
import gc
import json
import math
from pathlib import Path
import time

from . import balance_contribution_process as experiment
from .protocol import JOINT_NAMES
from .server import PoseServer
from .tactile_replay import replay_snapshot


def pose_only(arm):
    """Read actual recorded scalar qpos addresses, never infer them from names."""
    if arm['run_status'] != 'COMPLETE' or len(arm['samples']) != 20001:
        raise ValueError('complete fixed-window raw arm required')
    context = arm['context']
    if context['free_root']['qpos_address'] != 0 or context['free_root']['dof_address'] != 0:
        raise ValueError('verified native free-root addresses required')
    rows = context['native_inventory']['rows']
    if (len(rows) != 42 or [r['coordinate'] for r in rows] != list(JOINT_NAMES)
            or [r['action_index'] for r in rows] != list(range(42))):
        raise ValueError('exact actual-model 42-coordinate action order required')
    addresses = []
    nq = context['native_inventory']['nq']
    for row in rows:
        start, stop = row['qpos_range']
        if type(start) is not int or type(stop) is not int or stop != start + 1 or not 7 <= start < nq:
            raise ValueError('exact scalar native qpos address required')
        addresses.append(start)
    if len(set(addresses)) != 42:
        raise ValueError('overlapping native joint addresses')
    result = []
    for index, sample in enumerate(arm['samples']):
        qpos = sample['qpos']
        if (len(qpos) != nq or not all(math.isfinite(v) for v in qpos)
                or not math.isfinite(sample['time_s']) or abs(sample['time_s'] - index*.0001) > 1e-10
                or sum(v*v for v in qpos[3:7]) <= 0):
            raise ValueError('finite complete native pose/clock required')
        result.append(dict(time_s=sample['time_s'], qpos=array('d', qpos[:7]),
                           joint_positions=array('d', (qpos[a] for a in addresses))))
    return result


def load_verified(folder):
    folder = Path(folder)
    report = json.loads((folder/'report.json').read_text(encoding='utf-8'))
    evaluation = experiment.evaluate(report, folder)
    if evaluation != report['evaluation'] or not evaluation['accepted'] or not evaluation['unity_replay_eligible']:
        raise ValueError('complete reconstructed four-arm integrity required; unavailable/failed behavior alone is not an integrity failure')
    clips = {}
    for c in experiment.base.CONDITIONS:
        arm = experiment.read_arm(folder, c, report['arm_artifacts'][c])
        clips[c] = pose_only(arm)
        del arm
        gc.collect()
    return report, clips


def selected(condition):
    if condition == 'ALL': return experiment.base.CONDITIONS
    if condition == 'PUSHED': return ('NP', 'WP')
    if condition not in experiment.base.CONDITIONS: raise ValueError('unknown recorded arm')
    return (condition,)


def replay(report, clips, condition='PUSHED', *, speed=.1, loop=True,
           server_factory=PoseServer, clock=time.monotonic, sleep=time.sleep):
    if not report.get('evaluation', {}).get('accepted') or not report['evaluation'].get('unity_replay_eligible'):
        raise ValueError('integrity-gated saved evidence required')
    if not math.isfinite(speed) or not 0 < speed <= 1:
        raise ValueError('display speed must be in (0,1]')
    conditions = selected(condition)
    if any(c not in clips or len(clips[c]) != 20001 for c in conditions):
        raise ValueError('complete selected saved clips required')
    print('RECORDED BALANCE CONTRIBUTION V1.1: no physics/CNS is running.', flush=True)
    print('Same position assistance; tactile OFF; descriptive contribution assay, not independent balance/gait.', flush=True)
    behavior = report['evaluation']['behavior']
    print(json.dumps({k: behavior[k] for k in ('primary_label', 'posture', 'responses', 'interpretation_limits',
                     'independent_balance_proven', 'gait_proven') if k in behavior}, separators=(',', ':')), flush=True)
    with server_factory() as server:
        while True:
            for c in conditions:
                print(f'REPLAY RESET -> {c}: saved t=0; this is not a simulated jump.', flush=True)
                print(f'{c}: ' + ('decoder input withdrawn before safety from500.5ms.' if c.startswith('W')
                                  else 'decoder input continues throughout.'), flush=True)
                start = clock()
                for index, sample in enumerate(clips[c]):
                    delay = start + sample['time_s']/speed - clock()
                    if delay > 0: sleep(delay)
                    if c.endswith('P') and index == 5000:
                        print(f'{c}: recorded thorax pulse starts at500ms.', flush=True)
                    if c.endswith('P') and index == 5200:
                        print(f'{c}: recorded thorax pulse ends at520ms.', flush=True)
                    server.publish(replay_snapshot(sample, index), now=clock())
                if loop or c != conditions[-1]: sleep(1.)
            if not loop: break


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--condition', choices=(*experiment.base.CONDITIONS, 'ALL', 'PUSHED'), default='PUSHED')
    parser.add_argument('--speed', type=float, default=.1)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    print('Validating complete saved four-arm evidence; no physics/CNS initialization.', flush=True)
    report, clips = load_verified(args.input)
    try:
        replay(report, clips, args.condition, speed=args.speed, loop=not args.once)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
