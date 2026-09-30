#!/bin/bash
# verify-manifest.sh — manifest sanity check for unforget plugin
#
# Validates:
#   1. plugin.json parses as JSON
#   2. plugin.json "name" field is "unforget"
#   3. plugin.json "name" matches SKILL.md frontmatter "name"
#   4. version agrees across SKILL.md, plugin.json, and marketplace.json
#      (this drift is why the marketplace listing once fell 6 versions behind)
#
# Note: this plugin uses the flat single-skill layout (one SKILL.md at repo
# root, no skills/ subdir). Claude Code supports this layout with no "skills"
# field. Codex loads the same root SKILL.md as a standalone skill.
#
# Run manually or add as a pre-commit / CI check.
#
# Adapted from radar-suite's verify-manifest.sh, simplified for unforget's
# flat single-skill layout.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$SCRIPT_DIR/plugin.json"
MARKETPLACE="$SCRIPT_DIR/marketplace.json"
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

# 4. version agreement across the three sources (catches the marketplace-listing drift)
SKILL_VER=$(python3 - "$REPO_ROOT" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "scripts"))
from verify_install import read_version
print(read_version(root) or "")
PY
)
PLUGIN_VER=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['version'])")
MARKET_VER=$(python3 -c "import json; print(json.load(open('$MARKETPLACE'))['plugins'][0]['version'])")
if [ "$SKILL_VER" != "$PLUGIN_VER" ] || [ "$SKILL_VER" != "$MARKET_VER" ]; then
    echo "ERROR: version mismatch — SKILL.md=$SKILL_VER, plugin.json=$PLUGIN_VER, marketplace.json=$MARKET_VER"
    echo "       bump all three together (a release changes all of them)"
    exit 1
fi

echo "OK: plugin.json valid, name=unforget, matches SKILL.md; version $SKILL_VER consistent across all three manifests"
exit 0
