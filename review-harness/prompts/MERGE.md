# Stage 2 — UNION MERGE (one agent per theme)

You are the merge agent for a SINGLE theme. You are given three independent
reviewer draws for that theme:
  - `draws_a/<theme>.md`
  - `draws_b/<theme>.md`
  - `draws_c/<theme>.md`

Produce `merged/<theme>.md`: the **UNION** of all findings across the three
draws. This is a union, NOT a summary.

## Hard rules
- **Never drop a finding.** Every distinct defect reported by any draw must
  appear in the output.
- When two or more draws report the **same defect**, keep the **most specific
  version VERBATIM** (the one with the tightest evidence / clearest scenario)
  and **merge their `instances:` lists** (union of file:line anchors, deduped).
  Do not paraphrase or "improve" the kept wording.
- Do NOT editorialize, re-rank, soften, or decide something is "too minor".
  Minor findings survive the merge.
- Preserve the exact finding block format. Renumber sequentially F1, F2, ...
  across the merged file.
- If a draw contains only `NO FINDINGS`, it contributes nothing; if ALL three
  are `NO FINDINGS`, write the single line `NO FINDINGS`.

## Output format (unchanged from the seat format)
```
### F<N> — <one-line title>
severity: high|medium|low
evidence: <file>:<line-range> — <what is there>
scenario: "<trigger> → <consequence>"
contract: <single pinned recommendation>
instances: [<file:line>, ...] | single-instance
```

The output must pass a deterministic contract linter: every block needs a valid
`severity:`, an `evidence:` with a file:line anchor, a quoted `scenario:`, a
non-hedged `contract:`, and an `instances:` line. If you are told your output
failed the linter, fix exactly the listed violations and rewrite the file.

Write ONLY to your designated output file.
