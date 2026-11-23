from malecns_backend import identity_review as p2

TABLE = {'IN13B020': dict(count=2, in_network=1, superclasses=['vnc_intrinsic']),
         'IN13B021': dict(count=2, in_network=0, superclasses=['vnc_intrinsic']),
         'IN10B015': dict(count=2, in_network=2, superclasses=['vnc_intrinsic']),
         'SNpp01': dict(count=10, in_network=0, superclasses=['vnc_sensory']),
         'Ti flexor MN': dict(count=12, in_network=5, superclasses=['vnc_motor'])}


def base(i, q, kind, agrees=True, **kw):
    e = dict(id=i, question=q, kind=kind, citation='A 2024', doi_or_url='x', preprint=False, primary=True,
             read_level='full', summary='s', check=dict(second_read=True, agrees=agrees, note=''))
    e.update(kw)
    return e


def walk(i='w', a='maleCNS', b='MANC', level='type', **kw):
    return base(i, 'Q1', 'crosswalk', datasets=[a, b], crosswalk_level=level, method='typing transfer', **kw)


def ident(i, target, types, level='M-A', ds='MANC', **kw):
    return base(i, 'Q2', 'identity', target=target, published_identity='p', source_dataset=ds, level=level,
                types=types, method='NBLAST', **kw)


def fc(i, pairs, neural=True, readout='presence', **kw):
    return base(i, 'Q5', 'functional_connectivity', stimulated=['club'], recorded=['10Ba'], neural_readout=neural,
                readout=readout, pairs=pairs, method='optogenetics + calcium', **kw)


def test_validation():
    assert p2.validate(walk()) == [] and p2.validate(ident('a', 'T1:13Ba', ['IN13B020'])) == []
    assert 'unknown target' in p2.validate(ident('b', 'T9:x', []))
    assert 'kind not declared for question' in p2.validate(dict(ident('c', 'T1:13Ba', []), question='Q5'))
    assert 'crosswalk needs two known datasets' in p2.validate(walk(b='hemibrain'))
    assert 'pair needs stim and rec targets and a response' in p2.validate(fc('d', [dict(stim='club', rec='x')]))
    assert p2.validate(dict(kind='nope')) == ['bad kind']


def test_crosswalk_carries_types_over():
    es = [ident('a', 'T1:13Ba', ['IN13B020'])]
    assert p2.mappings(es, TABLE)[0]['T1:13Ba']['status'] == 'SOURCE_ONLY'
    maps, walks = p2.mappings(es + [walk()], TABLE)
    assert maps['T1:13Ba'] == dict(status='MAPPED', types=['IN13B020']) and 'MANC' in walks
    assert p2.mappings(es + [walk(level='partial')], TABLE)[0]['T1:13Ba']['status'] == 'SOURCE_ONLY'
    assert p2.mappings(es + [walk(agrees=False)], TABLE)[0]['T1:13Ba']['status'] == 'SOURCE_ONLY'


def test_mapping_rules():
    w = [walk()]
    ok = p2.mappings(w + [ident('a', 'T1:13Ba', ['IN13B020']), ident('b', 'T1:13Ba', ['IN13B020'], ds='maleCNS')], TABLE)[0]
    assert ok['T1:13Ba']['status'] == 'MAPPED'
    bad = p2.mappings(w + [ident('a', 'T1:13Ba', ['IN13B020']), ident('b', 'T1:13Ba', ['IN13B021'])], TABLE)[0]
    assert bad['T1:13Ba'] == dict(status='CONFLICTING', types=['IN13B020', 'IN13B021'])
    cand = p2.mappings(w + [ident('a', 'T2:10Ba', ['IN10B015', 'IN13B021'], level='M-B')], TABLE)[0]
    assert cand['T2:10Ba']['status'] == 'CANDIDATE_SET'
    missing = p2.mappings(w + [ident('a', 'T2:10Ba', ['IN10B999'])], TABLE)[0]
    assert missing['T2:10Ba']['status'] == 'SOURCE_ONLY'
    weak = p2.mappings(w + [ident('a', 'T2:10Ba', ['IN10B015'], level='M-C')], TABLE)[0]
    assert weak['T2:10Ba']['status'] == 'UNMAPPED'


def test_restatements_and_labels():
    w = [walk()]
    es = w + [ident('a', 'T1:13Ba', ['IN13B020']), ident('c', 'T4:club', ['SNpp01']),
              ident('d', 'T5:10Ba', ['IN10B015']), ident('m', 'T6:slow', ['Ti flexor MN'])]
    maps, _ = p2.mappings(es, TABLE)
    d1 = p2.restate_d1(maps, TABLE)
    assert d1['T1:13Ba'] == dict(level='type', status='MAPPED', types=['IN13B020'], in_network=1)
    assert d1['T2:10Ba'] == dict(level='hemilineage', status='UNMAPPED')
    assert list(p2.restate_d2(maps)) == ['T6:slow']
    one = fc('f', [dict(stim='T4:club', rec='T5:10Ba', response='excited'), dict(stim='T4:club', rec='T5:9Ba', response='x')])
    t = p2.d5(es + [one], maps)
    assert [x['rec'] for x in t] == ['T5:10Ba']
    assert p2.label(t, d1) == 'MAPPING_ONLY'
    two = fc('g', [dict(stim='T4:club', rec='T5:10Ba', response='excited'), dict(stim='T4:club', rec='T1:13Ba', response='excited')])
    assert p2.label(p2.d5(es + [two], maps), d1) == 'TARGETS_AVAILABLE'
    assert p2.d5(es + [fc('h', two['pairs'], neural=False)], maps) == []
    assert p2.label([], dict(x=dict(level='hemilineage'))) == 'INSUFFICIENT'


def test_evaluate_and_expectations():
    log = dict(queries=[], screened=[dict(title='t', decision='included')])
    es = [walk(), ident('a', 'T1:13Ba', ['IN13B020', 'IN13B021'], level='M-B'), ident('c', 'T4:club', ['SNpp01'], ds='FANC')]
    r = p2.evaluate(dict(entries=es), log, TABLE)
    assert r['label'] == 'MAPPING_ONLY' and r['mappings']['T4:club']['status'] == 'SOURCE_ONLY'
    assert r['expectations'] == dict(X1=True, X2=True, X3=True, X4=True)
    unchecked = walk()
    unchecked['check'] = dict(second_read=False, agrees=False)
    assert p2.evaluate(dict(entries=[unchecked]), log, TABLE)['label'] == 'INCONCLUSIVE'
    assert p2.evaluate(dict(entries=[walk(), walk()]), log, TABLE)['label'] == 'INCONCLUSIVE'
