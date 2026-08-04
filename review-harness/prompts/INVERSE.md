# Stage 5 — INVERSE (single agent, two inventories)

Build two inventories from `PLAN.md` and `DIFF_MANIFEST.md` (+ the worktree):

1. **Plan requirements** — every discrete requirement/promise the PR description
   and linked issue make (new estimator, specific parameters, specific
   behaviors, docs, tests, API surface, deprecations, etc.).
2. **Actual changes** — every changed file / significant change from the
   manifest.

Then emit findings for the mismatches:
- **Requirement with no implementing change** — the plan promises X but nothing
  in the diff implements X.
- **Change with no sanctioning requirement** — a change exists that no part of
  the plan asks for (possible scope creep / stray edit).
- **Manifest file nobody accounted for** — a changed file that neither a
  requirement nor a prior finding explains.

Use the standard finding format. For a requirement gap, `evidence:` cites the
PLAN.md line and the absence; for scope creep, cite the changed file:line.
Output `inverse.md`; `NO FINDINGS` if the two inventories fully reconcile.

Write ONLY to your designated output file.
