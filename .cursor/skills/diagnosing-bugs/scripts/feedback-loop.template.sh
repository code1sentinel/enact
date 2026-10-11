#!/usr/bin/env bash
# Agent-runnable red/green wrapper for .cursor/skills/diagnosing-bugs.
# Copy, set CMD to one tight invocation, run until it goes red on this bug.
#
# Adapted from mattpocock/skills diagnosing-bugs (MIT,
# 49dd158d1076134a641b33efb035946536778336). The upstream HITL script is
# omitted: this repo's agents run headless.
set -euo pipefail

# Examples:
#   CMD='uv run pytest tests/test_e2e.py::test_failing_input_writes_poam -q'
#   CMD='enact validate --assessment-results /tmp/out/assessment-results.json --poam /tmp/out/poam.json'
#   CMD='opa test src/enact/library/ac-login-lockout -v'
#   CMD='node tests/eval_guide.js'
CMD="${CMD:?set CMD to the one command that should go red on this bug}"
RUNS="${RUNS:-1}"

red=0
i=1
while [ "$i" -le "$RUNS" ]; do
  echo "== loop $i/$RUNS: $CMD"
  set +e
  eval "$CMD"
  status=$?
  set -e
  echo "exit $status"
  if [ "$status" -ne 0 ]; then
    red=1
  fi
  i=$((i + 1))
done

if [ "$red" -eq 1 ]; then
  echo "RED: loop caught a failure"
  exit 1
fi
echo "GREEN: loop did not catch a failure"
exit 0
