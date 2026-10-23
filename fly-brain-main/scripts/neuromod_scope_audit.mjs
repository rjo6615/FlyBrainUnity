// Static scope audit using the actual Neuromod class; no LIF or body simulation.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Neuromod, NEUROMOD, isOctopaminergic} from '../src/sim/neuromod.js';
import {decodeNeurons} from '../src/codec/neurons.js';
import {decodeGraph} from '../src/codec/graph.js';

export const WATCHED = [817210, 820110, 820896, 825721, 1050248133, 1050380236,
  1050815462, 801079, 1050111955, 815843, 815569, 135305, 902679, 800567,
  46348, 905447, 800022, 903285, 801128, 56710, 919576];

export function auditScope(data, calibration, minSyn, watched = WATCHED) {
  if (!Number.isInteger(minSyn) || minSyn < 1) throw Error('invalid minimum synapses');
  const types = data.meta.types;
  for (const [field, predicate] of [['oaThr', isOctopaminergic], ['ipcThr', t => t === 'IPC']]) {
    const expected = types.flatMap((t, i) => predicate(t) ? [String(i)] : []).sort();
    const actual = Object.keys(calibration[field] || {}).sort();
    if (JSON.stringify(expected) !== JSON.stringify(actual)) throw Error(`calibration identity mismatch: ${field}`);
    if (Object.values(calibration[field]).some(x => !Number.isFinite(x))) throw Error('nonfinite calibration');
  }
  // Detached threshold-only receiver, never an actual simulation brain.
  const receiver = {thr: new Float32Array(data.N), spikeCount: new Uint32Array(data.N),
    setThr(i, value) { this.thr[i] = value; }};
  const modulation = new Neuromod(data, receiver, {calib: calibration, minSyn});
  modulation.modulate(); // Held modeled oaFed rate, not measured dynamic tone.
  const slots = new Map(Array.from(modulation.targets, (i, k) => [i, k]));
  const indexByBody = new Map(Array.from(data.bodyIds, (id, i) => [String(id), i]));
  const rows = watched.map(body => {
    const i = indexByBody.get(String(body));
    if (i === undefined) throw Error(`unknown watched body ID: ${body}`);
    const sources = [];
    for (const pre of modulation.oa) {
      let count = 0;
      for (let k = data.indptr[pre]; k < data.indptr[pre + 1]; k++) {
        if (data.indices[k] === i && data.weights[k] >= minSyn) count += data.weights[k];
      }
      if (count) sources.push({body_id: String(data.bodyIds[pre]), dense_index: pre,
                              type: types[pre], anatomical_synapses: count});
    }
    const slot = slots.get(i);
    return {body_id: String(body), dense_index: i, type: types[i],
      direct_oa_sources: sources,
      anatomical_synapses: sources.reduce((sum, x) => sum + x.anatomical_synapses, 0),
      held_reference_fed_shift_mv: slot === undefined ? 0 : modulation.shift[slot],
      is_modulatory_cell: slot === undefined ? false : Boolean(modulation.isCell[slot])};
  });
  const targetSuperclasses = {};
  if (data.superclass && data.meta.superclasses) {
    for (const i of modulation.targets) {
      const name = data.meta.superclasses[data.superclass[i]];
      targetSuperclasses[name] = (targetSuperclasses[name] || 0) + 1;
    }
  }
  return {schema: 'neuromodulation-scope-v1', provenance: 'STATIC_REFERENCE_MODEL_AUDIT',
    lif_simulation: false, body_simulation: false, min_synapses: minSyn,
    oa_neurons: modulation.nOA, ipc_neurons: modulation.ipc.length,
    unique_direct_oa_targets: modulation.targets.length,
    direct_target_superclasses: targetSuperclasses,
    reference_parameters: {...NEUROMOD}, calibration_index_population_verified: true,
    interpretation: 'Held reference oaFed rate applied to raw OA synapse counts. No dynamic tone, spike prediction, receptor validation, or causal claim. Missing direct OA input does not exclude indirect effects.',
    watched: rows};
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2 || args[0] !== '--output') throw Error('usage: node fly-brain-main/scripts/neuromod_scope_audit.mjs --output report.json');
  const root = new URL('../public/data/', import.meta.url);
  const read = name => fs.readFileSync(new URL(name, root));
  const buffer = name => {const b = read(name); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);};
  const neurons = decodeNeurons(buffer('neurons.flyn'));
  const graph = decodeGraph(buffer('graph.flyg'));
  if (neurons.N !== graph.N) throw Error('neuron/graph size mismatch');
  const meta = JSON.parse(read('meta.json'));
  const calibration = JSON.parse(read('neuromod.json'));
  const options = JSON.parse(read('brain_params.json'));
  const report = auditScope({...neurons, ...graph, meta}, calibration, options.minSyn);
  report.calibration_context = {fed_energy: calibration.fedEnergy, calibration_seconds: calibration.secs};
  report.source_sha256 = Object.fromEntries(['neurons.flyn', 'graph.flyg', 'meta.json', 'neuromod.json', 'brain_params.json'].map(name =>
    [name, createHash('sha256').update(read(name)).digest('hex')]));
  report.source_sha256['src/sim/neuromod.js'] = createHash('sha256').update(fs.readFileSync(new URL('../src/sim/neuromod.js', import.meta.url))).digest('hex');
  fs.writeFileSync(args[1], JSON.stringify(report, null, 2) + '\n');
  console.log(`Static audit complete: ${report.oa_neurons} OA, ${report.ipc_neurons} IPC, ${report.unique_direct_oa_targets} direct targets.`);
  for (const row of report.watched) console.log(`${row.body_id} ${row.type}: OA synapses=${row.anatomical_synapses}, held-fed shift=${row.held_reference_fed_shift_mv.toFixed(6)} mV`);
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
