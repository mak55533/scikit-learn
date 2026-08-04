#!/usr/bin/env python3
"""fidelity_audit.py — stage-7 auditors over synthesis output. No agents.

Two checks that prevent the compressing synthesis step from silently dropping
findings:

  (a) FIDELITY: every input finding id (collected from the union/merge inputs
      plus depth/closure/inverse) appears in synthesis_ledger.json with a valid
      disposition. Valid dispositions:
        - kept-as: <delivered-id>
        - merged-into: <delivered-id>
        - duplicate-of: <input-or-delivered-id>
  (b) PRESERVATION: kept-ratio floor (delivered units / unioned findings >=
      FLOOR, default 0.60); no merge group larger than MAX_GROUP (default 6);
      every delivered unit carries at least one evidence anchor.

On failure exits 3 and prints the missing ids / violations so the runner can
re-prompt synthesis with exactly those ids.

Inputs are discovered structurally:
  --inputs   one or more findings .md files (merged/*.md, closure.md, inverse.md,
             depth additions) whose F<N> ids form the "must be accounted for" set
  --ledger   synthesis_ledger.json
  --delivered findings.json (array of delivered units with id + body/evidence)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEADER_RE = re.compile(r"^#{2,4}\s*(F\d+)\b")
FILE_LINE = re.compile(r"[\w./\-]+\.\w+:\d+(?:-\d+)?")
VALID_DISPOSITIONS = {"kept-as", "merged-into", "duplicate-of"}


def collect_input_ids(paths: list[Path]) -> dict[str, str]:
    """Return {qualified_id: source} for every F<N> across input files.

    Ids are namespaced by filename stem so F1 in merged/logic and F1 in
    inverse.md don't collide: e.g. "logic-and-correctness:F1".
    """
    ids: dict[str, str] = {}
    for p in paths:
        if not p.exists():
            continue
        stem = p.stem
        for line in p.read_text().splitlines():
            m = HEADER_RE.match(line.strip())
            if m:
                ids[f"{stem}:{m.group(1)}"] = str(p)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--delivered", required=True)
    ap.add_argument("--floor", type=float, default=0.60)
    ap.add_argument("--max-group", type=int, default=6)
    args = ap.parse_args()

    input_ids = collect_input_ids([Path(p) for p in args.inputs])
    total_input = len(input_ids)

    ledger_path = Path(args.ledger)
    delivered_path = Path(args.delivered)

    problems: list[str] = []

    if not ledger_path.exists():
        print(f"fidelity_audit FAIL: ledger missing: {ledger_path}", file=sys.stderr)
        return 3
    if not delivered_path.exists():
        print(f"fidelity_audit FAIL: delivered missing: {delivered_path}", file=sys.stderr)
        return 3

    try:
        ledger = json.loads(ledger_path.read_text())
    except json.JSONDecodeError as e:
        print(f"fidelity_audit FAIL: ledger is not valid JSON: {e}", file=sys.stderr)
        return 3
    try:
        delivered = json.loads(delivered_path.read_text())
    except json.JSONDecodeError as e:
        print(f"fidelity_audit FAIL: delivered is not valid JSON: {e}", file=sys.stderr)
        return 3

    # Ledger may be either {"entries": [...]} or a flat list, or a dict mapping
    # id -> disposition string/obj. Normalize to {input_id: (disposition, target)}.
    ledger_map: dict[str, tuple[str, str]] = {}
    entries = ledger.get("entries", ledger) if isinstance(ledger, dict) else ledger
    if isinstance(entries, dict):
        iterable = entries.items()
    else:
        iterable = [
            (e.get("id"), e) for e in entries if isinstance(e, dict)
        ]
    for key, val in iterable:
        if isinstance(val, str):
            disp, _, target = val.partition(":")
            ledger_map[key] = (disp.strip(), target.strip())
        elif isinstance(val, dict):
            disp = val.get("disposition", "")
            target = val.get("target", "") or val.get("kept_as", "") or val.get("into", "")
            ledger_map[key] = (str(disp).strip(), str(target).strip())

    # (a) FIDELITY: every input id accounted for with a valid disposition
    missing = []
    bad_disp = []
    for qid in input_ids:
        if qid not in ledger_map:
            # tolerate un-namespaced ids (e.g. "F1") if unique
            bare = qid.split(":", 1)[1]
            if bare in ledger_map:
                disp = ledger_map[bare][0]
            else:
                missing.append(qid)
                continue
        else:
            disp = ledger_map[qid][0]
        if disp not in VALID_DISPOSITIONS:
            bad_disp.append(f"{qid} -> {disp!r}")

    if missing:
        problems.append(
            f"FIDELITY: {len(missing)} input finding id(s) missing from ledger: "
            + ", ".join(sorted(missing))
        )
    if bad_disp:
        problems.append(
            f"FIDELITY: invalid disposition(s): " + ", ".join(sorted(bad_disp))
        )

    # (b) PRESERVATION
    if not isinstance(delivered, list):
        problems.append("PRESERVATION: delivered findings.json must be a JSON array")
        delivered = []

    n_delivered = len(delivered)
    if total_input > 0:
        ratio = n_delivered / total_input
        if ratio < args.floor:
            problems.append(
                f"PRESERVATION: kept-ratio {ratio:.2f} below floor {args.floor:.2f} "
                f"({n_delivered} delivered / {total_input} unioned)"
            )

    # merge-group sizes: count how many input ids map merged-into each target
    group_sizes: dict[str, int] = {}
    for qid, (disp, target) in ledger_map.items():
        if disp == "merged-into" and target:
            group_sizes[target] = group_sizes.get(target, 0) + 1
    big = {t: n for t, n in group_sizes.items() if n > args.max_group}
    if big:
        problems.append(
            "PRESERVATION: merge group(s) larger than "
            f"{args.max_group}: "
            + ", ".join(f"{t}={n}" for t, n in sorted(big.items()))
        )

    # every delivered unit carries an evidence anchor
    no_evidence = []
    for unit in delivered:
        if not isinstance(unit, dict):
            continue
        blob = " ".join(
            str(unit.get(k, "")) for k in ("evidence", "body", "instances", "file", "line")
        )
        if not FILE_LINE.search(blob):
            no_evidence.append(unit.get("id", "<no id>"))
    if no_evidence:
        problems.append(
            "PRESERVATION: delivered unit(s) with no file:line evidence: "
            + ", ".join(str(x) for x in no_evidence)
        )

    if problems:
        print(f"fidelity_audit FAIL ({len(problems)} problem group(s)):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        # emit the concrete missing ids for the synthesis re-prompt
        if missing:
            print("MISSING_IDS=" + ",".join(sorted(missing)), file=sys.stderr)
        return 3

    print(
        f"fidelity_audit OK: {total_input} input ids all accounted for; "
        f"{n_delivered} delivered units; kept-ratio "
        f"{(n_delivered / total_input) if total_input else 1.0:.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
