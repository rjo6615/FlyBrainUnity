// Rhythm Step R1b helper: decode fly-brain-main's display skeletons with the checked-in decodeSkel and
// write them as a flat little-endian binary for dng100_size_audit.py. No geometry is changed here.
//   usage: node skeleton_dump.mjs <skeletons.flys> <out.bin>
//   out:   uint32 [N, V, S]  then  uint32 vOff[N+1]  then  float32 pos[3V] (µm)  then  uint32 seg[2S]
import fs from 'node:fs';
import { decodeSkel } from '../../fly-brain-main/src/codec/skel.js';

const [src, out] = process.argv.slice(2);
if (!src || !out) throw new Error('usage: node skeleton_dump.mjs <skeletons.flys> <out.bin>');
const b = fs.readFileSync(src);
const s = decodeSkel(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
const S = s.seg.length / 2;
const fd = fs.openSync(out, 'wx');
for (const part of [new Uint32Array([s.N, s.V, S]), s.vOff, s.pos, s.seg])
  fs.writeSync(fd, new Uint8Array(part.buffer, part.byteOffset, part.byteLength));
fs.closeSync(fd);
