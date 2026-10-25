"""Static LF route/attachment inventory; no transplanted sites or native run."""
import argparse
import importlib.metadata as packages
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np

from . import lf_target_orientation as orientation
from . import coxa_yaw_anatomical_sign_bridge as bridge

ROOT = orientation.ROOT
DIRECTORY = 'docs/evidence/lf-route-attachment-v1/'
SNAPSHOT = DIRECTORY+'source-extracts.json'
SNAPSHOT_SHA = '2c2a30ec54b1cc374eeb301e1cf87305799a07fc0fb936b9a0a3e7c95c3685f4'
UPSTREAM = orientation.DIRECTORY+'run/validation.json'
UPSTREAM_SHA = '5daa911adc01cc42e4f40576a47ff87024497ec23309e3a01645b66815db27c9'
SCHEMA = 'lf-route-attachment-v1'
TENDONS = orientation.native.contract.force.TENDONS


def mesh_summary(raw):
    """Binary-STL data identity, not an anatomical surface-registration method."""
    if len(raw) < 84: raise ValueError('binary STL header/count missing')
    count = struct.unpack_from('<I', raw, 80)[0]
    if count == 0 or len(raw) != 84+50*count:
        raise ValueError('binary STL facet count/byte length mismatch')
    facets = np.frombuffer(raw, offset=84, dtype=np.dtype([
        ('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')]))
    vertices = facets['vertices']
    if not np.isfinite(vertices).all(): raise ValueError('nonfinite mesh vertices')
    return dict(triangles=count, ordered_vertices_sha256=orientation.lineage.sha(vertices.tobytes()),
        minimum=vertices.min(axis=(0, 1)).astype(float).tolist(),
        maximum=vertices.max(axis=(0, 1)).astype(float).tolist(),
        scope='ORDERED_NUMERIC_VERTICES_NOT_SHAPE_HOMOLOGY_OR_PHYSICAL_UNITS')


def extract_xml(raw, source=False):
    tree = ET.fromstring(raw)
    if tree.findall('.//include'): raise ValueError('included definitions require separate resolution')
    world = tree.find('worldbody')
    if world is None: raise ValueError('worldbody required')
    parents = {child: parent for parent in tree.iter() for child in parent}
    def owner(node):
        while node in parents:
            node = parents[node]
            if node.tag == 'body': return node.get('name')
        return 'world'
    sites = [dict(attributes=dict(n.attrib), owner_body=owner(n)) for n in world.iter('site')]
    body_records = []
    for name in ('Thorax', 'LFCoxa'):
        bodies = [b for b in world.iter('body') if b.get('name') == name]
        if len(bodies) != 1: raise ValueError('unique exact XML body required: '+name)
        body = bodies[0]
        geoms = [g for g in body.findall('geom') if g.get('mesh')]
        if len(geoms) != 1: raise ValueError('one direct body mesh geom required: '+name)
        geom = geoms[0]
        meshes = [m for m in tree.findall('./asset/mesh') if m.get('name') == geom.get('mesh')]
        if len(meshes) != 1: raise ValueError('unique exact mesh reference required')
        body_records.append(dict(body=dict(body.attrib), geom=dict(geom.attrib), mesh=dict(meshes[0].attrib)))
    routes = []
    if source:
        checked = orientation.native.pose.binding.inspect_model(raw, orientation.native.pose.binding.MODEL_HASH, TENDONS)
        for row in checked['bindings']:
            resolved = []
            if len(row['tendon_sites']) != 2 or any(set(n) != {'site'} for n in row['tendon_sites']):
                raise ValueError('audit supports exact two-site paths only, not wrapping/pulleys')
            for ref in row['tendon_sites']:
                found = [s for s in sites if s['attributes'].get('name') == ref['site']]
                if len(found) != 1: raise ValueError('unique source route site definition required: '+ref['site'])
                site = found[0]
                position = np.asarray([float(v) for v in site['attributes']['pos'].split()])
                if position.shape != (3,) or not np.isfinite(position).all(): raise ValueError('finite explicit local site position required')
                if site['owner_body'] not in ('Thorax', 'LFCoxa'): raise ValueError('unexpected source owner body')
                resolved.append(dict(**site, local_position=position.tolist(), compiled_site_id=None))
            routes.append(dict(tendon=row['tendon'], actuator_attributes=row['actuator_attributes'], sites=resolved))
    return dict(raw_sha256=orientation.lineage.sha(raw), bodies=body_records, sites=sites,
        tendon_count=len(tree.findall('./tendon/*')), routes=routes,
        scope='XML_DEFINITION_OWNERSHIP_NOT_COMPILED_INDEX_OR_ANATOMICAL_FUNCTION')


def sources():
    result = {}
    for path in (SNAPSHOT, 'docs/LF_ROUTE_ATTACHMENT_V1.md',
                 'malecns_backend/embodiment/lf_route_attachment.py',
                 'malecns_backend/embodiment/coxa_yaw_anatomical_sign_bridge.py',
                 bridge.PREREGISTRATION_PATH.relative_to(ROOT).as_posix()):
        result[path] = orientation.lineage.sha((ROOT/path).read_bytes().replace(b'\r\n', b'\n'))
    if result[SNAPSHOT] != SNAPSHOT_SHA: raise ValueError('route-attachment snapshot changed')
    raw = (ROOT/UPSTREAM).read_bytes()
    if orientation.lineage.sha(raw) != UPSTREAM_SHA: raise ValueError('original orientation raw evidence changed')
    result[UPSTREAM] = UPSTREAM_SHA
    return result


def inspect_assets(snapshot, source_model=None):
    base = Path(packages.distribution('flygym').locate_file(''))
    manifest = orientation.native.pose.force.audit.ROOT/orientation.native.MANIFEST
    installed = json.loads(manifest.read_text(encoding='utf-8'))
    source_manifest = orientation.native.pose.force.audit.ROOT/orientation.native.pose.MANIFEST
    source_manifest = json.loads(source_manifest.read_text(encoding='utf-8'))
    for row in snapshot['files'].values():
        if row['location'] == 'validated_environment':
            raw = (base/row['path']).read_bytes()
            expected = installed['files'][row['path']]
        else:
            if row['kind'] == 'xml':
                expected = dict(sha256=source_manifest['xml_sha256'], bytes=source_manifest['xml_bytes'])
            else: expected = source_manifest['assets'][row['path']]
            raw = ((Path(source_model) if row['kind'] == 'xml' else Path(source_model).parent/row['path']).read_bytes()
                   if source_model is not None else None)
        if row['raw_sha256'] != expected['sha256'] or row['bytes'] != expected['bytes']:
            raise ValueError('original source/target asset lock differs: '+row['path'])
        if raw is not None:
            if orientation.lineage.sha(raw) != row['raw_sha256'] or len(raw) != row['bytes']:
                raise ValueError('asset raw identity mismatch: '+row['path'])
            actual = extract_xml(raw, source=row['location'] == 'FlyMimic') if row['kind'] == 'xml' else mesh_summary(raw)
            if actual != row['extract']: raise ValueError('asset extract differs: '+row['path'])
    if source_model is not None and orientation.native.pose.manifest(source_model) != source_manifest:
        raise ValueError('complete original source model/assets manifest differs')


def build():
    before = sources()
    ready = orientation.preflight()
    native_record = orientation.native.load_report(ROOT/UPSTREAM)
    evaluated = orientation.evaluate(native_record, ready)
    if (evaluated != native_record['evaluation'] or evaluated['classification'] !=
            'TARGET_ORIENTATION_GEOMETRY_VERIFIED_TRANSFER_BLOCKED'):
        raise ValueError('original native orientation evidence does not verify')
    snapshot = orientation.lineage.transfer.read(SNAPSHOT)
    inspect_assets(snapshot)
    source, target = [snapshot['files'][key]['extract'] for key in ('source_xml', 'target_xml')]
    prior_binding = orientation.lineage.transfer.read(orientation.lineage.transfer.CONTEXT)['source_model']['bindings']
    if ([r['tendon'] for r in source['routes']] != list(TENDONS)
            or any(row['actuator_attributes'] != old['actuator_attributes'] or
                [dict(site=s['attributes']['name']) for s in row['sites']] != old['tendon_sites']
                for row, old in zip(source['routes'], prior_binding))):
        raise ValueError('exact original route/binding order differs')
    sign_authority = bridge.verify_preregistration()
    compiled = native_record['models']['BEFORE']['components']
    source_meta = orientation.lineage.transfer.read(orientation.POSE_RECORD)['metadata']
    endpoints = []
    for route in source['routes']:
        for index, site in enumerate(route['sites']):
            endpoints.append(dict(tendon=route['tendon'], route_order=index, source_site=site,
                source_compiled_owner_id_from_prior_pose_record=source_meta['body_id'] if site['owner_body'] == 'LFCoxa' else None,
                target_body_counterpart_inventory_id=native_record['frames']['coxa_id'] if site['owner_body'] == 'LFCoxa' else native_record['frames']['thorax_id'],
                target_site_id=None, target_local_position=None, correspondence_authority=None,
                attachment_transform=None, length_velocity_registration=None,
                same_name_body_is_endpoint_correspondence=False))
    comparisons = []
    for body, source_key, target_key in [('Thorax', 'source_thorax', 'target_thorax'), ('LFCoxa', 'source_coxa', 'target_active_coxa')]:
        left, right = snapshot['files'][source_key], snapshot['files'][target_key]
        comparisons.append(dict(body=body, source_mesh=left['path'], target_active_mesh=right['path'],
            source_scale=next(r['mesh']['scale'] for r in source['bodies'] if r['body']['name'] == body),
            target_scale=next(r['mesh']['scale'] for r in target['bodies'] if r['body']['name'] == body),
            raw_bytes_identical=left['raw_sha256'] == right['raw_sha256'],
            ordered_vertices_identical=left['extract']['ordered_vertices_sha256'] == right['extract']['ordered_vertices_sha256'],
            source_facets=left['extract']['triangles'], target_facets=right['extract']['triangles'],
            anatomical_homology=None, point_correspondence=None,
            interpretation='ASSET_IDENTITY_COMPARISON_NOT_ANATOMICAL_NONHOMOLOGY_OR_ALIGNMENT_TEST'))
    if sources() != before: raise ValueError('route audit sources changed during reconstruction')
    return dict(schema=SCHEMA, classification='ROUTE_AUDIT_VERIFIED_TARGET_ATTACHMENTS_UNRESOLVED',
        source_hashes=before, current_motor_count=20, model_coordinates=42, new_admissions=0,
        physics_transitions=0, cns_transitions=0, production_transfer_enabled=False,
        current_original_raw_freezes_satisfied=ready['original_raw_freezes_satisfied'],
        source_model_scope=source['scope'], source_route_count=len(source['routes']), endpoints=endpoints,
        target_xml_site_count=len(target['sites']), target_xml_tendon_count=target['tendon_count'],
        target_compiled_tendon_count=compiled['dimensions']['ntendon'],
        target_compiled_site_names=compiled['inventories']['site'],
        exact_source_site_names_found_in_compiled_target=[e['source_site']['attributes']['name'] for e in endpoints
            if e['source_site']['attributes']['name'] in compiled['inventories']['site']],
        mesh_comparisons=comparisons, landmark_authority=sign_authority['anatomical_metric'],
        landmark_scope='FEMUR_BODY_ORIGIN_SIGN_METRIC_NOT_A_MUSCLE_ATTACHMENT_AUTHORITY',
        physical_force_conversion=None, length_scale_conversion=None, velocity_conversion=None,
        next_task='Predeclare paired source endpoint/native body-frame observations; verify source two-point lengths and derivatives without assigning target muscle sites.')


def verify(path):
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    now = build()
    recorded = saved.get('current_original_raw_freezes_satisfied')
    if type(recorded) is not bool or saved != dict(now, current_original_raw_freezes_satisfied=recorded):
        raise ValueError('saved route-attachment audit differs from reconstructed sources')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path); mode.add_argument('--output-dir', type=Path)
    parser.add_argument('--source-model', type=Path)
    args = parser.parse_args(argv)
    if args.source_model: inspect_assets(orientation.lineage.transfer.read(SNAPSHOT), args.source_model)
    if args.report: saved, now = verify(args.report)
    else:
        saved = now = build(); args.output_dir.mkdir(parents=True, exist_ok=False)
        with (args.output_dir/'audit.json').open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(saved, indent=2, allow_nan=False)+'\n')
    print('ROUTE AUDIT VERIFIED:4source routes/8sites; target attachments UNRESOLVED; transfer BLOCKED.')
    print('Target raw XML sites/tendons:', now['target_xml_site_count'], '/', now['target_xml_tendon_count'])
    print('Target compiled sites/tendons:', len(now['target_compiled_site_names']), '/', now['target_compiled_tendon_count'])
    print('Active target LFCoxa mesh is mirrored RFCoxa; asset comparison is not an anatomical homology verdict.')
    print('Original raw prerequisites recorded/current:', saved['current_original_raw_freezes_satisfied'], '/', now['current_original_raw_freezes_satisfied'])
    print('Roadmap:20/42; new admissions0; native/physics/CNS calls0; no new Unity behavior.')
    print('Next:', now['next_task'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
