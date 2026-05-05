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
TESTS_DIR="$(pwd)"
REPO_ROOT="$(cd .. && pwd)"

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

if [[ "$BLESS" == 1 ]]; then
  echo
  echo "All goldens written. Review with: git diff tests/golden/"
  exit 0
fi

if [[ "$FAILED" == 1 ]]; then
  echo
  echo "One or more tests failed."
  exit 1
fi

echo
echo "All tests passed."
