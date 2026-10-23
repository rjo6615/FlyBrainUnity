import test from 'node:test';
import assert from 'node:assert/strict';
import {auditScope} from '../../fly-brain-main/scripts/neuromod_scope_audit.mjs';

function fixture() {
  return {N: 4, bodyIds: [10n, 20n, 30n, 40n],
    meta: {types: ['OA-VUMa1', 'IPC', 'MN', 'IN']},
    indptr: [0, 3, 3, 3, 3], indices: [2, 3, 2], weights: [6, 5, 3]};
}
const calibration = {oaThr: {'0': -2}, ipcThr: {'1': 1}};
test('actual reference uses raw OA counts and configured cutoff, not fast effective weights', () => {
  const data = fixture(); const before = JSON.stringify(data, (_, v) => typeof v === 'bigint' ? String(v) : v);
  const report = auditScope(data, calibration, 6, [30, 40]);
  assert.equal(report.watched[0].anatomical_synapses, 6);
  assert.equal(report.watched[0].direct_oa_sources[0].body_id, '10');
  assert.ok(Math.abs(report.watched[0].held_reference_fed_shift_mv - 2 * 12 / 412) < 1e-7);
  assert.equal(report.watched[1].held_reference_fed_shift_mv, 0);
  assert.equal(report.unique_direct_oa_targets, 1);
  assert.equal(JSON.stringify(data, (_, v) => typeof v === 'bigint' ? String(v) : v), before);
  assert.equal(report.lif_simulation, false);
});
test('cutoff is explicit and deterministic; changing it changes anatomical target coverage', () => {
  const report = auditScope(fixture(), calibration, 5, [40]);
  assert.equal(report.watched[0].anatomical_synapses, 5);
  assert.deepEqual(auditScope(fixture(), calibration, 6, [30]), auditScope(fixture(), calibration, 6, [30]));
});
test('calibration identities, finite values, missing watched neurons and invalid cutoff fail closed', () => {
  assert.throws(() => auditScope(fixture(), {...calibration, oaThr: {'2': 0}}, 6, []), /identity/);
  assert.throws(() => auditScope(fixture(), {...calibration, ipcThr: {}}, 6, []), /identity/);
  assert.throws(() => auditScope(fixture(), {...calibration, oaThr: {'0': NaN}}, 6, []), /nonfinite/);
  assert.throws(() => auditScope(fixture(), calibration, 6, [999]), /unknown/);
  assert.throws(() => auditScope(fixture(), calibration, 0, []), /minimum/);
});
