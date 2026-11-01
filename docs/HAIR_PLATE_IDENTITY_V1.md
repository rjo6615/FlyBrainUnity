# Hair-plate Step A — CxHP8 identity check (V1)

Preregistered 2026-11-01 (`evidence/hair-plate-identity-v1/protocol.json`, SHA-256 locked
in `malecns_backend/embodiment/hair_plate_identity.py`). Connectivity only.

Question: do SNpp45 hair plates in our connectome show the published CxHP8 output
pattern (Nature Communications 2026; FANC reconstruction): strongest direct input to
posterior-moving coxa motor neurons and net inhibition of forward-moving ones? T1 uses
SNpp45 entering via VProN (the reference's CxHP8 identifier); T2/T3 use the serial
SNpp45 copies in the leg nerves.

Posterior set = Pleural remotor/abductor + Sternal posterior rotator MN; anterior set =
Tergopleural/Pleural promotor (T1 only) + Sternal anterior rotator MN (a declared
mapping of the reference's modules). A leg matches if posterior direct synapses exceed
anterior, the single most-targeted MN population is posterior, and the net signed
two-hop drive to the anterior set is negative. Verdict MATCH_ALL / FRONT_ONLY /
SERIAL_ONLY / NO_MATCH, with Step B's scope declared in advance for each.
Results: `HAIR_PLATE_IDENTITY_RESULTS.md`.
