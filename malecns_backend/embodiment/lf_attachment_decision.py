"""Locked-evidence target-attachment decision; no transform fitting or admission."""
import argparse
import json
from pathlib import Path

from . import lf_endpoint_frames_v1_1 as endpoint

ROOT = endpoint.ROOT
DIRECTORY = 'docs/evidence/lf-attachment-decision-v1/'
REVIEW = DIRECTORY+'reference-review.json'
REVIEW_SHA = '3e83c82accb0507fec2a8860427a0cb29a06067d4bed67e0483490081c6bc258'
UPSTREAM = endpoint.DIRECTORY+'run/validation.json'
UPSTREAM_SHA = 'a317d87446c5879b564f21ecd7ffa88572d7b5370e098293c032c695131eae10'
SCHEMA = 'lf-attachment-decision-v1'
METHODS = (
    ('ORIENTATION_ONLY', 'Rotation agreement does not locate anatomical endpoints.'),
    ('COPY_SOURCE_LOCAL_COORDINATES', 'Literal source coordinates do not establish target point correspondence.'),
    ('ALIGN_BODY_ORIGINS_OR_FRAMES', 'A mathematical transform can be defined without establishing its anatomical meaning.'),
    ('SURFACE_OR_ICP_FIT', 'No independent labeled correspondence/validation authority established; no fit performed.'),
    ('LF_RF_MIRROR_ASSUMPTION', 'Target mesh reflection does not establish source fiber/attachment symmetry.'),
    ('FEMUR_ORIGIN_SIGN_LANDMARK', 'Existing sign metric is not an anatomical muscle insertion authority.'),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sources():
    result = endpoint.sources()
    for p in (REVIEW, 'docs/LF_ATTACHMENT_DECISION_V1.md',
              'malecns_backend/embodiment/lf_attachment_decision.py'):
        result[p] = endpoint.o.lineage.sha((ROOT/p).read_bytes().replace(b'\r\n', b'\n'))
    if result[REVIEW] != REVIEW_SHA: raise ValueError('dated reference review changed')
    if endpoint.o.lineage.sha((ROOT/UPSTREAM).read_bytes()) != UPSTREAM_SHA:
        raise ValueError('original accepted endpoint raw evidence changed')
    result[UPSTREAM] = UPSTREAM_SHA
    return result


def assess_current_review(review):
    """Immutable current decision, not an automatic reference-to-mapping validator."""
    if (review['qualifying_endpoint_correspondences'] or review['independently_labeled_source_target_landmark_pairs']
            or review['target_anatomical_annotation_artifacts']
            or any(s['exact_target_endpoint_authority_established'] for s in review['primary_sources'])
            or review['local_export_inspection']['target_endpoint_authority_established']):
        raise ValueError('new reference material requires a separately versioned scientific decision')
    return [dict(candidate=method, registration_authorized=False, transform_computed=False,
        classification='INSUFFICIENT_CURRENT_ENDPOINT_AUTHORITY', reason=reason) for method, reason in METHODS]


def make_request(record, snapshot):
    sm, tm = record['source'], record['target']
    definitions = [s for route in record['ready']['source_routes'] for s in route['sites']]
    requested = []
    for site, sid in zip(definitions, record['source_site_ids']):
        owner = sm['arrays']['site_bodyid'][sid]
        carrier = sm['body_ids'].index(owner)
        requested.append(dict(source_site_name=site['attributes']['name'], source_site_id=sid,
            source_owner_body_name=sm['names']['body'][owner], source_owner_body_id=owner,
            source_body_local_position=sm['arrays']['site_pos'][sid],
            target_named_body_inventory_id=tm['body_ids'][carrier],
            target_annotation_point_id=None, target_local_position=None, independent_correspondence_authority=None,
            registration_transform=None, anatomical_uncertainty=None,
            target_body_counterpart_is_not_attachment_assignment=True))
    files = snapshot['files']
    return dict(schema='lf-attachment-reference-request-v1', status='REFERENCE_REQUEST_ONLY_NOT_MAPPING',
        executable_mapping=False, authorizes_registration=False, authorizes_production=False,
        source_model_raw_sha256=files['source_xml']['raw_sha256'],
        target_model_raw_sha256=files['target_xml']['raw_sha256'],
        source_compiled_identity=sm['identity']['sha256'], target_compiled_identity=tm['identity']['sha256'],
        mesh_locks={k: dict(path=files[k]['path'], raw_sha256=files[k]['raw_sha256']) for k in
            ('source_thorax', 'source_coxa', 'target_thorax', 'target_active_coxa')},
        active_target_coxa_scale=next(r['mesh']['scale'] for r in record['ready']['target_bodies'] if r['body']['name'] == 'LFCoxa'),
        required_endpoint_references=requested,
        required_reference_identity=dict(provider=None, dataset_and_revision=None, annotation_raw_sha256=None,
            specimen_laterality_reflection_context=None, source_frame_origin_orientation=None,
            target_frame_origin_orientation=None, geometric_length_conventions=None,
            independently_labeled_landmark_pairs=None, uncertainty_provenance=None),
        requirements=[
            'Independently annotated attachment or labeled anatomical correspondence tied to the exact assets.',
            'Explicit frame/origin/orientation, length convention and laterality/reflection provenance.',
            'Endpoint identity/owner/index correspondence and uncertainty, not only a transform residual.',
            'Prospective validation plan before residual/outcome inspection; preserve disagreement.',
            'Separately versioned scientific review of acquired reference data; request completion alone is not acceptance.',
        ],
        separate_unresolved_gates=['physical_force_units_and_conversion_lineage', 'individual_neuron_tendon_binding',
            'neural_to_activation', 'nonzero_velocity_physiology_and_target_velocity_transfer', 'original_raw_scientific_prerequisites'])


def build():
    before = sources()
    ready = endpoint.preflight()
    record = endpoint.n.load_report(ROOT/UPSTREAM)
    result = endpoint.evaluate(record, ready)
    if (result != record['evaluation'] or result['classification'] !=
            'ENDPOINT_FRAME_V1_1_OBSERVER_VERIFIED_TRANSFER_BLOCKED'):
        raise ValueError('original endpoint observer evidence does not verify')
    review = endpoint.o.lineage.transfer.read(REVIEW)
    registration = endpoint.o.lineage.transfer.read(endpoint.n.pose.force.audit.PATHS['registration'])
    if review['local_export_inspection']['original_recorded_export_sha256'] != registration['provenance']['evidence_export']['sha256']:
        raise ValueError('original reference-export provenance differs')
    candidates = assess_current_review(review)
    snapshot = endpoint.o.lineage.transfer.read(endpoint.route.SNAPSHOT)
    request = make_request(record, snapshot)
    if sources() != before: raise ValueError('decision sources changed during reconstruction')
    decision = dict(schema=SCHEMA, classification='ATTACHMENT_DECISION_VERIFIED_REFERENCE_REQUIRED',
        decision='NO_TARGET_ENDPOINT_REGISTRATION_AUTHORIZED_FROM_REVIEWED_EVIDENCE', source_hashes=before,
        execution_scope='STATIC_SAVED_EVIDENCE_AND_DATED_REFERENCE_REVIEW_NO_NATIVE_SOLVER_OR_CNS',
        current_motor_count=20, model_coordinates=42, new_admissions=0,
        physics_transitions=0, cns_transitions=0, supported_target_correspondences=0, source_endpoints=8,
        production_transfer_enabled=False, registration_authorized=False, candidate_methods=candidates,
        current_original_raw_freezes_satisfied=ready['original_raw_freezes_satisfied'],
        accepted_observer_classification=result['classification'],
        historical_v1_classification='ENDPOINT_FRAME_INTEGRITY_FAILURE',
        reference_scope=review['scope'], primary_sources=review['primary_sources'],
        additional_source_export_review=review['local_export_inspection'],
        target_coordinates=None, attachment_transforms=None, physical_force_conversion=None,
        reference_request=dict(filename='reference-request.json', canonical_sha256=endpoint.o.lineage.sha(canonical(request))),
        next_task='Acquire and qualify independent attachment/landmark reference artifacts tied to locked source/target assets; no more pose sweeps or fitting as substitutes.')
    return decision, request


def verify(path):
    path = Path(path)
    saved = json.loads(path.read_text(encoding='utf-8'))
    saved_request = json.loads((path.parent/'reference-request.json').read_text(encoding='utf-8'))
    now, request = build()
    recorded = saved.get('current_original_raw_freezes_satisfied')
    if (type(recorded) is not bool or saved != dict(now, current_original_raw_freezes_satisfied=recorded)
            or saved_request != request):
        raise ValueError('saved attachment decision/reference request differs from reconstructed evidence')
    return saved, now


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path); mode.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.report: saved, now = verify(args.report)
    else:
        saved, request = build(); now = saved
        args.output_dir.mkdir(parents=True, exist_ok=False)
        for name, value in [('decision.json', saved), ('reference-request.json', request)]:
            with (args.output_dir/name).open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(value, indent=2, allow_nan=False)+'\n')
    print('ATTACHMENT DECISION VERIFIED: REFERENCE_REQUIRED;0/8target endpoint correspondences supported in reviewed corpus.')
    print('Source observer remains verified; target registration NOT AUTHORIZED; request is not an executable mapping.')
    print('Original raw prerequisites recorded/current:', saved['current_original_raw_freezes_satisfied'], '/', now['current_original_raw_freezes_satisfied'])
    print('Roadmap:20/42;new admissions0;native/physics/CNS calls0;no new Unity behavior.')
    print('Next:', now['next_task'])
    return 0


if __name__ == '__main__': raise SystemExit(main())
