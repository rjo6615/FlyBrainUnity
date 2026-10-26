"""Read-only original loader source-graph prerequisite, without loading a CNS.

Complements the historical seven-artifact preflight. It does not alter the
executed live runner and cannot execute/retry a scientific campaign.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DESIGN = 'docs/evidence/balance-contribution-v1/protocol.json'
DESIGN_SHA256 = '2ea0a8b94476cdc4a1c7040dfa3d5a40048e4242491ec42bb4af3761be998a20'
GRAPH = 'fly-brain-main/public/data/graph_w3.bin'


def stream_identity(stream):
    digest, size = hashlib.sha256(), 0
    while True:
        block = stream.read(1024*1024)
        if not block:
            return dict(sha256=digest.hexdigest(), bytes=size)
        digest.update(block)
        size += len(block)


def original_graph_identity():
    raw = (ROOT/DESIGN).read_bytes()
    if hashlib.sha256(raw).hexdigest() != DESIGN_SHA256:
        raise ValueError('original scientific design identity changed')
    revision = json.loads(raw)['baseline']
    args = ['git', '-c', f'safe.directory={ROOT.as_posix()}', 'show', revision + ':' + GRAPH]
    with subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        identity = stream_identity(process.stdout)
        error = process.stderr.read().decode('utf-8', errors='replace')
        if process.wait() != 0:
            raise ValueError('original Git source graph unavailable: ' + error)
    # This original graph is a regular Git blob, not a working-copy hash chosen
    # after observing the failed run. It is streamed to avoid dumping binary data.
    return dict(identity, revision=revision, path=GRAPH, authority='original scientific baseline Git blob')


def check_graph(*, expected_reader=original_graph_identity, graph_path=None):
    path = Path(graph_path) if graph_path is not None else ROOT/GRAPH
    result = dict(verified=False, path=GRAPH)
    try:
        result['expected'] = expected_reader()
        with path.open('rb') as stream:
            result['observed'] = stream_identity(stream)
        result['verified'] = all(result['observed'][k] == result['expected'][k] for k in ('sha256','bytes'))
        if not result['verified']:
            result['error'] = 'original loader orientation source graph bytes differ'
    except (OSError, KeyError, ValueError) as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result


def check():
    # Read the original identity before invoking the historical preflight. No
    # graph decoder, CNS constructor, native initializer or live execute call.
    orientation = check_graph()
    from .balance_contribution import preflight
    original = preflight()
    return dict(schema='balance-loader-source-prerequisites-v1', orientation_source=orientation,
        original_preflight=original, verified=orientation['verified'] and original['verified'],
        scientific_transitions=0, native_constructions=0, cns_initializations=0,
        scientific_execution_authorized_by_this_check=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='exclusive JSON receipt; never overwrite')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('receipt already exists; use a fresh filename')
    report = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, allow_nan=False, indent=2)
        stream.write('\n')
    print(json.dumps(report, allow_nan=False))
    return 0 if report['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
