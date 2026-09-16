"""Python port of fly-brain-main/src/codec/{rc,neurons,graph}.js.

The integer arithmetic intentionally mirrors JavaScript's unsigned/int32 operations.
"""

from array import array
import math
import struct

TOP = 1 << 24
PONE = 1 << 12
MOVE = 5


def _i32(x):
    x &= 0xFFFFFFFF
    return x if x < 0x80000000 else x - 0x100000000


class Decoder:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.range = -1
        code = 0
        for _ in range(5):
            code = _i32((code << 8) | self.next())
        self.code = code

    def next(self):
        if self.pos >= len(self.data):
            return 0
        value = self.data[self.pos]
        self.pos += 1
        return value

    def bit(self, probs, index):
        pr = probs[index]
        bound = _i32(((self.range & 0xFFFFFFFF) >> 12) * pr)
        if ((self.code ^ -0x80000000) < (bound ^ -0x80000000)):
            self.range = bound
            probs[index] = pr + ((PONE - pr) >> MOVE)
            result = 0
        else:
            self.code = _i32(self.code - bound)
            self.range = _i32(self.range - bound)
            probs[index] = pr - (pr >> MOVE)
            result = 1
        while ((self.range & 0xFFFFFFFF) >> 24) == 0:
            self.range = _i32(self.range << 8)
            self.code = _i32((self.code << 8) | self.next())
        return result

    def direct(self, nbits):
        value = 0
        while nbits:
            n = min(nbits, 16)
            nbits -= n
            self.range = (self.range & 0xFFFFFFFF) >> n
            x = (self.code & 0xFFFFFFFF) // self.range
            self.code = _i32(self.code - x * self.range)
            value = value * (1 << n) + x
            while ((self.range & 0xFFFFFFFF) >> 24) == 0:
                self.range = _i32(self.range << 8)
                self.code = _i32((self.code << 8) | self.next())
        return value


def probs(n):
    return array("H", [PONE >> 1]) * n


class UInt:
    def __init__(self, contexts):
        self.k = probs(contexts * 32)
        self.m = probs(contexts * 32 * 4)

    def decode(self, decoder, context):
        base, node = context * 32, 1
        for _ in range(5):
            node = (node << 1) | decoder.bit(self.k, base + node)
        bits, result = node - 32, 1
        if bits:
            mb = (base + bits) * 4
            first = decoder.bit(self.m, mb + 1)
            result = (result << 1) | first
            if bits >= 2:
                result = (result << 1) | decoder.bit(self.m, mb + 2 + first)
            if bits >= 3:
                rest = bits - 2
                result = result * (1 << rest) + decoder.direct(rest)
        return result - 1


class SInt(UInt):
    def decode(self, decoder, context):
        value = super().decode(decoder, context)
        return -(value + 1) // 2 if value & 1 else value // 2


def lg(value):
    return (value + 1).bit_length() - 1


def decode_neurons(path):
    raw = memoryview(path.read_bytes())
    magic, version, count = struct.unpack_from("<III", raw)
    if magic != 0x4E594C46 or version != 1:
        raise ValueError(f"{path} is not a FLYN v1 file")
    d = Decoder(raw[12:])
    mid, msc, mcls, mnt, mside, msoma = UInt(1), UInt(32), UInt(32), UInt(32), UInt(32), SInt(3)
    has_probs = probs(2)
    body_ids, soma = array("q"), array("f")
    classes, nts, superclasses, sides = array("H"), array("B"), array("B"), array("B")
    body_id, previous_has, previous = 0, 1, [0, 0, 0]
    nan = float("nan")
    for _ in range(count):
        body_id += mid.decode(d, 0)
        body_ids.append(body_id)
        superclass = msc.decode(d, 0)
        superclasses.append(superclass)
        classes.append(mcls.decode(d, superclass))
        nts.append(mnt.decode(d, superclass))
        sides.append(mside.decode(d, superclass))
        has = d.bit(has_probs, previous_has)
        previous_has = has
        for axis in range(3):
            if has:
                previous[axis] += msoma.decode(d, axis)
                soma.append(previous[axis])
            else:
                soma.append(nan)
    return count, body_ids, soma, classes, nts, superclasses, sides


def decode_graph(path):
    raw = memoryview(path.read_bytes())
    magic, version, count, edge_count, minimum = struct.unpack_from("<IIIII", raw)
    if magic != 0x47594C46 or version != 1:
        raise ValueError(f"{path} is not a FLYG v1 file")
    d = Decoder(raw[20:])
    mdeg, mfirst, mgap, mw = UInt(24), SInt(24), UInt(24), UInt(48)
    copy_probs = probs(4 * 8 * 2)
    order = array("I", (d.direct(18) for _ in range(count)))
    coded_ptr = array("I", [0])
    coded_targets, coded_weights = array("I"), array("H")
    prev_targets, prev_weights, previous_degree = [], [], 0
    for row in range(count):
        degree = mdeg.decode(d, min(lg(previous_degree), 23))
        ratio = min(7, max(0, lg(degree) - lg(len(prev_targets)) + 4)) if prev_targets else 0
        copied, previous_bit = [], 0
        for i in range(len(prev_targets)):
            ctx = (previous_bit * 8 + ratio) * 2 + (1 if i == 0 else 0)
            previous_bit = d.bit(copy_probs, ctx)
            if previous_bit:
                copied.append(i)
        residual, last, previous_gap = [], -1, 0
        for i in range(degree - len(copied)):
            if i == 0:
                last = row + mfirst.decode(d, min(lg(degree), 23))
            else:
                gap = mgap.decode(d, min(lg(previous_gap), 23))
                previous_gap, last = gap, last + gap + 1
            residual.append(last)
        targets, weights = [], []
        ci = ri = previous_weight = 0
        while ci < len(copied) or ri < len(residual):
            ct = prev_targets[copied[ci]] if ci < len(copied) else 0xFFFFFFFF
            rt = residual[ri] if ri < len(residual) else 0xFFFFFFFF
            if ct < rt:
                ref = prev_weights[copied[ci]]
                weight = mw.decode(d, 24 + min(lg(ref - minimum), 23))
                target = ct
                ci += 1
            else:
                weight = mw.decode(d, min(lg(previous_weight), 23))
                target = rt
                ri += 1
            targets.append(target)
            weights.append(weight + minimum)
            previous_weight = weight
        coded_targets.extend(targets)
        coded_weights.extend(weights)
        coded_ptr.append(len(coded_targets))
        prev_targets, prev_weights, previous_degree = targets, weights, degree
    if len(coded_targets) != edge_count:
        raise ValueError(f"FLYG decoded {len(coded_targets)} entries, header says {edge_count}")

    # Restore original row/target numbering exactly as the JS decoder's second pass.
    row_ptr = array("I", [0]) * (count + 1)
    for row in range(count):
        row_ptr[order[row] + 1] = coded_ptr[row + 1] - coded_ptr[row]
    for i in range(count):
        row_ptr[i + 1] += row_ptr[i]
    target_starts = array("I", [0]) * (count + 1)
    for target in coded_targets:
        target_starts[order[target] + 1] += 1
    for i in range(count):
        target_starts[i + 1] += target_starts[i]
    row_of = array("I", [0]) * edge_count
    weight_of = array("H", [0]) * edge_count
    for row in range(count):
        old_row = order[row]
        for j in range(coded_ptr[row], coded_ptr[row + 1]):
            target = order[coded_targets[j]]
            slot = target_starts[target]
            target_starts[target] += 1
            row_of[slot] = old_row
            weight_of[slot] = coded_weights[j]
    targets = array("I", [0]) * edge_count
    weights = array("H", [0]) * edge_count
    cursor = array("I", row_ptr[:-1])
    source = 0
    for target in range(count):
        end = target_starts[target]
        while source < end:
            row = row_of[source]
            slot = cursor[row]
            cursor[row] += 1
            targets[slot] = target
            weights[slot] = weight_of[source]
            source += 1
    return count, edge_count, minimum, row_ptr, targets, weights
