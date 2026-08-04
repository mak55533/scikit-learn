# ORCHESTRATOR.md — how a profiled Claude Code session drives this harness

This harness is deliberately split into two halves:

## 1. Deterministic helper (`run.sh` + the three Python scripts)
`run.sh` **never launches an agent.** It prepares inputs, reports pending seats,
validates outputs, runs the contract/fidelity linters, and writes markers. The
Python scripts (`diff_manifest.py`, `contract_lint.py`, `fidelity_audit.py`) are
pure and agentless.

## 2. Native-Agent orchestration (the overseeing Claude Code session)
The overseeing session is the profiled process. **It** launches every seat with
Claude Code's native `Agent` tool so CCX records each seat as a child in
`profile_timeline.json` via SubagentStart/SubagentStop. No seat is ever launched
through Bash, `claude -p`, `claude-go-brr`, `codex exec`, or any shell wrapper.

### Loop the orchestrator runs
```
run.sh stage0 --repo … --worktree … --base … --head … --pr 26385   # once
loop:
  stage=$(run.sh next)                       # stage0|draw-a|…|synthesis|done
  [ "$stage" = done ] && stop
  for seat in $(run.sh pending "$stage"):
      prompt=$(run.sh seat-prompt "$stage" "$seat")
      launch NATIVE Agent(prompt)            # up to 12 concurrent in one turn
  wait for all Agent calls in the wave
  run.sh validate "$stage"                   # lint + mark; nonzero => re-prompt
  on validate failure: relaunch a fresh native Agent for the failing seat with
      the original prompt PLUS the concrete lint/fidelity errors, max 3 retries
```

### Stage order (barriers between stages)
```
stage0     inputs: PLAN.md, DIFF_MANIFEST.md, hunks/          (run.sh, no agent)
draw-a     12 theme seats (native Agent, ≤12 concurrent)      -> draws_a/<theme>.md
draw-b     12 fresh seats, blind to A                         -> draws_b/<theme>.md
draw-c     12 fresh seats, blind to A/B                       -> draws_c/<theme>.md
merge      12 seats, union of the 3 draws per theme, lint     -> merged/<theme>.md
depth      1 seat, ADD-ONLY strengthening                     -> depth.md
closure    1 seat, rule sweep across full manifest            -> closure.md
inverse    1 seat, plan/change inventory reconciliation       -> inverse.md
synthesis  1 seat, SELECT verbatim + ledger                   -> report.md,
                                                                 findings.json,
                                                                 synthesis_ledger.json
fidelity   run.sh validate synthesis (2 auditors, no agent)   loop until clean
deliver    report.md / findings.json are the deliverables
```

### Resume semantics
On resume, the orchestrator inspects `runs/<pr>/markers/`, skips every seat whose
marker exists AND whose output file validates, and launches only the pending
native Agent work reported by `run.sh pending <stage>`. `run.sh next` reports the
first incomplete stage. Because markers are only written after validation, a
crashed seat is naturally retried.

### One model, highest effort
Every native Agent seat uses ONE model at its highest reasoning setting. Retries
use the same native Agent mechanism. Models are not mixed across seats.
