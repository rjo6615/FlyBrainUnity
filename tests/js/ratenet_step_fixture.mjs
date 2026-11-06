// I2 reference fidelity: one Euler step of the checked-in ratenet.js RateNetwork on a fixture.
// Usage: node ratenet_step_fixture.mjs <fixture.json>; prints {"r_next": [...]} as JSON.
import fs from 'node:fs';
import { RateNetwork } from '../../fly-brain-main/src/ratenet.js';
const f = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const N = f.N;
const net = new RateNetwork(N, Uint32Array.from(f.indptr), Uint32Array.from(f.indices), Uint16Array.from(f.weights),
  Uint8Array.from(f.nt), Float32Array.from(f.size),
  { dt: f.dt, b: f.b, snap: 0, adaptK: 0, depU: 0, minSyn: f.minSyn, sizeNorm: true, sizeRef: f.sizeRef,
    maxSizeScale: 1e30, sensoryMask: new Uint8Array(N), seed: 1 });
for (let i = 0; i < N; i++) {
  net.a[i] = f.a_star[i] / net.sizeScale[i]; net.theta[i] = f.theta_star[i] * net.sizeScale[i];
  net.tau[i] = f.tau[i]; net.rmax[i] = f.rmax[i];
  net.r[i] = f.r[i]; net.out[i] = f.r[i]; net.ext[i] = f.I[i]; net.silenced[i] = f.silenced[i];
}
net.recomputeInput();
net.step();
process.stdout.write(JSON.stringify({ r_next: Array.from(net.r) }));
