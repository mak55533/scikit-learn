#!/usr/bin/env bash
# cloud_submit.sh THEME — submit one theme seat to the claude-go-brr cloud,
# capture its agent_output as runs/26385/draws_a/THEME.md.
# NOTE: this is the cloud-execution driver (claude-go-brr), used per the user's
# explicit request to run the harness on the cloud. It is NOT invoked by run.sh.
set -Eeuo pipefail
THEME="$1"
REPO="/Users/makark/Functio/daniel-flow/scikit-learn"
OFF="/Users/makark/.claude/plugins/cache/claude-go-brr/claude-go-brr/0.1.5/offload.sh"
RUN="$REPO/review-harness/runs/26385"
export OFFLOAD_POLL_INTERVAL="${OFFLOAD_POLL_INTERVAL:-10}"
export OFFLOAD_POLL_TIMEOUT="${OFFLOAD_POLL_TIMEOUT:-1800}"

PROMPT="You are a code-review seat. Read the file review-harness/runs/26385/cloud_prompts/${THEME}.txt in this repository and follow its instructions EXACTLY and in full — it is your complete charter, including which input files to read and the required output format. Do not modify any file. Your final message (agent_output) must be ONLY the findings-file content it specifies (finding blocks or the single line NO FINDINGS), with no other text."

cd "$REPO"
OUT="$RUN/.cloud/${THEME}.submit.log"
mkdir -p "$RUN/.cloud"
echo "[$(date +%H:%M:%S)] submitting $THEME" >&2
bash "$OFF" submit -d "$REPO" "$PROMPT" > "$OUT" 2>&1 || true

# find the run_id the submit created
RID="$(grep -oE 'run_id=[0-9A-Za-z._-]+' "$OUT" | head -1 | cut -d= -f2 || true)"
echo "[$(date +%H:%M:%S)] $THEME run_id=$RID" >&2
if [[ -z "$RID" || ! -f "$REPO/.git/offload/$RID.output.txt" ]]; then
  echo "FAIL $THEME: no output (run_id=$RID)" >&2
  exit 1
fi
python3 - "$RID" "$THEME" <<'PY'
import sys,re,pathlib
rid,theme=sys.argv[1],sys.argv[2]
repo=pathlib.Path("/Users/makark/Functio/daniel-flow/scikit-learn")
txt=(repo/f".git/offload/{rid}.output.txt").read_text()
m=re.search(r"(?m)^#{2,4}\s*F\d+|^NO FINDINGS", txt)
out=txt[m.start():] if m else txt
dst=repo/"review-harness/runs/26385/draws_a"/f"{theme}.md"
dst.write_text(out)
print(f"wrote {dst} ({len(out)} chars)")
PY
echo "[$(date +%H:%M:%S)] $THEME done" >&2
