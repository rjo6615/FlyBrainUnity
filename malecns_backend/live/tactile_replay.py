"""Replay one recorded tactile arm through the existing output-only Unity stream."""
import argparse
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import time

from . import matched_tactile_delivery as experiment
from .server import PoseServer


def replay_snapshot(sample, index):
    return SimpleNamespace(time_ms=sample['time_s']*1000., root_position_xyz=tuple(sample['qpos'][:3]),
        root_quaternion_wxyz=tuple(sample['qpos'][3:7]), joint_positions=tuple(sample['joint_positions']),
        diagnostics=dict(physics_transition=index, neural_transition_count=index//5, finite=True))


def replay(report, condition, *, speed=.1, loop=True, server_factory=PoseServer, clock=time.monotonic, sleep=time.sleep):
    if not 0 < speed <= 1:
        raise ValueError('replay speed must be in (0, 1]')
    if report.get('protocol') != experiment.PROTOCOL:
        raise ValueError('unrecognized recorded experiment protocol')
    if not report.get('evaluation', {}).get('integrity_passed'):
        raise ValueError('review inconclusive evidence offline; Unity replay requires verified pair integrity')
    arm = report['arms'][condition]
    if arm['run_status'] != 'COMPLETE' or len(arm['samples']) != experiment.PROTOCOL['physics_steps'] + 1:
        raise ValueError('complete recorded arm required')
    print(f'RECORDED {condition}, {speed:g}x playback. No CNS or physics is running.', flush=True)
    print(json.dumps(report['evaluation']['milestones'], indent=2), flush=True)
    with server_factory() as server:
        while True:
            start = clock()
            for index, sample in enumerate(arm['samples']):
                due = start + sample['time_s'] / speed
                wait = due - clock()
                if wait > 0:
                    sleep(wait)
                # Downsampling affects display only; recorded states remain intact.
                server.publish(replay_snapshot(sample, index), now=clock())
            if not loop:
                break
            sleep(1.)
            print(f'RECORDED {condition}: replaying the same saved trajectory.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--condition', choices=experiment.CONDITIONS, required=True)
    parser.add_argument('--speed', type=float, default=.1)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args(argv)
    if not 0 < args.speed <= 1:
        parser.error('--speed must be in (0, 1]')
    report = json.loads(gzip.decompress(args.input.read_bytes()))
    # Verify the full saved pair before displaying a result as verified.
    if report.get('evaluation') != experiment.evaluate(report):
        raise ValueError('recorded evaluation disagrees with raw evidence')
    try:
        replay(report, args.condition, speed=args.speed, loop=not args.once)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
