#!/usr/bin/env bash
# unforget self-test corpus harness
#
# Runs each deterministic helper under `scripts/` against the fixture project,
# normalizes the output, and diffs against `tests/golden/<helper>.json`.
# Exits non-zero on any divergence.
#
# To re-baseline a golden file (after an intentional change):
#   bash tests/run.sh --bless
#
# See tests/README.md for the full coverage matrix and what's deferred.

set -uo pipefail   # NOTE: deliberately not -e — we tolerate non-zero exits
                   # from helpers (e.g. check_format_version returns 1 when
                   # it reports drift) and rely on the diff for pass/fail.

cd "$(dirname "$0")"
TESTS_DIR="$(pwd -P)"
# Resolve the PHYSICAL path (-P): the skill is often installed as a symlink
# (~/.claude/skills/unforget → the real checkout), and the helpers emit
# realpath-resolved paths. Using the logical path here would make normalize.py's
# repo-root string-replace miss, spuriously failing scan_surfaces on the golden.
REPO_ROOT="$(cd .. && pwd -P)"

FIXTURE="$TESTS_DIR/fixtures/sample-project"
GOLDEN="$TESTS_DIR/golden"
NORMALIZE="$TESTS_DIR/normalize.py"
SCRIPTS="$REPO_ROOT/scripts"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

BLESS=0
if [[ "${1:-}" == "--bless" ]]; then
  BLESS=1
fi

FAILED=0

run_diff() {
  local kind="$1"; shift
  local actual="$TMP/${kind}.json"
  local golden="$GOLDEN/${kind}.json"
  local raw="$TMP/${kind}.raw.json"

  # Tee the raw helper output through normalize. We ignore the helper's exit
  # code intentionally — pass/fail is determined by golden diff, not exit code.
  python3 "$SCRIPTS/${kind}.py" "$@" > "$raw"
  python3 "$NORMALIZE" --kind "$kind" --repo-root "$REPO_ROOT" < "$raw" > "$actual"

  if [[ "$BLESS" == 1 ]]; then
    cp "$actual" "$golden"
    echo "BLESSED: $kind"
    return 0
  fi

  if [[ ! -f "$golden" ]]; then
    echo "FAIL: $kind — no golden at $golden"
    echo "      To create it: bash tests/run.sh --bless"
    FAILED=1
    return 0
  fi

  if diff -u "$golden" "$actual"; then
    echo "PASS: $kind"
  else
    echo "FAIL: $kind diverged from golden."
    echo "      To re-baseline (after reviewing the diff): bash tests/run.sh --bless"
    FAILED=1
  fi
}

run_diff scan_surfaces        --root "$FIXTURE" --include-comments
run_diff check_format_version "$FIXTURE/Documentation/Development/UNFORGET.md"
run_diff encode_project_path  "/Volumes/2 TB Drive/Coding/GitHub/unforget-test"
run_diff dedup_findings       --candidates "$TESTS_DIR/fixtures/dedup-input.json"
run_diff verify_install       --skill-root "$REPO_ROOT"

if [[ "$BLESS" == 1 ]]; then
  echo
  echo "All goldens written. Review with: git diff tests/golden/"
  exit 0
fi

# Header-order lint: a repo-wide invariant, not a golden snapshot (the checked
# count grows as tables are added, which would make a golden brittle). Scans
# every UNFORGET-ledger table header for canonical core-column order. This is
# the guard that keeps finding #1 (a fixture that reversed Target/Finding) from
# silently returning. Runs over the whole repo, LLM-free.
echo
echo "--- header-order lint (canonical column order) ---"
if ! python3 "$SCRIPTS/check_header_order.py" --root "$REPO_ROOT"; then
  echo "FAIL: one or more UNFORGET-ledger headers are out of canonical order"
  FAILED=1
fi

# Behavioral corpus: run the LLM-free halves inline (checker selftest + check
# over any already-produced results). The LLM half is driven separately; see
# tests/behavioral/README.md. Selftest failing means the behavioral CHECKER is
# broken and must fail the suite; a behavioral case failing does too.
# Example-as-fixture: the committed examples/UNFORGET.md is a real v2 ledger that
# exercises all six @status values, a done-unverified "owed" row, a bounded-index
# split, AND the optional 1-Star Risk column appended after Status. That last part
# is the regression guard for the "status_cell read the trailing column, not the
# token" bug: if status parsing regresses, the token count drops and this fails.
echo
echo "--- example-as-fixture (examples/UNFORGET.md, a real v2 ledger) ---"
if ! python3 - "$REPO_ROOT" <<'PY'
import json, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
ex = root / "examples" / "UNFORGET.md"
scripts = root / "scripts"
ok = True

# 1. format v2 recognized
r = subprocess.run([sys.executable, str(scripts / "check_format_version.py"), str(ex)],
                   capture_output=True, text=True)
fv = json.loads(r.stdout or "{}")
if not fv.get("recognized") or fv.get("format_version") != "v2":
    print(f"FAIL: example not recognized as v2 ({fv.get('format_version')})"); ok = False

# 2. EVERY row carries a parseable @status token and there are ZERO integrity issues.
#    (This is the 1-Star-Risk-after-Status regression guard: the bug made this 0.)
r = subprocess.run([sys.executable, str(scripts / "parse_status.py"), "--file", str(ex)],
                   capture_output=True, text=True)
rows = json.loads(r.stdout or "[]")
tokened = sum(1 for x in rows if x["token_present"])
issues = [(x["id"], x["issues"]) for x in rows if x["issues"]]
if tokened != len(rows):
    print(f"FAIL: only {tokened}/{len(rows)} example rows parsed a @status token "
          f"(regression: an appended column may be shadowing the Status cell)"); ok = False
if issues:
    print(f"FAIL: example has status integrity issues: {issues}"); ok = False

# 3. the verify gate passes on the example (no error-severity findings)
r = subprocess.run([sys.executable, str(scripts / "verify_ledger.py"), "--file", str(ex)],
                   capture_output=True, text=True)
v = json.loads(r.stdout or "{}")
if not v.get("gate_pass", False):
    print(f"FAIL: verify gate does not pass on the example ({v.get('error_count')} errors)"); ok = False

if ok:
    print(f"OK: example is v2, all {len(rows)} rows tokened, verify gate passes.")
sys.exit(0 if ok else 1)
PY
then
  echo "FAIL: examples/UNFORGET.md regressed"
  FAILED=1
fi

echo
echo "--- behavioral corpus (LLM-free portion) ---"
if ! bash "$TESTS_DIR/behavioral/run-behavioral.sh" --selftest; then
  echo "FAIL: behavioral checker selftest"
  FAILED=1
fi
if ! bash "$TESTS_DIR/behavioral/run-behavioral.sh" --check; then
  echo "FAIL: one or more behavioral cases with a result.md diverged"
  FAILED=1
fi

if [[ "$FAILED" == 1 ]]; then
  echo
  echo "One or more tests failed."
  exit 1
fi

echo
echo "All tests passed."
