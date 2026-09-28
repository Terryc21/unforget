#!/usr/bin/env python3
r"""The forbidden-content check: does candidate text contain a declared type?

Deterministic half of the forbidden-content guard (see
reference/forbidden-content.md). It answers ONE question — "does the text the
agent is about to write contain something this repo declared it must never
contain?" — and reports the TYPE that matched, never the matched text.

Why types and not matches: a guard that echoes the offending string in its own
output re-leaks the thing it just caught. The advisory reads
`credential-fragment`, and the caller (the LLM) paraphrases and retries. This
is a hard property of the design, not a nicety — see reference §4.

The declaration is a repo-local `.unforget-guard.json` (names + regex), and the
strictness is the registry global `policy_redaction` (off | warn | block).
Absent a declaration, or with policy off, this is a no-op returning
`{"checked": false}` — existing users see no behaviour change.

Not a scanner and not a redactor: it never reads the ledger or the repo, only
the candidate text it is handed. Whole-repo secret-scanning is a different job
with different failure modes.

Usage:
  # Check text against a repo's declared types:
  python3 guard_scan.py --dir <ledger-dir> --text "<candidate text>"

  # Or supply the text on stdin (avoids putting it in argv / shell history):
  cat row.md | python3 guard_scan.py --dir <ledger-dir> --stdin

  # Overridable for tests / non-standard layout:
  python3 guard_scan.py --config <path> --text "<candidate text>"

Output (stdout, JSON):
  {
    "checked": true|false,          # false = no declaration, or policy off
    "policy": "off"|"warn"|"block", # effective policy (or the configured one)
    "clean": true|false,            # no declared type matched
    "types": ["credential-fragment", ...],   # matched TYPE NAMES, sorted,
                                             # deduped — never the text
    "advisory": "<one-line summary or ''>"
  }

Exit codes:
  0  ok / no match (clean, or nothing declared)
  1  a declared type matched under policy warn OR block
  2  usage error / unreadable or malformed config

Standard library only. Regexes are applied with re.IGNORECASE and are
caller-supplied; a config with an invalid regex is a usage error (exit 2), not
a silent pass.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

POLICIES = {"off", "warn", "block"}
DEFAULT_POLICY = "off"
GUARD_FILENAME = ".unforget-guard.json"

# Registry global read order mirrors defer_tally.py's threshold handling: the
# repo's README block wins, and a missing/partial registry just means defaults.
try:
    import registry as _registry  # noqa: E402
except Exception:  # pragma: no cover - registry is always present in-tree
    _registry = None


def _usage_error(msg: str) -> "SystemExit":
    """Exit 2 (usage error) with a message on stderr.

    SystemExit("msg") exits 1, which is the "a type matched" code and would
    read as a successful catch. Usage problems must not look like findings.
    """
    print(msg, file=sys.stderr)
    return SystemExit(2)


def load_config(config_path: Path) -> dict:
    """Read .unforget-guard.json. Returns {} when absent (declared: false)."""
    if not config_path.is_file():
        return {}
    try:
        data = json.loads(config_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise _usage_error(f"guard_scan: cannot read {config_path}: {exc}")
    if not isinstance(data, dict):
        raise _usage_error(f"guard_scan: {config_path} must contain a JSON object")
    return data


def compile_types(config: dict) -> list[tuple[str, re.Pattern]]:
    """Compile declared types. A bad regex is a usage error, never a silent pass."""
    out: list[tuple[str, re.Pattern]] = []
    for entry in config.get("forbidden_types", []) or []:
        if not isinstance(entry, dict):
            raise _usage_error("guard_scan: each forbidden_types entry must be an object")
        name = entry.get("name")
        pattern = entry.get("pattern")
        if not name or not pattern:
            raise _usage_error("guard_scan: each forbidden_types entry needs name + pattern")
        try:
            out.append((str(name), re.compile(str(pattern), re.IGNORECASE)))
        except re.error as exc:
            # Fail loud: a typo'd pattern that silently matches nothing is the
            # failure mode this whole guard exists to prevent.
            raise _usage_error(f"guard_scan: invalid regex for type {name!r}: {exc}")
    return out


def resolve_policy(config: dict, ledger_dir: Path | None) -> str:
    """Config value wins; else the registry global; else the default (off)."""
    policy = config.get("policy_redaction")
    if policy in POLICIES:
        return policy
    if ledger_dir is not None and _registry is not None:
        try:
            reg = _registry.read(dir=str(ledger_dir))
            value = (reg.get("global") or {}).get("policy_redaction")
            if value in POLICIES:
                return value
        except SystemExit as _se:
            if getattr(_se, "code", 1) == 2:
                raise
        except Exception:
            pass
        except Exception:
            pass
    return DEFAULT_POLICY


def scan(text: str, compiled: list[tuple[str, re.Pattern]]) -> list[str]:
    """Return sorted, deduped NAMES of matched types. Never returns match text."""
    return sorted({name for name, rx in compiled if rx.search(text)})


def advisory_for(policy: str, types: list[str]) -> str:
    if not types:
        return ""
    listed = ", ".join(types)
    if policy == "block":
        return (f"forbidden content matched ({listed}) — the write is refused. "
                f"Paraphrase to describe the problem without the value; do not "
                f"repeat the matched text.")
    return (f"forbidden content matched ({listed}) — rewrite the row so it names "
            f"the problem without the value. Advisory only; the write proceeds.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--dir", help="ledger directory (holds README + .unforget-guard.json)")
    p.add_argument("--config", help="explicit path to the guard config")
    p.add_argument("--text", help="candidate text to check")
    p.add_argument("--stdin", action="store_true", help="read candidate text from stdin")
    p.add_argument("--policy", choices=sorted(POLICIES),
                   help="override the configured policy (testing)")
    args = p.parse_args()

    if not args.text and not args.stdin:
        print("guard_scan: pass --text or --stdin", file=sys.stderr)
        return 2

    ledger_dir = Path(args.dir) if args.dir else None
    if args.config:
        config_path = Path(args.config)
    elif ledger_dir is not None:
        config_path = ledger_dir / GUARD_FILENAME
    else:
        print("guard_scan: pass --dir or --config", file=sys.stderr)
        return 2

    config = load_config(config_path)
    policy = args.policy or resolve_policy(config, ledger_dir)
    compiled = compile_types(config)

    # Nothing declared, or the repo turned it off → no-op, and we say so
    # explicitly so a caller can distinguish "no match" from "not checked".
    if not compiled or policy == "off":
        print(json.dumps({"checked": False, "policy": policy, "clean": True,
                          "types": [], "advisory": ""}, indent=2))
        return 0

    text = sys.stdin.read() if args.stdin else (args.text or "")
    types = scan(text, compiled)

    result = {
        "checked": True,
        "policy": policy,
        "clean": not types,
        "types": types,
        "advisory": advisory_for(policy, types),
    }
    print(json.dumps(result, indent=2))
    return 1 if types else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        raise SystemExit(130)
