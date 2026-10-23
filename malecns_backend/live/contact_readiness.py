"""Passive live-v3 Tarsus5 force/contact survey; no tactile events are delivered."""
import argparse
import json
import math
from pathlib import Path

LEGS = ('LF', 'LM', 'LH', 'RF', 'RM', 'RH')
THRESHOLD = 1e-12  # Existing engineering comparison, not a biological threshold.


def sample_distal_contact(physics, identity, contact_forces):
    """Use exact Tarsus5 body ownership and recognized ground geom IDs."""
    import numpy as np
    raw = np.asarray(contact_forces, dtype=float)
    if raw.shape != (36, 3) or not np.isfinite(raw).all():
        raise ValueError('contact readiness requires finite (36, 3) force telemetry')
    ground = set(identity['ground_geom_ids'])
    result = {}
    for position, leg in enumerate(LEGS):
        bid = identity['tarsus5_body_ids'][leg]
        geoms = {i for i in range(int(physics.model.ngeom))
                 if bid is not None and int(physics.model.geom_bodyid[i]) == bid}
        available = bool(ground and geoms and bid is not None)
        pairs = []
        if available:
            for c in physics.data.contact[:physics.data.ncon]:
                a, b = int(c.geom1), int(c.geom2)
                if (a in geoms and b in ground) or (b in geoms and a in ground):
                    pairs.append((a, b))
        vector = tuple(map(float, raw[position * 6 + 5]))
        result[leg] = {'force_row': position * 6 + 5, 'force_vector': vector,
                       'force_magnitude': math.sqrt(sum(x*x for x in vector)),
                       'identity_available': available, 'ground_contact': bool(pairs),
                       'exact_geom_pairs': tuple(pairs)}
    return result


class ContactReadinessSurvey:
    """Bounded aggregates only; no encoder, RNG or brain state access."""
    collect_distal_contact = True

    def __init__(self):
        self.samples = 0
        self.first_time_ms = self.last_time_ms = None
        self.rows = {leg: dict(force_row=i*6+5, identity_samples=0,
            ground_contact_samples=0, force_positive_samples=0,
            contact_with_force_samples=0, contact_without_force_samples=0,
            force_without_ground_contact_samples=0, neither_samples=0,
            ground_contact_onsets=0, peak_force_magnitude=0.,
            first_geom_pairs=None) for i, leg in enumerate(LEGS)}
        self.previous = dict.fromkeys(LEGS, False)

    def __call__(self, record):
        if 'physics_transition_index' not in record:
            return
        time_ms = float(record['physics_time_ms'])
        if not math.isfinite(time_ms) or (self.last_time_ms is not None and time_ms <= self.last_time_ms):
            raise ValueError('physics samples must have finite increasing times')
        data = record['contact_information']['distal_contact_readiness']
        # Validate the complete record before mutating aggregate state.
        for i, leg in enumerate(LEGS):
            value = data[leg]
            if value['force_row'] != i*6+5:
                raise ValueError('unexpected distal force row')
            if not math.isfinite(value['force_magnitude']) or value['force_magnitude'] < 0:
                raise ValueError('invalid force magnitude')
        self.samples += 1
        self.first_time_ms = time_ms if self.first_time_ms is None else self.first_time_ms
        self.last_time_ms = time_ms
        for leg in LEGS:
            value, row = data[leg], self.rows[leg]
            force = value['force_magnitude'] > THRESHOLD
            contact = bool(value['ground_contact'])
            row['peak_force_magnitude'] = max(row['peak_force_magnitude'], value['force_magnitude'])
            row['force_positive_samples'] += force
            if not value['identity_available']:
                self.previous[leg] = False
                continue
            row['identity_samples'] += 1
            row['ground_contact_samples'] += contact
            row['contact_with_force_samples'] += contact and force
            row['contact_without_force_samples'] += contact and not force
            row['force_without_ground_contact_samples'] += force and not contact
            row['neither_samples'] += not contact and not force
            row['ground_contact_onsets'] += contact and not self.previous[leg]
            if contact and row['first_geom_pairs'] is None:
                row['first_geom_pairs'] = [list(pair) for pair in value['exact_geom_pairs']]
            self.previous[leg] = contact

    def report(self):
        rows = {}
        for leg, row in self.rows.items():
            status = ('IDENTITY_UNAVAILABLE' if row['identity_samples'] != self.samples or not self.samples
                      else 'NO_OBSERVED_TARSUS5_GROUND_CONTACT' if not row['ground_contact_samples']
                      else 'CONTACT_OBSERVED_FORCE_ZERO' if not row['contact_with_force_samples']
                      else 'CONTACT_AND_FORCE_OBSERVED_REQUIRES_MATCHED_CALIBRATION')
            rows[leg] = dict(row, status=status)
        return dict(schema='live-contact-readiness-v1', samples=self.samples,
            first_time_ms=self.first_time_ms, last_time_ms=self.last_time_ms,
            engineering_threshold=THRESHOLD, tactile_delivery_enabled=False,
            interpretation='Observational coincidence, not force attribution or threshold calibration. Tarsus5-ground contacts only; other collision sources can generate forces. Onset counts include initial observed contact. No matched causal comparison has run.',
            legs=rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration-s', type=float, default=2.)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration_s) or args.duration_s <= 0:
        parser.error('--duration-s must be finite and positive')
    from .headless import create_live_v3_session
    survey = ContactReadinessSurvey()
    session = create_live_v3_session(telemetry_observer=survey)
    completed = False
    error = None
    try:
        state = session.initialize()
        start_ms = state.time_ms
        print('Initialized; surveying current v3 posture without tactile delivery.', flush=True)
        while state.time_ms - start_ms < args.duration_s * 1000:
            state = session.step(lightweight=True)
        completed = True
    except KeyboardInterrupt:
        error = 'KeyboardInterrupt'
    except BaseException as exc:
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            session.close()
        finally:
            report = survey.report()
            report.update(completed=completed, requested_duration_s=args.duration_s, error=error)
            args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            print(f'Saved {args.output}; completed={completed}', flush=True)
    return 0 if completed else 1


if __name__ == '__main__':
    raise SystemExit(main())
