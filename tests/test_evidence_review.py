import copy

from malecns_backend import evidence_review as p1

TABLE = dict(types={'IN17A001': 1, 'Ti flexor MN': 3, 'IN13B020': 1}, hemilineages={'17A': 19, '13B': 39},
             classes={'vnc_motor': 68, 'vnc_intrinsic': 967})


def entry(i, q='Q1', measure='graded', grade='B', kind='hemilineage', value='13B', agrees=True, **kw):
    e = dict(id=i, question=q, citation='Author 2020', doi_or_url='10.0/x', preprint=False, primary=True,
             species=p1.SPECIES, stage='adult', preparation='ex vivo', method='whole-cell patch',
             published_identity='13B neurons', mapping=dict(kind=kind, value=value), grade=grade, measure=measure,
             value='no spikes', units='', n=5, summary='s', read_level='full',
             check=dict(second_read=True, agrees=agrees, note=''))
    e.update(kw)
    return e


def target(i, **kw):
    base = dict(q='Q4', measure='target_candidate', grade='A', kind='type', value='Ti flexor MN',
                stimulus_reproducible=True, readout_quantitative=True)
    base.update(kw)
    return entry(i, **base)


def test_validation_rules():
    assert p1.validate(entry('a'), TABLE) == []
    assert 'grade A needs a type in the network' in p1.validate(entry('b', grade='A'), TABLE)
    assert 'grade B needs a hemilineage or class in the network' in p1.validate(entry('c', value='99Z'), TABLE)
    assert 'grade A/B needs Drosophila melanogaster' in p1.validate(entry('d', species='Locusta'), TABLE)
    assert 'measure not declared for question' in p1.validate(entry('e', q='Q2'), TABLE)
    assert 'target needs stimulus_reproducible' in p1.validate(
        entry('f', q='Q4', measure='target_candidate', grade='A', kind='type', value='Ti flexor MN'), TABLE)
    bad = entry('g')
    del bad['n']
    assert p1.validate(bad, TABLE) == ['missing n']


def test_counts_needs_check_primary_and_grade():
    assert p1.counts(entry('a'))
    assert not p1.counts(entry('b', agrees=False))
    assert not p1.counts(entry('c', primary=False))
    assert not p1.counts(entry('d', grade='C', kind='none', value=None, species='Schistocerca gregaria'))


def test_d1_candidate_and_conflict():
    es = [entry('a'), entry('b', value='17A'), entry('c', value='17A', measure='spiking')]
    assert p1.d1(es) == {'hemilineage:13B': 'CANDIDATE', 'hemilineage:17A': 'CONFLICTING'}
    assert p1.d1([entry('d', measure='spiking')]) == {'hemilineage:13B': 'SPIKING'}
    assert p1.d1([entry('e', agrees=False)]) == {}


def test_d2_d3_d4_d5():
    q2 = entry('m', q='Q2', measure='input_resistance', grade='A', kind='type', value='Ti flexor MN', n=12)
    assert p1.d2([q2, dict(q2, id='m2', n=None)]) == {'type:Ti flexor MN|input_resistance': ['m']}
    syn = entry('s', q='Q3', measure='synaptic_sign', kind='class', value='vnc_intrinsic')
    assert p1.d3([syn]) == {'class:vnc_intrinsic|synaptic_sign': ['s']}
    gj = entry('g', q='Q3', measure='gap_junction', kind='class', value='vnc_motor', connectivity_source=False)
    assert p1.d4([gj]) == dict(recorded=['g'], usable=[])
    assert p1.d5([target('t1'), target('t2', stimulus_reproducible=False), target('t3', grade='C', kind='none',
                                                                                   value=None)]) == ['t1']


def test_labels():
    assert p1.label([]) == 'EVIDENCE_INSUFFICIENT'
    assert p1.label([entry('a')]) == 'EVIDENCE_PARTIAL'
    assert p1.label([target('t1')]) == 'EVIDENCE_PARTIAL'
    assert p1.label([entry('a'), target('t1'), target('t2')]) == 'EVIDENCE_SUFFICIENT_FOR_VARIANT'
    assert p1.label([entry('a', measure='spiking'), target('t1'), target('t2')]) == 'EVIDENCE_PARTIAL'


def test_expectations_and_evaluate():
    es = [entry('a'), entry('core', grade='A', kind='type', value='IN17A001', measure='spiking')]
    assert p1.expectations(es, 'EVIDENCE_PARTIAL') == dict(X1=False, X2=True, X3=False, X4=True)
    log = dict(queries=[], screened=[dict(title='x', decision='included')])
    r = p1.evaluate(dict(entries=[entry('a')]), log, TABLE)
    assert r['label'] == 'EVIDENCE_PARTIAL' and r['integrity']['valid_entries']
    dup = p1.evaluate(dict(entries=[entry('a'), entry('a')]), log, TABLE)
    assert dup['label'] == 'INCONCLUSIVE'
    unchecked = copy.deepcopy(entry('b'))
    unchecked['check']['second_read'] = False
    assert p1.evaluate(dict(entries=[unchecked]), log, TABLE)['label'] == 'INCONCLUSIVE'
    assert p1.evaluate(dict(entries=[]), dict(queries=[]), TABLE)['label'] == 'INCONCLUSIVE'
