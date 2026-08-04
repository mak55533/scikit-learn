#!/usr/bin/env python3
"""diff_manifest.py — build DIFF_MANIFEST.md and per-file hunk diffs.

Deterministic. No agents. Given a git repo, a BASE sha and a HEAD sha, emit:

  * <out>/DIFF_MANIFEST.md : one line per changed file (A/M/D/R status + +/- line
    counts, from `git diff --name-status` and `--numstat`), grouped by top-level
    directory, with a total header.
  * <worktree>/hunks/<path-with-slashes-as-underscores>.diff : the exact hunk
    diff for each changed file (`git diff BASE HEAD -- <file>`), so seats can see
    deletions too.

Usage:
  diff_manifest.py --repo REPO --base BASE --head HEAD --out OUTDIR --hunks HUNKDIR
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_name_status(text: str) -> list[tuple[str, str, str]]:
    """Return list of (status, path, orig_path). orig_path only for renames."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            # R100\told\tnew
            orig, path = parts[1], parts[2]
            rows.append((status[0], path, orig))
        else:
            rows.append((status[0], parts[1], ""))
    return rows


def parse_numstat(text: str) -> dict[str, tuple[str, str]]:
    """path -> (added, deleted). '-' for binary."""
    stats: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        # renames render as "old => new" or {a => b}; the last path token wins,
        # but numstat already gives the new path when using default format.
        stats[path] = (added, deleted)
    return stats


def top_dir(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--out", required=True, help="dir to write DIFF_MANIFEST.md")
    ap.add_argument("--hunks", required=True, help="dir to write per-file .diff")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    hunks = Path(args.hunks).resolve()
    out.mkdir(parents=True, exist_ok=True)
    hunks.mkdir(parents=True, exist_ok=True)

    name_status = parse_name_status(
        git(repo, "diff", "--name-status", "-M", args.base, args.head)
    )
    numstat = parse_numstat(git(repo, "diff", "--numstat", args.base, args.head))

    total_add = total_del = 0
    grouped: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for status, path, orig in name_status:
        added, deleted = numstat.get(path, ("0", "0"))
        if added.isdigit():
            total_add += int(added)
        if deleted.isdigit():
            total_del += int(deleted)
        label = path if not orig else f"{orig} -> {path}"
        grouped[top_dir(path)].append((status, label, added, deleted))

        # write hunk diff for this file
        safe = path.replace("/", "_")
        diff_text = git(repo, "diff", args.base, args.head, "--", path)
        (hunks / f"{safe}.diff").write_text(diff_text)

    lines: list[str] = []
    lines.append("# DIFF_MANIFEST")
    lines.append("")
    lines.append(f"- base: `{args.base}`")
    lines.append(f"- head: `{args.head}`")
    lines.append(
        f"- files changed: {len(name_status)} | +{total_add} / -{total_del}"
    )
    lines.append(
        "- status legend: A=added M=modified D=deleted R=renamed C=copied"
    )
    lines.append(
        "- hunks: per-file diff at `hunks/<path-with-slashes-as-underscores>.diff`"
    )
    lines.append("")
    for group in sorted(grouped):
        lines.append(f"## {group}/")
        lines.append("")
        lines.append("| status | file | +added | -deleted |")
        lines.append("| --- | --- | --- | --- |")
        for status, label, added, deleted in sorted(grouped[group], key=lambda r: r[1]):
            lines.append(f"| {status} | `{label}` | {added} | {deleted} |")
        lines.append("")

    (out / "DIFF_MANIFEST.md").write_text("\n".join(lines) + "\n")
    print(
        f"wrote {out / 'DIFF_MANIFEST.md'} ({len(name_status)} files, "
        f"+{total_add}/-{total_del}); hunks in {hunks}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
