# Stage 4 — CLOSURE (single agent, rule sweep)

You are given all findings so far (`merged/<theme>.md` and `depth.md`) plus
`DIFF_MANIFEST.md` and the worktree.

Each finding implicitly asserts a **RULE** ("array indices must be bounds
checked", "every public estimator must be exported from the package namespace",
"docstring params must match the signature", etc.). Your job:

1. Extract the rule behind each existing finding.
2. Sweep that rule across the **FULL manifest** — including files that no
   finding has touched yet.
3. For every NEW occurrence of a rule violation you can verify in the tree, emit
   a finding (same format). These are genuinely new sites, not restatements of
   the finding that implied the rule.

Do not restate existing findings. Only emit newly-discovered occurrences.

Output `closure.md` in the finding format; `NO FINDINGS` if the sweep surfaces
nothing new. Write ONLY to your designated output file.
