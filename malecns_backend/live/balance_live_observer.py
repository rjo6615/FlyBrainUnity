"""One-way provisional pose observation; scientific samples stay authoritative."""
from __future__ import annotations

import math
import time

from .protocol import JOINT_NAMES, decode, encode, pose
from .server import PoseServer
from .tactile_replay import replay_snapshot


class CheckedPoseServer(PoseServer):
    """Expose listener/thread failures without changing the existing wire loop."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serve_error = None

    def _serve(self):
        try:
            super()._serve()
        except Exception as exc:
            if not self._stop.is_set():
                self.serve_error = f'{type(exc).__name__}: {exc}'
        finally:
            if self._listener is not None:
                self._listener.close()
            self._ready.set()

    def check(self):
        if self.serve_error or self._thread is None or not self._thread.is_alive():
            raise RuntimeError(self.serve_error or 'pose network thread stopped')

    def start(self):
        try:
            super().start()
            self.check()
            return self
        except BaseException:
            self.close()
            raise


def sample_snapshot(context, sample, index):
    """Generalize the saved replay projection to one still-provisional state.

    The actual-model inventory is already validated by Trial.bind. Recheck the
    exact scalar address/order contract here; never infer qpos from action index.
    """
    if type(index) is not int or not 0 <= index <= 20000:
        raise ValueError('fixed scientific state index required')
    root, inventory = context['free_root'], context['native_inventory']
    if root['qpos_address'] != 0 or root['dof_address'] != 0:
        raise ValueError('actual native free-root addresses required')
    rows = inventory['rows']
    if (len(rows) != 42 or [r['coordinate'] for r in rows] != list(JOINT_NAMES)
            or [r['action_index'] for r in rows] != list(range(42))):
        raise ValueError('actual native 42-coordinate action order required')
    nq = inventory['nq']
    addresses = []
    for row in rows:
        a, b = row['qpos_range']
        if type(a) is not int or type(b) is not int or b != a + 1 or not 7 <= a < nq:
            raise ValueError('native scalar qpos address required')
        addresses.append(a)
    if len(set(addresses)) != 42:
        raise ValueError('overlapping native qpos addresses')
    qpos = sample['qpos']
    if (len(qpos) != nq or not all(math.isfinite(v) for v in qpos)
            or not math.isfinite(sample['time_s']) or abs(sample['time_s'] - index*.0001) > 1e-10
            or sum(v*v for v in qpos[3:7]) <= 0):
        raise ValueError('finite recorded native pose and exact state clock required')
    return replay_snapshot(dict(time_s=sample['time_s'], qpos=qpos,
        joint_positions=[qpos[a] for a in addresses]), index)


def packet_for(snapshot, session, sequence):
    # Same fields and conversion as the unchanged PoseServer.publish.
    return pose(session, sequence, snapshot.time_ms/1000., snapshot.root_position_xyz,
        snapshot.root_quaternion_wxyz, snapshot.joint_positions,
        physics_transitions=int(snapshot.diagnostics['physics_transition']),
        neural_transitions=int(snapshot.diagnostics['neural_transition_count']), finite=True)


class LiveObserver:
    """No session/brain/actuator reference and no client-input interface."""
    def __init__(self, server_factory=CheckedPoseServer, clock=time.monotonic):
        self.server = server_factory()
        self.clock = clock
        self.disabled = False
        self.record = dict(schema='balance-live-display-v1', session_id=self.server.session_id,
            provisional=True, offers=[], faults=[], sent_frames=0, replaced_frames=0,
            visual_review='UNCONFIRMED', publication_proves_receipt=False)

    def start(self):
        # A bind fault is fatal BEFORE native construction, unlike midrun faults.
        try:
            self.server.start()
        except Exception as exc:
            self.fault(exc)
            self.server.close()
            raise

    def fault(self, exc):
        self.record['faults'].append(f'{type(exc).__name__}: {exc}')
        self.disabled = True

    def observe(self, context, sample, index):
        if self.disabled:
            return
        try:
            self.server.check()
            now = self.clock()
            if not self.server.due(now):
                return
            snapshot = sample_snapshot(context, sample, index)
            packet = packet_for(snapshot, self.server.session_id, self.server._sequence)
            offer = dict(state_index=index, wall_monotonic_s=now, packet=packet, published=False)
            self.record['offers'].append(offer)
            offer['published'] = self.server.publish(snapshot, now=now)
            if offer['published']:
                # Journal the exact local wire bytes, not a claim of delivery.
                with self.server._lock:
                    actual = decode(self.server._newest)
                offer['wire_packet'] = actual
                if encode(actual) != encode(packet):
                    raise ValueError('offered/queued pose mismatch')
        except Exception as exc:
            self.fault(exc)

    def close(self):
        try:
            if not self.disabled:
                self.server.check()
        except Exception as exc:
            self.fault(exc)
        try:
            self.server.close()
        except Exception as exc:
            self.fault(exc)
        self.record.update(sent_frames=self.server.sent_frames,
                           replaced_frames=self.server.replaced_frames)
        return self.record


def audit_display(arm, record):
    """Separate projection integrity from scientific validity and human review."""
    try:
        if (record['schema'] != 'balance-live-display-v1' or record['provisional'] is not True
                or record['publication_proves_receipt'] is not False or not record['session_id']):
            raise ValueError('provisional display identity required')
        sequence, previous, last_wall, last_publish, published = 0, -1, float('-inf'), float('-inf'), 0
        for offer in record['offers']:
            index, wall = offer['state_index'], offer['wall_monotonic_s']
            if (type(index) is not int or not previous < index < len(arm['samples'])
                    or not math.isfinite(wall) or wall < last_wall):
                raise ValueError('display index/wall ordering mismatch')
            expected = packet_for(sample_snapshot(arm['context'], arm['samples'][index], index),
                                  record['session_id'], sequence)
            if encode(offer['packet']) != encode(expected) or type(offer['published']) is not bool:
                raise ValueError('display packet differs from raw scientific state')
            if offer['published']:
                if wall - last_publish < 1./30.:
                    raise ValueError('display publication exceeds declared wall rate')
                if encode(offer['wire_packet']) != encode(expected):
                    raise ValueError('queued wire packet differs from scientific state')
                sequence += 1
                published += 1
                last_publish = wall
            previous, last_wall = index, wall
        for key in ('sent_frames', 'replaced_frames'):
            if type(record[key]) is not int or record[key] < 0:
                raise ValueError('invalid local display counters')
        if record['faults']:
            raise ValueError('recorded observation fault: ' + '; '.join(record['faults']))
        return dict(status='UNCONFIRMED', projection_status='VERIFIED', session_id=record['session_id'], offered=len(record['offers']),
            published=published, sent_frames=record['sent_frames'], replaced_frames=record['replaced_frames'],
            visual_review='UNCONFIRMED', reason='Local publication is not client receipt or full visual coverage')
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        return dict(status='FAILED', projection_status='FAILED', visual_review='UNCONFIRMED',
                    reason=f'{type(exc).__name__}: {exc}')
