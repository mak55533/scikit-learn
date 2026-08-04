#!/usr/bin/env python3
"""contract_lint.py — deterministic linter over a findings markdown file.

A findings file is a sequence of blocks in the canonical format:

  ### F<N> — <one-line title>
  severity: high|medium|low
  evidence: <file>:<line-range> — <what is there>
  scenario: "<trigger> -> <consequence>"
  contract: <the single pinned recommendation>
  instances: [<file:line>, ...] | single-instance

Rules enforced (per finding block):
  1. Has an `instances:` line: either `instances: [file:line, ...]` (each token
     matches a file:line shape) or `instances: single-instance`.
  2. Has a `scenario: "..."` line — a quoted trigger -> consequence sentence.
  3. No hedged contract: the `contract:` line must not contain permissive-
     alternative hedges ("or alternatively", "whichever", "and/or",
     "either ... or", "consider possibly", ...). One pinned recommendation.
  4. Has a `severity:` line with a valid level.
  5. Cites at least one `file:line` evidence anchor on the `evidence:` line.

Exit 0 if clean; exit 2 listing violations otherwise. A file that legitimately
contains NO findings (only the sentinel `NO FINDINGS`) is clean.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SEVERITIES = {"high", "medium", "low"}

# file:line or file:line-line anchor, e.g. sklearn/cluster/_hdbscan/hdbscan.py:123
FILE_LINE = re.compile(r"[\w./\-]+\.\w+:\d+(?:-\d+)?")

# hedge patterns that leave a path where the defect survives
HEDGE_PATTERNS = [
    r"\bor alternatively\b",
    r"\bwhichever\b",
    r"\band/or\b",
    r"\beither\b.*\bor\b",
    r"\bconsider (?:possibly|maybe)\b",
    r"\bmight want to\b",
    r"\bperhaps\b",
    r"\bif you (?:prefer|want)\b",
]
HEDGE_RE = re.compile("|".join(HEDGE_PATTERNS), re.IGNORECASE)

HEADER_RE = re.compile(r"^#{2,4}\s*F\d+\b")


def split_blocks(text: str) -> list[tuple[int, list[str]]]:
    """Split into finding blocks. Returns (start_line_no, lines) per block."""
    lines = text.splitlines()
    blocks: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start = 0
    for i, line in enumerate(lines):
        if HEADER_RE.match(line.strip()):
            if current:
                blocks.append((start, current))
            current = [line]
            start = i + 1
        elif current:
            current.append(line)
    if current:
        blocks.append((start, current))
    return blocks


def field(block: list[str], name: str) -> str | None:
    prefix = f"{name}:"
    for line in block:
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            return stripped[len(prefix):].strip()
    return None


def lint_block(start: int, block: list[str]) -> list[str]:
    title = block[0].strip()
    errs: list[str] = []

    def err(msg: str) -> None:
        errs.append(f"[block @line {start}: {title[:60]}] {msg}")

    severity = field(block, "severity")
    if severity is None:
        err("missing `severity:` line")
    elif severity.lower() not in SEVERITIES:
        err(f"invalid severity {severity!r} (want high|medium|low)")

    evidence = field(block, "evidence")
    if evidence is None:
        err("missing `evidence:` line")
    elif not FILE_LINE.search(evidence):
        err("evidence has no file:line anchor")

    scenario = field(block, "scenario")
    if scenario is None:
        err("missing `scenario:` line")
    else:
        if not (scenario.startswith('"') and scenario.rstrip().endswith('"')):
            err("scenario must be a quoted \"...\" sentence")
        inner = scenario.strip('"').strip()
        if len(inner) < 8:
            err("scenario too short to be a trigger -> consequence sentence")

    contract = field(block, "contract")
    if contract is None:
        err("missing `contract:` line")
    else:
        hedge = HEDGE_RE.search(contract)
        if hedge:
            err(f"hedged contract (matched {hedge.group(0)!r}); pin one recommendation")

    instances = field(block, "instances")
    if instances is None:
        err("missing `instances:` line")
    else:
        val = instances.strip()
        if val == "single-instance":
            pass
        elif val.startswith("[") and val.endswith("]"):
            body = val[1:-1].strip()
            if not body:
                err("instances list is empty (use single-instance instead)")
            else:
                for tok in [t.strip() for t in body.split(",") if t.strip()]:
                    if not FILE_LINE.fullmatch(tok):
                        err(f"instances token {tok!r} is not a file:line anchor")
        else:
            err("instances must be `[file:line, ...]` or `single-instance`")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("findings_file")
    args = ap.parse_args()

    path = Path(args.findings_file)
    if not path.exists():
        print(f"contract_lint: file not found: {path}", file=sys.stderr)
        return 2
    text = path.read_text()

    blocks = split_blocks(text)
    if not blocks:
        # allow an explicit "no findings" sentinel
        if re.search(r"\bNO FINDINGS\b", text, re.IGNORECASE):
            print(f"contract_lint OK: {path} (0 findings, sentinel present)")
            return 0
        print(
            f"contract_lint FAIL: {path} has no F<N> finding blocks and no "
            f"`NO FINDINGS` sentinel",
            file=sys.stderr,
        )
        return 2

    all_errs: list[str] = []
    for start, block in blocks:
        all_errs.extend(lint_block(start, block))

    if all_errs:
        print(f"contract_lint FAIL: {path} ({len(all_errs)} violations)", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        return 2

    print(f"contract_lint OK: {path} ({len(blocks)} findings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
