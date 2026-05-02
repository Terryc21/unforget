#!/bin/bash
# verify-manifest.sh — manifest sanity check for unforget plugin
#
# Validates:
#   1. plugin.json parses as JSON
#   2. plugin.json "name" field matches SKILL.md frontmatter "name"
#   3. plugin.json "skills" array contains exactly one entry named "unforget"
#      (flat single-skill layout; if v0.3+ moves to nested skills/, this script
#      should be replaced with the radar-suite-style drift check)
#
# Run manually or add as a pre-commit / CI check.
#
# Adapted from radar-suite's verify-manifest.sh, simplified for unforget's
# flat single-skill layout (one SKILL.md at repo root, no skills/ subdir).

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$SCRIPT_DIR/plugin.json"
SKILL_FILE="$REPO_ROOT/SKILL.md"

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: plugin.json not found at $MANIFEST"
    exit 1
fi

if [ ! -f "$SKILL_FILE" ]; then
    echo "ERROR: SKILL.md not found at $SKILL_FILE"
    exit 1
fi

# 1. JSON parse check (uses python; jq optional)
if ! python3 -c "import json; json.load(open('$MANIFEST'))" 2>/dev/null; then
    echo "ERROR: plugin.json is not valid JSON"
    exit 1
fi

# 2. plugin.json "name" field
MANIFEST_NAME=$(grep -m1 '"name":' "$MANIFEST" | sed 's/.*"name": *"\([^"]*\)".*/\1/')
if [ "$MANIFEST_NAME" != "unforget" ]; then
    echo "ERROR: plugin.json top-level name is '$MANIFEST_NAME', expected 'unforget'"
    exit 1
fi

# 3. SKILL.md frontmatter name
SKILL_NAME=$(awk '/^---$/{count++; next} count==1 && /^name:/{print $2; exit}' "$SKILL_FILE")
if [ "$SKILL_NAME" != "unforget" ]; then
    echo "ERROR: SKILL.md frontmatter name is '$SKILL_NAME', expected 'unforget'"
    exit 1
fi

# 4. plugin.json "skills" array contains "unforget"
SKILLS_LIST=$(awk '/"skills":/,/^  \]/' "$MANIFEST" | grep '"name":' | sed 's/.*"name": *"\([^"]*\)".*/\1/')
SKILL_COUNT=$(echo "$SKILLS_LIST" | grep -c .)

if [ "$SKILL_COUNT" -ne 1 ]; then
    echo "ERROR: plugin.json skills array has $SKILL_COUNT entries, expected exactly 1"
    echo "Skills found:"
    echo "$SKILLS_LIST" | sed 's/^/  - /'
    exit 1
fi

if [ "$SKILLS_LIST" != "unforget" ]; then
    echo "ERROR: plugin.json skills array contains '$SKILLS_LIST', expected 'unforget'"
    exit 1
fi

echo "OK: plugin.json valid, name=unforget, skills=[unforget], matches SKILL.md frontmatter"
exit 0
