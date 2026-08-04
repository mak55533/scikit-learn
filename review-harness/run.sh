#!/usr/bin/env bash
#
# run.sh — deterministic state/checkpoint helper for the fan-out review harness.
#
# *** THIS SCRIPT NEVER LAUNCHES AN AGENT. ***
# Per review-harness/ORCHESTRATOR.md, the overseeing Claude Code session launches
# every reviewer/merge/depth/closure/inverse/synthesis seat with the native
# `Agent` tool. This script only:
#   - prepares inputs (PLAN.md, manifest, hunks, prompt assembly, dirs)
#   - reports the pending seats for a stage
#   - validates expected outputs and runs the contract / fidelity linters
#   - writes completion markers (only after validation)
#   - reports which stage should run next
#
# Subcommands:
#   run.sh stage0 --repo R --worktree W --base B --head H --pr N   prepare inputs
#   run.sh seat-prompt <stage> <name>                              print a seat prompt
#   run.sh pending <stage>                                         list pending seats
#   run.sh validate <stage>                                        validate + lint + mark
#   run.sh next                                                    report next stage
#   run.sh status                                                  overall run status
#
set -Eeuo pipefail

HARNESS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROMPTS="$HARNESS_DIR/prompts"
PR="${PR:-26385}"
RUN_DIR="${RUN_DIR:-$HARNESS_DIR/runs/$PR}"
MARKERS="$RUN_DIR/markers"
PY="${PYTHON:-python3}"

THEMES=(
  logic-and-correctness
  security-and-boundaries
  concurrency-async-and-error-paths
  tests-and-verification
  type-and-interface-contracts
  duplication-and-single-sourcing
  dead-code-and-change-hygiene
  readability-and-abstraction
  docs-and-comments
  data-access-and-performance
  module-boundaries-and-placement
  build-config-and-operational-wiring
)

log() { printf '%s\n' "$*" >&2; }
mark() { mkdir -p "$MARKERS"; : > "$MARKERS/$1"; }
is_marked() { [[ -f "$MARKERS/$1" ]]; }

theme_charter() {
  "$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
    "$PROMPTS/themes.json" "$1"
}

# ---- stage 0: prepare inputs --------------------------------------------------
cmd_stage0() {
  local repo worktree base head
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo) repo="$2"; shift 2;;
      --worktree) worktree="$2"; shift 2;;
      --base) base="$2"; shift 2;;
      --head) head="$2"; shift 2;;
      --pr) PR="$2"; RUN_DIR="$HARNESS_DIR/runs/$PR"; MARKERS="$RUN_DIR/markers"; shift 2;;
      *) log "unknown flag $1"; exit 64;;
    esac
  done
  mkdir -p "$RUN_DIR" "$MARKERS" "$RUN_DIR/draws_a" "$RUN_DIR/draws_b" \
    "$RUN_DIR/draws_c" "$RUN_DIR/merged"
  echo "base=$base" > "$RUN_DIR/RUN_CONFIG"
  echo "head=$head" >> "$RUN_DIR/RUN_CONFIG"
  echo "repo=$repo" >> "$RUN_DIR/RUN_CONFIG"
  echo "worktree=$worktree" >> "$RUN_DIR/RUN_CONFIG"
  echo "pr=$PR" >> "$RUN_DIR/RUN_CONFIG"

  # manifest + hunks (hunks live in the worktree so seats see them)
  "$PY" "$HARNESS_DIR/diff_manifest.py" \
    --repo "$repo" --base "$base" --head "$head" \
    --out "$RUN_DIR" --hunks "$worktree/hunks"
  cp "$RUN_DIR/DIFF_MANIFEST.md" "$worktree/DIFF_MANIFEST.md"
  [[ -f "$RUN_DIR/PLAN.md" ]] && cp "$RUN_DIR/PLAN.md" "$worktree/PLAN.md" || true
  mark stage0
  log "stage0 complete: manifest + hunks ready in $worktree"
}

# ---- assemble a seat prompt (printed, not executed) ---------------------------
cmd_seat_prompt() {
  local stage="$1" name="$2"
  case "$stage" in
    draw-a|draw-b|draw-c)
      local letter="${stage#draw-}"
      echo "SEAT IDENTITY: draw-${letter}/${name}"
      echo
      echo "You are running in the review worktree (cwd). Read only: PLAN.md,"
      echo "DIFF_MANIFEST.md, hunks/*.diff, and the changed source files. Do NOT"
      echo "create subagents. Write EXACTLY one file:"
      echo "  runs/$PR/draws_${letter}/${name}.md"
      echo "Return a one-line completion status after writing it."
      echo
      theme_charter "$name"
      echo
      cat "$PROMPTS/BASE_CHARTER.md"
      ;;
    merge)
      echo "SEAT IDENTITY: merge/${name}"
      echo "Inputs: runs/$PR/draws_{a,b,c}/${name}.md"
      echo "Output EXACTLY: runs/$PR/merged/${name}.md"
      echo "Do NOT create subagents. Return a one-line status."
      echo
      cat "$PROMPTS/MERGE.md"
      ;;
    depth)   echo "SEAT IDENTITY: depth/all"; echo "Output EXACTLY: runs/$PR/depth.md"; echo; cat "$PROMPTS/DEPTH.md";;
    closure) echo "SEAT IDENTITY: closure/all"; echo "Output EXACTLY: runs/$PR/closure.md"; echo; cat "$PROMPTS/CLOSURE.md";;
    inverse) echo "SEAT IDENTITY: inverse/all"; echo "Output EXACTLY: runs/$PR/inverse.md"; echo; cat "$PROMPTS/INVERSE.md";;
    synthesis)
      echo "SEAT IDENTITY: synthesis/all"
      echo "Outputs EXACTLY: runs/$PR/report.md, runs/$PR/findings.json, runs/$PR/synthesis_ledger.json"
      echo; cat "$PROMPTS/SYNTHESIS.md";;
    *) log "unknown stage $stage"; exit 64;;
  esac
}

# ---- pending seats for a stage ------------------------------------------------
cmd_pending() {
  local stage="$1" letter subdir
  case "$stage" in
    draw-a|draw-b|draw-c)
      letter="${stage#draw-}"; subdir="draws_${letter}"
      for t in "${THEMES[@]}"; do
        if is_marked "${stage}.${t}" && [[ -s "$RUN_DIR/$subdir/$t.md" ]]; then :; else echo "$t"; fi
      done
      ;;
    merge)
      for t in "${THEMES[@]}"; do
        if is_marked "merge.${t}" && [[ -s "$RUN_DIR/merged/$t.md" ]]; then :; else echo "$t"; fi
      done
      ;;
    depth)     is_marked depth     && [[ -s "$RUN_DIR/depth.md" ]]     || echo all;;
    closure)   is_marked closure   && [[ -s "$RUN_DIR/closure.md" ]]   || echo all;;
    inverse)   is_marked inverse   && [[ -s "$RUN_DIR/inverse.md" ]]   || echo all;;
    synthesis) is_marked synthesis && [[ -s "$RUN_DIR/findings.json" ]] || echo all;;
    *) log "unknown stage $stage"; exit 64;;
  esac
}

# ---- validate a stage's outputs, lint, and mark -------------------------------
cmd_validate() {
  local stage="$1" letter subdir failed=0
  case "$stage" in
    draw-a|draw-b|draw-c)
      letter="${stage#draw-}"; subdir="draws_${letter}"
      for t in "${THEMES[@]}"; do
        local f="$RUN_DIR/$subdir/$t.md"
        if [[ ! -s "$f" ]]; then log "MISSING: $f"; failed=1; continue; fi
        if "$PY" "$HARNESS_DIR/contract_lint.py" "$f" >/dev/null 2>"$RUN_DIR/.lint.$stage.$t.err"; then
          mark "${stage}.${t}"
        else
          log "LINT FAIL: $f"; cat "$RUN_DIR/.lint.$stage.$t.err" >&2; failed=1
        fi
      done
      ;;
    merge)
      for t in "${THEMES[@]}"; do
        local f="$RUN_DIR/merged/$t.md"
        if [[ ! -s "$f" ]]; then log "MISSING: $f"; failed=1; continue; fi
        if "$PY" "$HARNESS_DIR/contract_lint.py" "$f" >/dev/null 2>"$RUN_DIR/.lint.merge.$t.err"; then
          mark "merge.${t}"
        else
          log "LINT FAIL: $f"; cat "$RUN_DIR/.lint.merge.$t.err" >&2; failed=1
        fi
      done
      ;;
    depth|closure|inverse)
      local f="$RUN_DIR/$stage.md"
      if [[ ! -s "$f" ]]; then log "MISSING: $f"; failed=1
      elif "$PY" "$HARNESS_DIR/contract_lint.py" "$f" >/dev/null 2>"$RUN_DIR/.lint.$stage.err"; then
        mark "$stage"
      else
        log "LINT FAIL: $f"; cat "$RUN_DIR/.lint.$stage.err" >&2; failed=1
      fi
      ;;
    synthesis)
      for f in report.md findings.json synthesis_ledger.json; do
        [[ -s "$RUN_DIR/$f" ]] || { log "MISSING: $RUN_DIR/$f"; failed=1; }
      done
      if [[ "$failed" -eq 0 ]]; then
        local inputs=()
        for t in "${THEMES[@]}"; do inputs+=("$RUN_DIR/merged/$t.md"); done
        for extra in depth closure inverse; do
          [[ -f "$RUN_DIR/$extra.md" ]] && inputs+=("$RUN_DIR/$extra.md")
        done
        if "$PY" "$HARNESS_DIR/fidelity_audit.py" \
            --inputs "${inputs[@]}" \
            --ledger "$RUN_DIR/synthesis_ledger.json" \
            --delivered "$RUN_DIR/findings.json" 2>"$RUN_DIR/.fidelity.err"; then
          mark synthesis
        else
          log "FIDELITY FAIL:"; cat "$RUN_DIR/.fidelity.err" >&2; failed=1
        fi
      fi
      ;;
    *) log "unknown stage $stage"; exit 64;;
  esac
  [[ "$failed" -eq 0 ]] || exit 3
  log "validate $stage: OK"
}

# ---- report next stage --------------------------------------------------------
cmd_next() {
  is_marked stage0 || { echo "stage0"; return; }
  for s in draw-a draw-b draw-c merge; do
    [[ -z "$(cmd_pending "$s")" ]] || { echo "$s"; return; }
  done
  is_marked depth     || { echo "depth"; return; }
  is_marked closure   || { echo "closure"; return; }
  is_marked inverse   || { echo "inverse"; return; }
  is_marked synthesis || { echo "synthesis"; return; }
  echo "done"
}

cmd_status() {
  echo "RUN_DIR=$RUN_DIR"
  for s in stage0 draw-a draw-b draw-c merge depth closure inverse synthesis; do
    case "$s" in
      draw-a|draw-b|draw-c|merge)
        local p; p="$(cmd_pending "$s" | tr '\n' ' ')"
        [[ -z "$p" ]] && echo "  $s: complete" || echo "  $s: pending -> $p";;
      *) is_marked "$s" && echo "  $s: complete" || echo "  $s: pending";;
    esac
  done
  echo "next: $(cmd_next)"
}

main() {
  local cmd="${1:-}"; [[ $# -gt 0 ]] && shift || true
  case "$cmd" in
    stage0) cmd_stage0 "$@";;
    seat-prompt) cmd_seat_prompt "$@";;
    pending) cmd_pending "$@";;
    validate) cmd_validate "$@";;
    next) cmd_next;;
    status) cmd_status;;
    themes) printf '%s\n' "${THEMES[@]}";;
    -h|--help|"") sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//';;
    *) log "unknown command: $cmd"; exit 64;;
  esac
}
main "$@"
