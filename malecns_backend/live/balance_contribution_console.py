"""Native-safe concise console for the unchanged balance V1.1 execution core."""
import argparse
import json
from pathlib import Path

from . import balance_contribution_process as experiment


def summary(report):
    evaluation = report['evaluation']
    behavior = evaluation.get('behavior') or {}
    return experiment.base.native(dict(status=report.get('run_status'), integrity=evaluation['status'],
        accepted=evaluation['accepted'], unity_replay_eligible=evaluation['unity_replay_eligible'],
        checks=evaluation.get('checks', {}), reason=evaluation.get('reason'),
        behavior={k: behavior[k] for k in ('primary_label', 'posture', 'responses', 'interpretation_limits',
                                         'independent_balance_proven', 'gait_proven') if k in behavior}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--evaluate', type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    if args.evaluate:
        if args.live:
            parser.error('--evaluate cannot execute a live assay')
        report = json.loads((args.evaluate/'report.json').read_text(encoding='utf-8'))
        report['evaluation'] = experiment.evaluate(report, args.evaluate)
    else:
        report = experiment.execute(args.output, live=args.live)
    print(json.dumps(summary(report), allow_nan=False, indent=2))
    if args.evaluate or args.live:
        return 0 if report['evaluation']['accepted'] else 1
    return 0 if report['preflight']['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
