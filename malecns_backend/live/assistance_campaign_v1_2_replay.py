"""Integrity-gated Unity replay of saved V1.2 assistance-campaign poses; no native execution."""
import argparse
import gc
import json
import math
from pathlib import Path
import time

from ..embodiment.distal_tarsus_reference import json_safe
from . import assistance_campaign_v1_2 as experiment
from . import balance_contribution_replay as playback
from .server import PoseServer
from .tactile_replay import replay_snapshot

ARM_IDS = experiment.ARM_IDS
DEFAULT_ARMS = ('A_NP', 'R_NP')
STATES = 20001


def saved_form(value):
    """The exact form the campaign's existing save wrote (json_safe markers, no NaN literals)."""
    return json.loads(json.dumps(json_safe(experiment.base.native(value)), allow_nan=False))


def load_verified(folder, *, evaluate=None, reader=None, project=None):
    """Re-run the unchanged V1.2 evaluator once, projecting poses from the arms it reads.

    Clips are returned only if the reconstructed evaluation equals the saved
    report exactly and scientific integrity was accepted; otherwise nothing is shown.
    """
    evaluate = evaluate or experiment.evaluate
    reader = reader or experiment.read_arm
    project = project or playback.pose_only
    folder = Path(folder)
    report = json.loads((folder/'report.json').read_text(encoding='utf-8'))
    if report.get('schema') != experiment.SCHEMA:
        raise ValueError('V1.2 assistance-campaign report required')
    clips = {}

    def loader(f, arm_id, artifact):
        arm = reader(f, arm_id, artifact)
        clips[arm_id] = project(arm)
        return arm

    evaluation = evaluate(report, folder, loader=loader)
    scientific = evaluation.get('scientific', {})
    if (saved_form(evaluation) != report['evaluation'] or not scientific.get('accepted')
            or not scientific.get('unity_replay_eligible') or list(clips) != list(ARM_IDS)):
        clips.clear()
        gc.collect()
        raise ValueError('complete reconstructed V1.2 eight-arm scientific integrity required')
    return report, clips


def selected(arms):
    chosen = tuple(ARM_IDS) if arms == 'ALL' else tuple(a.strip() for a in arms.split(','))
    if not chosen or len(set(chosen)) != len(chosen) or any(a not in ARM_IDS for a in chosen):
        raise ValueError('choose distinct recorded arms from ' + ','.join(ARM_IDS))
    return chosen


def describe(arm_id):
    level, condition = arm_id.split('_')
    yield (f'{arm_id}: 22 baseline-only servos neutralized after recorded state 5005 (500.5 ms).' if level == 'R'
           else f'{arm_id}: all 42 position servos keep the original assisted policy.')
    yield (f'{arm_id}: 20-channel decoder input withdrawn before safety from tick 1001 (500.5 ms).'
           if condition.startswith('W') else f'{arm_id}: 20-channel decoder input continues throughout.')
    if condition.endswith('P'):
        yield f'{arm_id}: recorded thorax push [0,1.024,0] at outgoing states 5000-5199 (500-520 ms).'


def replay(report, clips, arms=','.join(DEFAULT_ARMS), *, speed=.1, loop=True,
           server_factory=PoseServer, clock=time.monotonic, sleep=time.sleep):
    scientific = report.get('evaluation', {}).get('scientific', {})
    if (report.get('schema') != experiment.SCHEMA or not scientific.get('accepted')
            or not scientific.get('unity_replay_eligible')):
        raise ValueError('accepted V1.2 assistance-campaign evidence required')
    if not math.isfinite(speed) or not 0 < speed <= 1:
        raise ValueError('display speed must be in (0,1]')
    chosen = selected(arms)
    if any(a not in clips or len(clips[a]) != STATES for a in chosen):
        raise ValueError('complete selected saved clips required')
    print('RECORDED ASSISTANCE CAMPAIGN V1.2: saved poses; no physics/CNS is running.', flush=True)
    print('One seed, partial position assistance; not independent balance or gait.', flush=True)
    print('Original live display status (separate from this replay): visual_review='
          + str(report['evaluation'].get('visual_review')), flush=True)
    comparisons = scientific['behavior']['comparisons']
    for name, c in comparisons.items():
        if c['first'] in chosen and c['second'] in chosen:
            print(f"{name}: {c['tilt_label']} (mean {c['world_tilt_mean_first_minus_second_deg']:+.2f} deg)", flush=True)
    with server_factory() as server:
        while True:
            for arm_id in chosen:
                print(f'REPLAY RESET -> {arm_id}: saved t=0; this is not a simulated jump.', flush=True)
                for line in describe(arm_id):
                    print(line, flush=True)
                start = clock()
                for index, sample in enumerate(clips[arm_id]):
                    delay = start + sample['time_s']/speed - clock()
                    if delay > 0:
                        sleep(delay)
                    if index == 5006:
                        print(f'{arm_id}: state 5006, first state where the declared arm policies can differ.', flush=True)
                    server.publish(replay_snapshot(sample, index), now=clock())
                if loop or arm_id != chosen[-1]:
                    sleep(1.)
            if not loop:
                break


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--arms', default=','.join(DEFAULT_ARMS),
                        help='comma-separated arm IDs, or ALL (default A_NP,R_NP)')
    parser.add_argument('--speed', type=float, default=.1)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    selected(args.arms)
    print('Re-verifying complete V1.2 eight-arm evidence (slow: reads ~4.5 GB); no native/CNS initialization.',
          flush=True)
    report, clips = load_verified(args.input)
    try:
        replay(report, clips, args.arms, speed=args.speed, loop=not args.once)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
