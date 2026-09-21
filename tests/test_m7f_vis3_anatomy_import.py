import importlib.util, pathlib, struct

PATH=pathlib.Path(__file__).parents[1]/'tools/import_m7f_vis3_anatomy.py'
spec=importlib.util.spec_from_file_location('vis3',PATH); vis3=importlib.util.module_from_spec(spec); spec.loader.exec_module(vis3)

def binary_stl(path):
    header=b'fixture'+bytes(73)
    facet=struct.pack('<12fH',0,0,1, 1,2,3, 4,5,6, 7,8,9, 0)
    path.write_bytes(header+struct.pack('<I',1)+facet)

def test_reflection_scale_and_winding_are_baked(tmp_path):
    source=tmp_path/'a.stl'; target=tmp_path/'a.obj'; binary_stl(source)
    vis3.convert_stl(source,target,[2,3,4])
    lines=target.read_text().splitlines()
    vertices=[[float(x) for x in line.split()[1:]] for line in lines if line.startswith('v ')]
    expected=[[.2,1.2,.6],[.8,2.4,1.5],[1.4,3.6,2.4]]
    assert all(abs(a-b)<1e-9 for row,want in zip(vertices,expected) for a,b in zip(row,want))
    assert lines[-1]=='f 1 3 2'

def test_authoritative_hash_is_frozen():
    assert vis3.EXPECTED_XML_SHA256=='413b3a1dcb7537d08122e16f256f27ec0d8bb9f52c58670345b6c24c9e72e05a'
