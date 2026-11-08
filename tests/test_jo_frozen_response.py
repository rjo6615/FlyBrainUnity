from malecns_backend.live import jo_frozen_response as d5
from malecns_backend.live import antennal_gravity_live as live


class Inner:
    def __init__(self):
        self.calls = 0

    def encode(self, data):
        self.calls += 1
        return {'C_left': dict(d=float(self.calls), rate_hz=self.calls)}

    def apply(self, brain, encoded):
        brain.append(encoded)


class T:
    tilt_event = None
    held = live_jo = None
    used_held = False


def test_freeze_holds_last_pre_tilt_output():
    trial, inner = T(), Inner()
    f = d5.Freeze(inner, trial)
    a, b = f.encode(None), f.encode(None)
    assert b['C_left']['d'] == 2. and not trial.used_held
    trial.tilt_event = {'state_index': 5005}
    c, d = f.encode(None), f.encode(None)
    assert c is b and d is b and trial.used_held and trial.live_jo['C_left']['d'] == 4.
    sink = []
    f.apply(sink, c)
    assert sink == [b]


def test_arms_and_split():
    assert len(d5.ARMS) == 61 and d5.ARMS[0] == d5.REPRO
    assert d5.split('G1F_DOWN20_25') == ('G1F', 25)
    assert not set(d5.SEEDS) & set(range(1, 25))


def test_q1_labels():
    assert d5.q1_label(10, 24, 0, 12)[0] == 'JO_FALLS_REPLICATED'
    assert d5.q1_label(0, 24, 0, 12)[0] == 'JO_FALLS_NOT_REPLICATED'
    assert d5.q1_label(3, 24, 0, 12)[0] == 'JO_FALLS_WEAK'


def test_q2_labels():
    P = lambda s, f, n: [(s, f)]*n
    assert d5.q2_label(P(1, 0, 4) + P(0, 0, 20))[0] == 'UNDERPOWERED'
    assert d5.q2_label(P(1, 0, 8) + P(0, 0, 16))[0] == 'RESPONSE_NEEDED'
    label, det = d5.q2_label(P(1, 1, 5) + P(0, 1, 6) + P(0, 0, 13))
    assert label == 'RESPONSE_PROTECTIVE' and det['b'] == 0 and det['c'] == 6
    assert d5.q2_label(P(1, 1, 6) + P(0, 0, 18))[0] == 'RESPONSE_NOT_NEEDED'
    assert d5.q2_label(P(1, 1, 3) + P(1, 0, 3) + P(0, 1, 1) + P(0, 0, 17))[0] == 'INDETERMINATE'


def tick(pre, held, d, rate, live_d=None):
    return dict(pre_tilt=pre, jo_held=held, jo_d={'L': d, 'R': d}, jo_live_d={'L': live_d or d, 'R': live_d or d},
                jo_rate_hz=rate)


def rates(d):
    out = {}
    for side, name in (('L', 'left'), ('R', 'right')):
        for zone, hz in live.ge.zone_rates(d, 'G1').items():
            out[f'{zone}_{name}'] = hz
    return out


def test_freeze_audit():
    pre = [tick(True, False, x, rates(x)) for x in (-.2, -.1)]
    sighted = dict(neural=pre + [tick(False, False, x, rates(x)) for x in (.1, .2)])
    frozen = dict(neural=pre + [tick(False, True, -.1, rates(-.1), live_d=x) for x in (.1, .2)])
    assert d5.freeze_audit(frozen, sighted, 'G1') == (True, 2)
    bad = dict(neural=pre + [tick(False, True, -.1, rates(-.1)), tick(False, True, .2, rates(.2))])
    assert not d5.freeze_audit(bad, sighted, 'G1')[0]
    early = dict(neural=[tick(True, False, -.2, rates(-.2))] + [tick(False, True, -.2, rates(-.2))]*3)
    assert not d5.freeze_audit(early, sighted, 'G1')[0]


def test_labels_and_expectations():
    falls = {}
    for s in d5.SEEDS:
        for t in d5.TYPES:
            falls[f'{t}_DOWN20_{s}'] = dict(falls=False)
    for s in d5.SEEDS[:6]:
        falls[f'G1_DOWN20_{s}'] = falls[f'G1F_DOWN20_{s}'] = dict(falls=True)
        falls[f'FLIP_DOWN20_{s}'] = dict(falls=True)
    out = d5.labels(falls)
    assert out['fall_counts'] == dict(OFF=0, G1=6, G1F=6, FLIP=6, FLIPF=0)
    assert out['Q1'] == 'JO_FALLS_REPLICATED' and out['Q2_counts']['b'] == 6 and out['Q2'] == 'RESPONSE_NEEDED'
    assert out['expectations'] == dict(E1=True, E2=True, E3=True)
