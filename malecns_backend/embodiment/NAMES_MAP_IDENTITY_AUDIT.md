# MuJoCo 3.2.7 `names_map` identity audit

## Scope and authoritative meaning

The validated LegendaryPC environment is pinned to MuJoCo **3.2.7**.  In that
version, the public `mjModel` type documentation describes `nnames_map` as the
number of slots in the names map and `names_map` as the **internal hash map of
names**.  The corresponding MuJoCo name implementation constructs that table
from the compiled `names` buffer and uses it in `mj_name2id` to accelerate the
lookup of an object ID from an object name.  `mj_id2name` instead resolves the
object's name address from the per-object `*_nameadr` arrays and the `names`
buffer.

Authoritative upstream references for the pinned release:

* [`mjModel` reference](https://mujoco.readthedocs.io/en/3.2.7/APIreference/APItypes.html#mjmodel)
  (`nnames`, `nnames_map`, `names`, and `names_map` fields).
* [`engine_name.c` at the 3.2.7 tag](https://github.com/google-deepmind/mujoco/blob/3.2.7/src/engine/engine_name.c)
  (name-map construction and the `mj_name2id`/`mj_id2name` lookup paths).

Thus the integers in `names_map` are hash-table/index layout, not model
parameters.  They are a derived representation of names already stored in the
compiled model.

## Why equivalent constructions can differ

The runtime attaches the fly through dm_control.  Fresh attachment instances
can qualify compiled names with different per-instance prefixes.  Hash slots
are selected from the exact compiled strings, so different prefixes produce a
different integer table (and can produce a different collision/probing layout)
even when the normalized object names, object ordering, and every physical
parameter are the same.  This does not claim that MuJoCo randomly maps an
identical byte-for-byte name table: it explains why independently constructed,
scientifically equivalent dm_control models need not have identical map bytes.

## Dynamics relevance and exclusion decision

`names_map` is consumed by name-to-ID lookup; it is not an input to MuJoCo's
kinematics, mass/inertia assembly, collision detection, constraint solving,
integration, actuation, or sensor calculations.  Its only semantic effect is
whether a textual name resolves to the intended already-compiled object ID.
The experiment's dynamics-relevant compiled numeric arrays remain in the
identity, as do dimensions, `model.opt`, and initial `qpos`, `qvel`, `act`, and
`ctrl`.

The identity also independently records ordered, namespace-normalized
inventories for every compiled **body, joint, geom, actuator, sensor, and
site**.  A rename, removal, addition, or reorder in any of those scientific
inventories therefore changes identity without relying on hash-table layout.
The experiment resolves and validates its named interface against those
compiled objects before execution.  Given those safeguards, omitting only
`model_arrays.names_map` cannot hide a change capable of affecting dynamics;
it can only ignore a different acceleration-table representation of names.

The exclusion is consequently scientifically justified and deliberately
narrow: `names_map` alone is omitted from `physics_model_identity`.  It remains
present as raw data in the recursive diagnostic snapshot, although the snapshot
comparison applies the same sole exclusion so equivalent constructions report
`differences = []`.  No category of name-related arrays, integer arrays, or
internal-looking arrays is excluded.

## LegendaryPC verification (no scientific execution)

From the repository root, run the focused regression suite first:

```powershell
python -m pytest tests/test_candidate_motor_channel_experiment.py -q
```

Then run the zero-transition diagnostic:

```powershell
python -m malecns_backend.embodiment.candidate_motor_channel_experiment --diagnose-identity
```

All A1/A2/B1/B2 comparisons must be identical, have equal aggregate hashes,
and report `differences = []`.  Any remaining difference is a stop condition.
Neither command creates `attempt_004` or authorizes scientific execution.
