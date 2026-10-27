"""Integrity-gated replay of controlled-live V1.1 records; no native execution."""
import argparse
import gc
import json
from pathlib import Path

from . import controlled_live_balance_v1_1 as experiment
from . import balance_contribution_replay as playback


def load_verified(folder):
    folder = Path(folder)
    report = json.loads((folder/'report.json').read_text(encoding='utf-8'))
    evaluation = experiment.evaluate(report, folder)
    if (evaluation != report['evaluation'] or not evaluation['scientific']['accepted']
            or not evaluation['scientific']['unity_replay_eligible']):
        raise ValueError('complete reconstructed V1.1 scientific integrity required')
    clips = {}
    for condition in experiment.base.CONDITIONS:
        arm = experiment.original.read_arm(folder, condition, report['arm_artifacts'][condition])
        clips[condition] = playback.pose_only(arm)
        del arm
        gc.collect()
    return report, clips


def replay(report, clips, condition='PUSHED', **kwargs):
    if (report.get('schema') != experiment.SCHEMA
            or not report.get('evaluation', {}).get('scientific', {}).get('accepted')
            or not report['evaluation']['scientific'].get('unity_replay_eligible')):
        raise ValueError('accepted controlled-live V1.1 evidence required')
    print('RECORDED CONTROLLED-LIVE V1.1: saved poses; no physics/CNS experiment runs.', flush=True)
    print('Original LIVE observation status (separate from this replay): ' +
          json.dumps(report['evaluation'].get('display', {})), flush=True)
    # Reuse only the validated presentation API's flat scientific summary.
    # The original V1 evaluator is NEVER given a fabricated report. The complete
    # new-schema report was verified above by the V1.1 evaluator.
    return playback.replay(dict(evaluation=report['evaluation']['scientific']), clips, condition, **kwargs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--condition', choices=(*experiment.base.CONDITIONS,'ALL','PUSHED'), default='PUSHED')
    parser.add_argument('--speed', type=float, default=.1)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    print('Verifying complete V1.1 saved evidence; no native/CNS initialization.', flush=True)
    report, clips = load_verified(args.input)
    try:
        replay(report, clips, args.condition, speed=args.speed, loop=not args.once)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
