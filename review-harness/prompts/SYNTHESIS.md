# Stage 6 — SYNTHESIS (single agent, SELECT verbatim, prove preservation)

You are given every upstream findings file: `merged/<theme>.md` (12 files),
`depth.md`, `closure.md`, `inverse.md`. Each finding block has an id `F<N>`;
qualify it by its source file stem (e.g. `logic-and-correctness:F3`,
`inverse:F1`).

Assemble the final deliverables by **SELECTING findings verbatim** — you compress
by DEDUPLICATING identical findings and GROUPING, never by rewriting or
discarding signal.

## Produce three files

### 1. `report.md`
- A header with **counts by severity** (high/medium/low totals).
- Then findings grouped by severity (high, then medium, then low). Each finding
  rendered **human-first**:
  - a severity-prefixed one-line title,
  - 2–4 plain-English sentences explaining the defect and its consequence,
  - beneath, a `<details>` collapsed section containing the **verbatim** finding
    block (the exact evidence/scenario/contract/instances).

### 2. `findings.json`
A JSON array. Each element:
```json
{"id": "...", "severity": "high|medium|low", "title": "...",
 "file": "...", "line": "...", "scenario": "...", "contract": "...",
 "instances": ["file:line", ...], "body": "<verbatim finding block>"}
```
Every delivered unit MUST carry a file:line anchor (in file/line/instances/body).

### 3. `synthesis_ledger.json`
This PROVES you kept everything. A JSON object mapping **every input finding id**
(qualified) to its disposition:
```json
{"entries": {
  "logic-and-correctness:F1": {"disposition": "kept-as", "target": "H1"},
  "logic-and-correctness:F2": {"disposition": "merged-into", "target": "H1"},
  "duplication-and-single-sourcing:F1": {"disposition": "duplicate-of", "target": "logic-and-correctness:F1"}
}}
```
Valid dispositions: `kept-as`, `merged-into`, `duplicate-of`. EVERY input id
must appear exactly once. A downstream auditor will fail the run if any input id
is missing or a merge group exceeds 6 members or the kept-ratio floor (60% of
unioned findings surviving as delivered units) is violated — so do NOT
over-merge. When in doubt, keep a finding as its own delivered unit.

If told specific ids are MISSING from the ledger, add exactly those and rewrite.

Write ONLY the three designated output files.
