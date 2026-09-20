# M6C-P1 Tier-A provenance mismatch diagnosis

## Scope and safety

This is a provenance-only diagnosis. M6C science was not executed, neither the
Tier-A nor M6B scientific artifact was edited or regenerated, and no
provenance or acceptance check was weakened. The Windows artifact that failed
preflight was not available in this checkout, so its raw hash cannot be
reported directly; the deterministic Windows checkout representation is
reported separately below.

## Identity and lock

M6C resolves `TIER_A_PATH` to the repository-root artifact
`six_tibia_causal_result.json`. It is the completed Milestone 4B-2 simultaneous
six-tibia causal result. This legacy result has no explicit `schema` member;
its effective artifact schema is the `six_tibia_causal` result shape documented
for Milestone 4B-2, and its completed validation classification is `S7`.

M6C expects the raw-byte SHA-256
`18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271`.
That value was introduced with M6C in commit
`d13570342cee6985774c3190adc9e0461d4649db` and is the SHA-256 of the blob
committed by `598f9820c18b28d90f815a766406007d687a423e` (the only artifact-changing
commit in `git log --all --follow`). The task-supplied implementation object
`d3742c06f400aceeca71d56ead12f4cab60dbad8` is not present in this clone, but
the merged implementation has the same lock-introducing commit and code.

The current repository file and the historical committed artifact are byte
identical: 9,555 bytes, raw SHA-256
`18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271`,
and Git blob ID `804abe7f0f95f199c114d6ad39195d89f00bea0c`. Thus the expected hash is the
**correct historical canonical hash**, not stale and not a hash of another
artifact or serialization.

## What M6C actually validates

The raw lock is checked before JSON parsing. `_read_locked` hashes
`Path.read_bytes()` and raises `ProvenanceFailure("Tier-A raw-byte SHA256
mismatch")`; `load_provenance` invokes it for Tier-A before the M6B lock and
before any Windows adapter is imported. If bytes pass, `validate_tier_a`
requires exactly:

* classification `S7`;
* seed `1`;
* duration `500` ms; and
* ordered `per_leg` keys `LF`, `LM`, `LH`, `RF`, `RM`, `RH`.

The artifact also records pre-motor equivalence, global and per-leg causal
milestones, sensory/motor spikes, decoded/applied/physical divergences,
trajectories, body-level differences, timing, mapping hash, producing commit,
provenance categories, and scientific safeguards. M6C does not semantically
revalidate all those fields. In particular, action indices and coordinate
signs do not occur in this result: M6C obtains the ordered 42-action inventory
and indices from locked M6A, defines the six Tier-A names in code, and assigns
the existing decoder sign `+1`.

The resulting six interfaces were cross-checked against the intended result's
ordered `per_leg` membership and the locked M6A inventory:

| leg | actuator | action index | M6C coordinate sign |
|---|---|---:|---:|
| LF | `joint_LFTibia` | 5 | +1 |
| LM | `joint_LMTibia` | 12 | +1 |
| LH | `joint_LHTibia` | 19 | +1 |
| RF | `joint_RFTibia` | 26 | +1 |
| RM | `joint_RMTibia` | 33 | +1 |
| RH | `joint_RHTibia` | 40 | +1 |

This cross-check establishes identity and consistency; it is not an inference
of scientific validity from the list alone.

## Representation comparison

The canonical blob is UTF-8 without BOM, contains 265 LF terminators and no CR
bytes, ends in one newline, and retains its two-space JSON indentation and key
order. Relevant representations are:

| representation | bytes | SHA-256 |
|---|---:|---|
| committed/current Linux raw bytes | 9,555 | `18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271` |
| normalized LF | 9,555 | `18aaafd51360e0a60b56f98c0b93e156e4cba2a27efd653111b04a5b8c329271` |
| Git checkout with `core.autocrlf=true` | 9,820 | `f0163e17424996b92e092f7ba8e74bb330469897eb04fdd5a0b4dc05db950720` |
| no final newline (excluded hypothesis) | 9,554 | `2620c3f0cfea78b33407dc7eafc3cfe03bd720d542518f437486c3e5540999b9` |
| UTF-8 BOM prepended (excluded hypothesis) | 9,558 | `692f24e78e6b48ce97a8f2d785604b75a3eb46c0e868644b7c1cc769ad46f2b3` |

A controlled Git materialization with `core.autocrlf=true` changes every one
of the 265 line terminators from LF to CRLF and makes no other byte change.
Removing those 265 CR bytes reproduces the committed artifact exactly. JSON
parsing of both representations yields equal values, so whitespace,
indentation, key order, trailing-newline semantics, and every scientific field
are unchanged. There are no scientific differences in mappings, action
indices, coordinate signs, validation classification, causal results, sensory
or motor evidence, seed, duration, milestones, provenance, or interface
definitions.

The repository `.gitattributes` protects several other raw-byte-locked JSON
inputs with `-text`, including M6A, but does not protect
`six_tibia_causal_result.json`. Therefore a normal Windows checkout may
materialize this mutable working-tree copy with CRLF while the repository blob
and M6C constant remain LF. M6C locked the correct completed result, not an old
preregistration or an M5/M6 result, but omitted the cross-platform
materialization protection required by its raw-byte policy.

## Conclusion and deferred repair

Classification: **`REPRESENTATION_ONLY_PROVENANCE_MISMATCH`**, specifically a
repository-checkout line-ending/materialization defect. This conclusion is
fully confirmed if the unavailable Windows file hashes to
`f0163e17424996b92e092f7ba8e74bb330469897eb04fdd5a0b4dc05db950720`;
if it has another hash, its bytes must be supplied before classifying that
particular copy. The repository evidence excludes a stale lock and wrong
artifact lock.

M6C needs a provenance-only repair: add the exact root path
`six_tibia_causal_result.json -text` to `.gitattributes`, then rematerialize the
file from the already committed blob (not normalize, rewrite, or regenerate a
scientific result). That repair is deliberately **not performed here**. It
would preserve strict raw-byte validation and change no scientific protocol,
result, data, mapping, threshold, or acceptance criterion.

For the future Windows preflight, the reviewed completed M6B artifact should
be passed without modifying it:

```powershell
.\fly-brain-interactive\.venv\Scripts\python.exe -m malecns_backend.embodiment.integrated_whole_leg_readiness --m6b-sha256 02a4bbb7ec79ccf0967e9b8499c5a68d0ed8133a56688592ba13cfb2785285a2 --preflight-windows
```

This command is documented only; it was not executed.

SCIENTIFIC M6C EXECUTED: **NO**  
TIER-A SCIENTIFIC ARTIFACT MODIFIED: **NO**  
M6B SCIENTIFIC ARTIFACT MODIFIED: **NO**  
PROVENANCE VALIDATION WEAKENED: **NO**
