#!/usr/bin/env python3
"""Self-contained regression bench for guard_scan.py (the forbidden-content guard).

Guards four properties that are easy to break and expensive to get wrong:

  1. The default is a NO-OP. No declaration, or policy off, must not change
     behaviour for an existing repo (the backwards-compat guarantee).
  2. Types are reported, matched text never is. A guard that echoes the secret
     in its own advisory re-leaks it; this is the property the whole design
     exists for, so it is asserted against the literal secret bytes.
  3. A malformed declaration is a USAGE ERROR (exit 2), never a silent pass.
     A typo'd regex that matches nothing is the exact failure this guard is
     meant to prevent, so it must be loud.
  4. warn never blocks; block does (both exit 1 on a match — the distinction
     is in the advisory text, not the exit code).

Pass/fail is the exit code, not a golden diff: the outputs are small and
asserted directly. No third-party dependencies.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "guard_scan.py"
SECRET = "sk-ABCDEFGHIJKLMNOP1234"
HOST = "billing-api.internal"

GUARD = {
    "policy_redaction": "warn",
    "forbidden_types": [
        {"name": "credential-fragment", "pattern": r"sk-[A-Za-z0-9]{16,}"},
        {"name": "private-hostname", "pattern": r"\b[a-z0-9-]+\.internal\b"},
    ],
}

ok = True


def fail(msg):
    global ok
    print(f"FAIL: {msg}")
    ok = False


def run(dirpath, text=None, stdin_text=None, policy=None, config=None):
    cmd = [sys.executable, str(SCRIPT)]
    if config:
        cmd += ["--config", config]
    else:
        cmd += ["--dir", str(dirpath)]
    if policy:
        cmd += ["--policy", policy]
    if stdin_text is not None:
        cmd += ["--stdin"]
        r = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True)
    else:
        cmd += ["--text", text if text is not None else ""]
        r = subprocess.run(cmd, capture_output=True, text=True)
    return r


def write_guard(d, payload):
    d.mkdir(parents=True, exist_ok=True)
    (d / ".unforget-guard.json").write_text(json.dumps(payload))
    return d


tmp = Path(tempfile.mkdtemp())
g = write_guard(tmp / "guard", GUARD)

# 1. default is a no-op -----------------------------------------------------
r = run(tmp / "absent", text="anything at all")
if r.returncode != 0:
    fail(f"no declaration should exit 0, got {r.returncode}")
d = json.loads(r.stdout)
if d.get("checked") is not False or d.get("types") != []:
    fail(f"no declaration should report checked=false/clean, got {d}")

off = write_guard(tmp / "off", {**GUARD, "policy_redaction": "off"})
r = run(off, text=f"{SECRET} should not be flagged when policy is off")
if r.returncode != 0:
    fail(f"policy=off should exit 0 even on a match, got {r.returncode}")
if json.loads(r.stdout).get("checked") is not False:
    fail("policy=off should report checked=false")

# 2. types yes, matched text never -----------------------------------------
r = run(g, text=f"token {SECRET} lives at {HOST}")
d = json.loads(r.stdout)
if r.returncode != 1:
    fail(f"a match should exit 1, got {r.returncode}")
if sorted(d.get("types", [])) != ["credential-fragment", "private-hostname"]:
    fail(f"expected both type names, got {d.get('types')}")
blob = r.stdout + r.stderr
for leak in (SECRET, HOST, "sk-ABCDEFGHIJKLMNOP", "ABCDEFGHIJKLMNOP1234"):
    if leak in blob:
        fail(f"RE-LEAK: matched text {leak!r} appeared in the guard's own output")
if not d.get("advisory"):
    fail("a match must carry an advisory line")

# 2b. the same check via stdin must be equally leak-free
r = run(g, stdin_text=f"token {SECRET}")
if r.returncode != 1 or SECRET in (r.stdout + r.stderr):
    fail("stdin path: expected exit 1 with no leaked text")
if json.loads(r.stdout).get("types") != ["credential-fragment"]:
    fail(f"stdin path: wrong types {r.stdout}")

# 2c. a clean row under a declared policy is checked and passes
r = run(g, text="Retry logic swallows the underlying error")
d = json.loads(r.stdout)
if r.returncode != 0 or d.get("checked") is not True or d.get("clean") is not True:
    fail(f"clean row should be checked+clean+exit 0, got rc={r.returncode} {d}")

# 3. malformed declarations are usage errors, not silent passes ------------
# NB: each carries an explicit policy_redaction. Without one, policy defaults
# to "off", and "off" is a total no-op that returns BEFORE compiling — which is
# correct, but would mean these cases never reached the code under test.
cases = {
    "bad-regex": {"policy_redaction": "warn",
                  "forbidden_types": [{"name": "b", "pattern": "([unclosed"}]},
    "not-json": "RAW NOT JSON",
    "not-object": "[1,2,3]",
    "missing-pattern": {"policy_redaction": "warn",
                        "forbidden_types": [{"name": "x"}]},
    "entry-not-object": {"policy_redaction": "warn",
                         "forbidden_types": ["just-a-string"]},
}
for name, payload in cases.items():
    dpath = tmp / name
    dpath.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        (dpath / ".unforget-guard.json").write_text(payload)
    else:
        (dpath / ".unforget-guard.json").write_text(json.dumps(payload))
    r = run(dpath, text=SECRET)
    if r.returncode != 2:
        fail(f"{name}: expected usage error exit 2, got {r.returncode}")
    if "Traceback" in r.stderr:
        fail(f"{name}: should report cleanly, not traceback")
    if SECRET in r.stderr:
        fail(f"{name}: usage error must not echo the candidate text")

# 3b. policy=off is a TOTAL no-op — it returns before compiling, so a malformed
#     declaration in a file nobody reads can never break a repo not using the
#     guard. (Regression: an invalid regex used to raise even with policy off.)
off_broken = write_guard(tmp / "off-broken",
                         {**GUARD, "policy_redaction": "off",
                          "forbidden_types": [{"name": "b", "pattern": "([unclosed"}]})
r = run(off_broken, text=SECRET)
if r.returncode != 0:
    fail(f"policy=off with a broken declaration should be a silent no-op, got {r.returncode}")
if json.loads(r.stdout).get("checked") is not False:
    fail("policy=off with a broken declaration should report checked=false")

# 3c. the registry global is actually READ. (Regression: guard called
#     registry.read(), which does not exist; a broad except swallowed the
#     AttributeError, so a repo's registry policy was silently ignored and
#     the guard fell back to "off".)
reg_dir = tmp / "registry"
reg_dir.mkdir(parents=True, exist_ok=True)
(reg_dir / "README.md").write_text(
    "# Ledger\n\n<!-- unforget-registry:begin -->\n\n"
    "### unforget registry\n\n"
    "| key | value |\n|---|---|\n| policy_redaction | block |\n\n"
    "<!-- unforget-registry:end -->\n")
write_guard(reg_dir, {**GUARD, "policy_redaction": None})  # policy lives ONLY in the registry
r = run(reg_dir, text=SECRET)
d = json.loads(r.stdout)
if r.returncode != 1 or d.get("policy") != "block":
    fail(f"registry policy_redaction=block was not honoured: rc={r.returncode} {d}")

# 4. warn vs block ----------------------------------------------------------
rw = run(g, text=SECRET, policy="warn")
rb = run(g, text=SECRET, policy="block")
if rw.returncode != 1 or rb.returncode != 1:
    fail("both warn and block exit 1 on a match")
aw, ab = json.loads(rw.stdout)["advisory"], json.loads(rb.stdout)["advisory"]
if "Advisory only" not in aw:
    fail(f"warn advisory should say it is advisory, got {aw!r}")
if "refused" not in ab:
    fail(f"block advisory should say the write is refused, got {ab!r}")

# 5. missing text is a usage error ----------------------------------------
r = subprocess.run([sys.executable, str(SCRIPT), "--dir", str(g)],
                   capture_output=True, text=True)
if r.returncode != 2:
    fail(f"no --text/--stdin should exit 2, got {r.returncode}")

if ok:
    print("OK: guard_scan honours no-op default, reports types without leaking "
          "text, fails loud on malformed declarations, and separates warn/block.")
sys.exit(0 if ok else 1)
