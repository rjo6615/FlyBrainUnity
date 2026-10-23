// Execute the checked-in reference, including regional scaling and calibration.
// Input comes from the Python fixture; forced events have probability 1 so RNG
// algorithms do not contaminate the equation/order comparison.
import fs from 'node:fs';
import { createBrain, brainScales } from '../../fly-brain-main/src/brainmodel.js';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const data = {N: input.sizes.length, meta: input.meta,
  superclass: Uint8Array.from(input.superclass), cls: Uint16Array.from(input.cls),
  nt: Uint8Array.from(input.nt), indptr: Uint32Array.from(input.indptr),
  indices: Uint32Array.from(input.indices), weights: Uint16Array.from(input.counts)};
const size = Float32Array.from(input.sizes);
const options = JSON.parse(fs.readFileSync(new URL('../../fly-brain-main/public/data/brain_params.json', import.meta.url)));
const scales = brainScales(data, size, options);
const net = createBrain(data, size, options, Float32Array.from(input.signs));
const states = [];
for (let t = 0; t < input.steps; t++) {
  net.drive.fill(0);
  for (const index of input.events[t] || []) net.setDrive([index], 1000 / net.p.dt);
  const spikes = net.step();
  states.push({v: [...net.v], e: [...net.gE], i: [...net.gI], r: [...net.refr],
    counts: [...net.spikeCount], spikes: [...spikes].sort((a,b) => a-b)});
}
console.log(JSON.stringify({scales: [...scales.inScale], region: [...scales.region],
  sensory: [...scales.sensoryMask], weights: [...net.weights], sign: [...net.p.preSign],
  threshold: [...net.thr], bias: [...net.bias], states}));
