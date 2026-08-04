# Stage 3 — DEPTH (single agent, ADD-ONLY)

You are given all merged findings files (`merged/<theme>.md`). Re-read every
**medium** and **high** finding against the actual worktree tree and STRENGTHEN
them — but **ADD-ONLY**.

You MAY:
- Append **extra `instances:`** anchors you can verify for an existing finding
  (add a new finding block that references the same defect with the additional
  sites, tagged `depth-extra-instances` in the title).
- Append **sibling defects** you discover while re-reading (same class of bug at
  a nearby site).
- Append **harder evidence** as a new block that cites more precise file:line.

You MUST NOT:
- Rewrite, reword, re-rank, soften, or remove any existing finding.
- Change any existing block's text in any way.

Output `depth.md` containing ONLY the NEW blocks you are appending (same finding
format, numbered F1..). If you have nothing to add, write `NO FINDINGS`.

The existing merged findings are preserved byte-identical elsewhere; a
snapshot-diff will verify they were untouched, so do not restate them.

Write ONLY to your designated output file.
