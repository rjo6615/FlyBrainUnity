import pandas as pd

from malecns_backend import hair_plate_review as p3

TABLE = {'SNpp45': dict(count=60, in_network=6, superclasses=['vnc_sensory']),
         'SNpp46': dict(count=10, in_network=0, superclasses=['vnc_sensory']),
         'IN19A001': dict(count=12, in_network=2, superclasses=['vnc_intrinsic']),
         'MNcx01': dict(count=6, in_network=1, superclasses=['vnc_motor'])}
MCNS = pd.DataFrame(dict(bodyId=[11, 12, 13, 14], type=['SNpp45', 'SNpp45', 'SNpp46', None],
                         synonyms=[None, 'coxal hair plate', None, None], mancType=['SNpp45', 'SNpp45', 'SNpp46', None]))
BANC = pd.DataFrame(dict(root_id=['1', '2', '3', '4', '5', '6'],
                         cell_type=['SNpp45', 'SNpp45', 'SNpp45', 'SNxx01', 'SNpp46', 'CHP1'],
                         cell_function=[None, None, None, 'hairplate proprioception', None, None],
                         cell_sub_class=[None, None, None, None, 'CxHP8 candidate', 'HP_3'],
                         malecns_match=['11', '11', None, '13', '12', '14'],
                         malecns_cell_type=['SNpp45', 'SNpp45', None, None, None, None]))


def base(i, q, kind, agrees=True, **kw):
    e = dict(id=i, question=q, kind=kind, citation='A 2026', doi_or_url='x', preprint=False, primary=True,
             read_level='full', summary='s', check=dict(second_read=True, agrees=agrees, note=''))
    e.update(kw)
    return e


def walk(**kw):
    return base('w', 'Q2', 'crosswalk', datasets=['maleCNS', 'MANC'], crosswalk_level='type', method='m', **kw)


def note(agrees=True, sha='s'):
    return base('ann', 'Q2', 'annotation', agrees=agrees, read_level='dataset', datasets=['BANC', 'maleCNS'],
                output_sha256=sha, link_summary='x')


def ident(i, target, types, level='M-A', ds='FANC', q='Q1', **kw):
    return base(i, q, 'identity', target=target, published_identity='p', source_dataset=ds, level=level, types=types,
                method='NBLAST', **kw)


def tuning(i, target='H1:CxHP8', species=p3.DMEL, grade='B', joint='coxa', readout='tuning_curve', **kw):
    return base(i, 'Q3', 'afferent_tuning', target=target, species=species, grade=grade, preparation='p', joint=joint,
                stimulus='passive', readout=readout, values='v', n=5, method='calcium', **kw)


def fc(i, pairs, neural=True, readout='sign'):
    return base(i, 'Q4', 'functional_connectivity', stimulated=['CxHP8'], recorded=['x'], neural_readout=neural,
                readout=readout, pairs=pairs, method='optogenetics + recording')


def run(entries, table=TABLE, sha='s'):
    q = p3.annotation_query(BANC, MCNS)
    log = dict(queries=[], screened=[dict(title='t', decision='included')])
    return p3.evaluate(dict(entries=entries), log, table, q, [walk()], annotation_sha=sha)


def test_validation():
    assert p3.validate(ident('a', 'H1:CxHP8', ['SNpp45'])) == [] and p3.validate(note()) == []
    assert p3.validate(tuning('t')) == [] and p3.validate(ident('d', 'D:IN19A001', ['IN19A001'], q='Q4')) == []
    assert 'unknown target' in p3.validate(ident('b', 'H9:x', []))
    assert 'unknown target' in p3.validate(ident('b', 'D:IN19A001', [], q='Q1'))
    assert p3.validate(dict(ident('c', 'H1:CxHP8', []), question='Q5')) == ['kind not declared for question']
    assert 'H4 entry needs snpp45_is and SNpp45 in types' in p3.validate(ident('h', 'H4:SNpp45', ['SNpp45']))
    assert p3.validate(ident('h', 'H4:SNpp45', ['SNpp45'], snpp45_is='CxHP8')) == []
    assert 'grade C if and only if not Drosophila melanogaster' in p3.validate(tuning('t', species='Periplaneta americana'))
    assert 'bad joint' in p3.validate(tuning('t', joint='wing'))
    assert 'pair needs a hair-plate stim, a D: recorded cell and a response' in p3.validate(
        fc('f', [dict(stim='H1:CxHP8', rec='IN19A001', response='+')]))
    assert p3.validate(dict(kind='nope')) == ['bad kind']


def test_annotation_query_and_banc_link():
    q = p3.annotation_query(BANC, MCNS)
    rows = {r['fields']['root_id']: r['reasons'] for r in q['banc']['rows']}
    assert rows == {'1': ['typed SNpp45'], '2': ['typed SNpp45'], '3': ['typed SNpp45'], '4': ['hair plate'],
                    '5': ['CxHP'], '6': ['HP token']}                      # CHP1 is not an HP token; HP_3 is
    assert [r['fields']['bodyId'] for r in q['malecns']['rows']] == ['11', '12']
    link = q['banc_to_malecns']
    assert link['SNpp45']['level'] == 'group' and link['SNpp45']['malecns_types'] == ['SNpp45']
    assert link['SNpp45']['carries_over'] and link['SNpp45']['matched_rows'] == 2
    assert link['SNxx01']['level'] == 'neuron' and link['SNxx01']['malecns_types'] == ['SNpp46']
    assert not link['CHP1']['carries_over']                               # body 14 has no male CNS type
    assert p3.carry_map(link) == {'SNpp45': 'SNpp45', 'SNxx01': 'SNpp46', 'SNpp46': 'SNpp45'}


def test_banc_crosswalk_needs_counted_annotation():
    es = [ident('a', 'H1:CxHP8', ['SNxx01'], ds='BANC')]
    assert run(es + [note()])['mappings']['H1:CxHP8'] == dict(status='MAPPED', types=['SNpp46'])
    assert run(es + [note(agrees=False)])['mappings']['H1:CxHP8']['status'] == 'SOURCE_ONLY'
    unlinked = [ident('a', 'H1:CxHP8', ['CHP1'], ds='BANC'), note()]
    assert run(unlinked)['mappings']['H1:CxHP8']['status'] == 'SOURCE_ONLY'  # no carry-over, no name match
    assert run([ident('a', 'H1:CxHP8', ['SNpp45'], ds='MANC'), note()])['mappings']['H1:CxHP8']['status'] == 'MAPPED'


def test_snpp45_verdict():
    stepa = ident('s', 'H1:CxHP8', ['SNpp45'], level='M-C', ds='maleCNS')
    r = run([stepa, ident('f', 'H1:CxHP8', ['FANC_hp8'], ds='FANC'), note()])
    assert r['snpp45_verdict'] == 'UNRESOLVED' and r['mappings']['H1:CxHP8']['status'] == 'SOURCE_ONLY'
    assert r['expectations']['X1'] and r['reported']['m_c_identities'] == ['s']
    assert run([ident('a', 'H1:CxHP8', ['SNpp45'], ds='MANC'), note()])['snpp45_verdict'] == 'SUPPORTED'
    assert run([ident('a', 'H1:CxHP8', ['SNpp46'], ds='MANC'), note()])['snpp45_verdict'] == 'CONTRADICTED'
    elsewhere = ident('h', 'H4:SNpp45', ['SNpp45'], ds='MANC', snpp45_is='TrHP5')
    r = run([ident('a', 'H1:CxHP8', ['SNpp45'], ds='MANC'), elsewhere, note()])
    assert r['snpp45_verdict'] == 'CONTRADICTED' and r['snpp45_against'] == ['h']
    vague = ident('h', 'H4:SNpp45', ['SNpp45'], ds='MANC', snpp45_is='hair_plate_unspecified')
    assert run([vague, note()])['snpp45_verdict'] == 'UNRESOLVED'
    both = ident('a', 'H1:CxHP8', ['SNpp45', 'SNpp46'], ds='MANC')
    assert run([both, note()])['snpp45_verdict'] == 'UNRESOLVED'


def test_targets_and_labels():
    mapped = ident('a', 'H1:CxHP8', ['SNpp45'], ds='MANC')
    down = ident('d', 'D:IN19A001', ['IN19A001'], ds='MANC', q='Q4')
    mn = ident('m', 'D:MNcx01', ['MNcx01'], ds='maleCNS', q='Q4')
    assert run([tuning('t', target='H2:CxHP3'), note()])['label'] == 'INSUFFICIENT'
    r = run([tuning('t', target='H2:CxHP3'), note()])
    assert r['expectations']['X3'] and r['expectations']['X5']
    assert run([mapped, note()])['label'] == 'MAPPING_ONLY'
    assert run([mapped, tuning('t'), note()])['E_targets'][0]['target'] == 'H1:CxHP8'
    assert run([mapped, tuning('t'), note()])['label'] == 'ENCODER_VALIDATION_AVAILABLE'
    assert run([mapped, tuning('t', readout='qualitative'), note()])['E_targets'] == []
    assert run([mapped, tuning('t', joint='femur'), note()])['E_targets'] == []
    other = tuning('t', species='Carausius morosus', grade='C')
    r = run([mapped, other, note()])
    assert r['E_targets'] == [] and r['reported']['grade_c_tuning'] == ['t']
    one = fc('f', [dict(stim='H1:CxHP8', rec='D:IN19A001', response='excited'),
                   dict(stim='H1:CxHP8', rec='D:IN99', response='x')])
    r = run([mapped, down, one, note()])
    assert [x['rec'] for x in r['C_targets']] == ['D:IN19A001'] and r['mappings']['D:IN99']['status'] == 'UNMAPPED'
    assert r['label'] == 'MAPPING_ONLY'
    two = fc('g', [dict(stim='H1:CxHP8', rec='D:IN19A001', response='excited'),
                   dict(stim='H1:CxHP8', rec='D:MNcx01', response='excited')])
    assert run([mapped, down, mn, two, note()])['label'] == 'TARGETS_AVAILABLE'
    assert run([mapped, down, mn, fc('h', two['pairs'], neural=False), note()])['C_targets'] == []


def test_integrity():
    unchecked = note()
    unchecked['check'] = dict(second_read=False, agrees=False)
    assert run([unchecked])['label'] == 'INCONCLUSIVE'
    assert run([note(), note()])['label'] == 'INCONCLUSIVE'
    assert run([ident('a', 'H1:CxHP8', [])])['label'] == 'INCONCLUSIVE'            # no annotation entry
    assert run([note(sha='other')])['label'] == 'INCONCLUSIVE'                     # entry does not match output
    assert run([note()])['label'] == 'INSUFFICIENT'
