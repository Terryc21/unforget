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
# Note: this plugin uses the standard plugin layout: the one skill lives at
# skills/unforget/SKILL.md, which Claude Code discovers with no "skills" field.
# Codex can load the same directory as a standalone skill.
#
# Run manually or add as a pre-commit / CI check.
#
# Adapted from radar-suite's verify-manifest.sh, simplified for unforget's
# single-skill plugin layout.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$SCRIPT_DIR/plugin.json"
MARKETPLACE="$SCRIPT_DIR/marketplace.json"
SKILL_DIR="$REPO_ROOT/skills/unforget"
SKILL_FILE="$SKILL_DIR/SKILL.md"

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
SKILL_VER=$(python3 - "$SKILL_DIR" <<'PY'
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

# 5. one description: plugin.json and the marketplace's plugin entry say the same thing,
#    and the marketplace tagline is SKILL.md's opening sentence (SKILL.md itself goes on
#    to list trigger phrases, so it is not compared whole).
if ! python3 - "$MANIFEST" "$MARKETPLACE" "$SKILL_FILE" <<'PY'
import json, re, sys
plugin = json.load(open(sys.argv[1]))["description"].strip()
market = json.load(open(sys.argv[2]))
entry = market["plugins"][0]["description"].strip()
tagline = market["description"].strip()
text = open(sys.argv[3], encoding="utf-8").read()
m = re.search(r"^description:\s*\|\n((?:  .*\n)+)", text, re.M)
skill = " ".join(line.strip() for line in m.group(1).splitlines()) if m else ""
ok = True
if plugin != entry:
    print("ERROR: plugin.json description differs from marketplace.json plugins[0].description"); ok = False
first = lambda s: s.split(". ")[0].rstrip(".")
if first(tagline) != first(skill) or not plugin.startswith(first(skill)):
    print("ERROR: marketplace tagline and plugin description must open with SKILL.md's first sentence:")
    print(f"       SKILL.md: {first(skill)!r}")
    print(f"       tagline:  {first(tagline)!r}"); ok = False
sys.exit(0 if ok else 1)
PY
then
    exit 1
fi

echo "OK: plugin.json valid, name=unforget, matches SKILL.md; version $SKILL_VER consistent across all three manifests; descriptions agree"
exit 0
