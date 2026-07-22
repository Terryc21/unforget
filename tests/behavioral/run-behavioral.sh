#!/usr/bin/env bash
# Behavioral test runner for unforget.
#
# Unlike tests/run.sh (which diffs deterministic script output against golden
# JSON), behavioral cases exercise the LLM following the skill's PROSE. The LLM
# step is not automatable from a plain shell — it needs a Claude Code session.
# So this runner has two modes:
#
#   --check   (default) Run the structural checker over every case that already
#             has a result.md. Cases with no result.md are reported SKIPPED
#             (not run yet). This is the CI-safe, no-LLM mode.
#
#   --list    Print each case's command.txt so you (or a session) know what to
#             run. Use this to drive the LLM half by hand.
#
#   --selftest  Prove the checker itself works: synthesize a known-good and a
#             known-bad result for a canary case and confirm PASS then FAIL.
#             Runs with no LLM. This is what guards the guard.
#
# Protocol for producing a result.md (the LLM half):
#   1. Copy the case's input.md to a scratch project as UNFORGET.md.
#   2. In a Claude Code session in that project, run the line in command.txt.
#   3. Copy the resulting UNFORGET.md back to the case dir as result.md.
#      (For interactive commands like `promote`, save the assistant's REPORTED
#       output as result.md instead — see each case's assertions.txt.)
#   4. Re-run this script in --check mode.
#
# Exit: 0 if every case with a result PASSED (and selftest, if run, passed).
#       1 if any checked case FAILED. SKIPPED cases do not fail the run.

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$HERE/check_behavioral.py"
MODE="${1:---check}"

cases() { find "$HERE" -mindepth 1 -maxdepth 1 -type d | sort; }

case "$MODE" in
  --list)
    for c in $(cases); do
      echo "== $(basename "$c") =="
      cat "$c/command.txt"
      echo
    done
    ;;

  --selftest)
    # Canary: case 03 (edit A1 Target LATER->THIS). Build good + bad results.
    canary="$HERE/03-edit-target"
    tmp_good="$(mktemp)"; tmp_bad="$(mktemp)"
    sed 's/| A1 | 🟡 LATER |/| A1 | 🔴 THIS |/' "$canary/input.md" > "$tmp_good"
    cp "$canary/input.md" "$tmp_bad"   # unchanged = wrong (edit never applied)
    echo "--- selftest: GOOD result must PASS ---"
    python3 "$CHECK" --case "$canary" --result "$tmp_good"; good=$?
    echo "--- selftest: BAD result must FAIL ---"
    python3 "$CHECK" --case "$canary" --result "$tmp_bad"; bad=$?
    rm -f "$tmp_good" "$tmp_bad"
    if [[ $good -eq 0 && $bad -ne 0 ]]; then
      echo "SELFTEST PASS: checker passes correct, fails incorrect."
      exit 0
    fi
    echo "SELFTEST FAIL: checker did not discriminate (good=$good bad=$bad)."
    exit 1
    ;;

  --check|"")
    fails=0; ran=0; skipped=0
    for c in $(cases); do
      if [[ -f "$c/result.md" ]]; then
        ran=$((ran+1))
        echo "== $(basename "$c") =="
        python3 "$CHECK" --case "$c" || fails=$((fails+1))
        echo
      else
        skipped=$((skipped+1))
        echo "SKIP $(basename "$c") — no result.md (not run yet)"
      fi
    done
    echo
    echo "Behavioral: $ran run, $skipped skipped, $fails failed."
    [[ $fails -eq 0 ]] && exit 0 || exit 1
    ;;

  *)
    echo "usage: run-behavioral.sh [--check|--list|--selftest]" >&2
    exit 2
    ;;
esac
