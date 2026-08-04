# Cloud orchestrator seat — run the full fan-out review with NATIVE Agent subagents

You are a Claude Code agent running in a cloud container on a checkout of this
scikit-learn fork. **You are the OVERSEEING ORCHESTRATOR** for a fan-out code
review of merged PR scikit-learn/scikit-learn#26385 ("ENH Add HDBSCAN").

## Absolute execution rule (highest priority)
Launch EVERY reviewer/merge/depth/closure/inverse/synthesis seat as a **native
Claude Code subagent via the `Agent` tool** (subagent_type "general-purpose").
Do NOT run seats through Bash, `claude -p`, `claude-go-brr`, `codex`, or any CLI
or nested offload. Deterministic bookkeeping (linting, file assembly, marker
files) you may do yourself with Bash/Read/Write. For parallel stages, issue
multiple `Agent` calls in a SINGLE message so they run concurrently (up to 12).
Wait for every Agent in a wave before starting the next stage.

Use one model at its highest reasoning setting for all seats; do not mix models.

## Inputs (all committed in this checkout, paths relative to repo root)
- `review-harness/runs/26385/PLAN.md`             — plan of record
- `review-harness/runs/26385/DIFF_MANIFEST.md`    — 19 changed files, +/- counts
- `review-harness/runs/26385/hunks/*.diff`         — exact per-file changes
- `review-harness/runs/26385/head_files/<path>`    — full PR-head version of each
  changed file (verify every claim here; the live tree has since evolved — do
  NOT review the live tree, only these snapshots)
- `review-harness/runs/26385/cloud_prompts/<theme>.txt` — the ready-made per-theme
  reviewer charter (theme lens + base charter). Twelve themes:
  logic-and-correctness, security-and-boundaries,
  concurrency-async-and-error-paths, tests-and-verification,
  type-and-interface-contracts, duplication-and-single-sourcing,
  dead-code-and-change-hygiene, readability-and-abstraction, docs-and-comments,
  data-access-and-performance, module-boundaries-and-placement,
  build-config-and-operational-wiring
- `review-harness/contract_lint.py`, `review-harness/fidelity_audit.py` — run
  these with `python3` to validate seat outputs.

## Pipeline to run (write ALL outputs under review-harness/runs/26385/)

### Stage 1 — DRAW A: 12 reviewer seats (native Agent, up to 12 concurrent)
For each theme, launch a native Agent whose prompt is:
"You are seat draw-a/<theme>. Read review-harness/runs/26385/cloud_prompts/<theme>.txt
and follow it EXACTLY. Write your findings to
review-harness/runs/26385/draws_a/<theme>.md and nothing else. Do not create
subagents. Return a one-line status." 
After the wave, run `python3 review-harness/contract_lint.py` on each
draws_a/<theme>.md. If any fails, relaunch a fresh native Agent for that seat
with the concrete lint errors appended; max 3 retries per seat.

### Stage 1b — DRAW B, Stage 1c — DRAW C
Repeat Stage 1 into draws_b/ and draws_c/. These are independent, mutually-blind
redundant draws — do NOT let a later draw read earlier draws. Same lint loop.
(If container time is tight you may run k=2 draws instead of 3; note it in the
report. Prefer k=3.)

### Stage 2 — MERGE: 12 native Agent seats, one per theme (concurrent)
Each merge seat reads draws_a/<theme>.md, draws_b/<theme>.md, draws_c/<theme>.md
and the file review-harness/prompts/MERGE.md, and writes the UNION to
merged/<theme>.md (never drop a finding; keep most-specific wording verbatim;
merge instances lists). Lint each; revise-loop until clean (max 3).

### Stage 3 — DEPTH (1 native Agent)
Per review-harness/prompts/DEPTH.md: re-read every medium/high merged finding,
ADD-ONLY strengthening → depth.md. Must not alter existing findings.

### Stage 4 — CLOSURE (1 native Agent)
Per review-harness/prompts/CLOSURE.md: sweep each finding's implied RULE across
the FULL manifest → closure.md.

### Stage 5 — INVERSE (1 native Agent)
Per review-harness/prompts/INVERSE.md: plan-requirements vs actual-changes
inventories; emit mismatch findings → inverse.md.

### Stage 6 — SYNTHESIS (1 native Agent)
Per review-harness/prompts/SYNTHESIS.md: SELECT findings verbatim (dedup + group
by severity) → report.md, findings.json, synthesis_ledger.json.

### Stage 7 — FIDELITY AUDIT (you, deterministic — no agent)
Run:
`python3 review-harness/fidelity_audit.py --inputs review-harness/runs/26385/merged/*.md review-harness/runs/26385/depth.md review-harness/runs/26385/closure.md review-harness/runs/26385/inverse.md --ledger review-harness/runs/26385/synthesis_ledger.json --delivered review-harness/runs/26385/findings.json`
If it fails, relaunch the synthesis Agent with the concrete MISSING_IDS /
violations; loop until clean (max 3).

### Stage 8 — DELIVER
report.md (counts by severity; each finding human-first with the verbatim block
in a collapsed <details>) and findings.json are the deliverables. Also write
review-harness/runs/26385/RUN_NOTES.md: findings counts by severity, top 5
findings one line each, per-stage seat counts, and anything that misbehaved.

## Completion
Do not stop after starting a wave — keep launching, waiting, validating,
retrying, and advancing until Stage 8 is done. Your changes are returned as a
git patch; make sure every runs/26385/ output file is written before you finish.
Return a short final status summarizing counts by severity and the top findings.
