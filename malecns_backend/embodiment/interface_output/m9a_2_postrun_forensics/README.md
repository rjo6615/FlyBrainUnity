# M9A-2 post-run forensics

This directory is exclusively for derived, read-only forensic output from
`malecns_backend.embodiment.m9a_2_postrun_forensics`. The tool refuses partial
analysis unless all eight canonical candidate NPZs are present, hashes every
input before parsing and again afterward, imports no simulation or neural
runtime, and writes a report with exclusive-create semantics.

The current Linux checkout contains the four immutable Attempt 1 files but not
the four Windows M9A-2 raw files. Consequently no result JSON is committed:
claiming exact eight-file findings here would fabricate missing evidence. Copy
the four canonical Windows NPZs into the already-established M9A-2 evidence
directory and run `python -m malecns_backend.embodiment.m9a_2_postrun_forensics
--write-report` in the pinned analysis environment. This performs zero physics
or neural transitions.

Report creation occurs only after `analyze()` returns successfully. Therefore
the Boolean-comparison failure on the desktop cannot create a partial report:
exclusive creation is never entered on that failing path. This checkout also
contains no report JSON. Do not delete anything automatically if a future
operator encounters an existing report.
