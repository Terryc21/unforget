#!/usr/bin/env python3
r"""Classify ledger rows for setting aside by likelihood (read-only).

Implements the deterministic half of reference/pickup.md § Setting rows aside by
likelihood. It decides, for every open row rated `@likelihood:rare` or
`@likelihood:improbable`, whether a standing policy may set it aside on its own
or whether the user must decide. It never edits the ledger: the session applies
the edits the user (or the user's standing policy) approved.

The rules, in order:
  - Only open or blocked rows with a valid `@likelihood:` of rare or improbable
    are candidates. Unrated rows, other likelihoods (including `uncertain`) and
    rows already set aside are never candidates.
  - A candidate NEEDS THE USER when any of these holds:
      * its Target is THIS (setting it aside would take it off the release gate);
      * its Risk: No Fix is 🟡 High or 🔴 Critical;
      * the table has no Risk: No Fix column, so risk cannot be checked;
      * its text mentions a protected class (default: data loss, corruption,
        privacy, security, payments, money, credentials).
    Otherwise it is POLICY-ELIGIBLE.
  - The registry's `park_policy` turns that into an action:
      off  (default)  nothing is offered unprompted
      ask             every candidate goes into the batched question
      auto            policy-eligible rows are set aside and reported;
                      the rest go into the batched question

Usage:
  python3 set_aside.py classify --file <UNFORGET.md> [--dir <ledger-dir>]
      [--policy off|ask|auto] [--classes "data loss, privacy"]

  --dir reads `park_policy` and `park_protected_classes` from the registry.
  --policy / --classes override the registry for this run.

Output (stdout, JSON):
  {
    "file": "<path>",
    "policy": "off"|"ask"|"auto",
    "protected_classes": ["data loss", ...],
    "candidates": [
      {"id": "A12", "likelihood": "rare", "target": "NEXT",
       "eligibility": "policy-eligible"|"needs-user",
       "action": "none"|"ask"|"auto",
       "reasons": ["<why it needs the user>", ...]}
    ],
    "counts": {"auto": N, "ask": N, "none": N},
    "set_aside": {"count": N, "by_likelihood": {"rare": N, ...}, "ids": [...]},
    "summary_line": "Set aside: 9 (rare 5, improbable 4)"
  }

Exit codes: 0 ok · 2 usage error / file not found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_status  # noqa: E402

POLICIES = ("off", "ask", "auto")
DEFAULT_POLICY = "off"
DEFAULT_PROTECTED_CLASSES = [
    "data loss", "data-loss", "lose data", "loses data", "lost data", "corrupt",
    "privacy", "security", "payment", "purchase", "billing", "money", "credential",
]
HIGH_RISK_RE = re.compile(r"🔴|🟡|\bcritical\b|\bhigh\b", re.I)
CANDIDATE_STATES = {"open", "blocked"}


def parse_classes(value) -> list[str]:
    if value is None:
        return list(DEFAULT_PROTECTED_CLASSES)
    return [c.strip().lower() for c in str(value).split(",") if c.strip()]


def registry_settings(dir_path: Path | None) -> dict:
    """Read park_policy / park_protected_classes; absent registry → defaults."""
    if dir_path is None:
        return {}
    try:
        import registry  # type: ignore
        reg = registry.read_registry(dir_path)
        return dict(reg.get("global") or {})
    except (ImportError, OSError, ValueError):
        return {}


def protection_reasons(parsed: dict, row_text: str, classes: list[str]) -> list[str]:
    """Why a set-aside of this row needs the user's own decision (empty = none).

    Used by the classifier and by verify's accepted-risk check. Over-matching is
    the safe direction: a false match only routes a row to the user.
    """
    reasons = []
    risk = parsed.get("risk_no_fix")
    if risk is None or not str(risk).strip():
        reasons.append("no Risk: No Fix rating to check")
    elif HIGH_RISK_RE.search(str(risk)):
        reasons.append(f"Risk: No Fix is {str(risk).strip()}")
    lowered = row_text.lower()
    for phrase in classes:
        if phrase and phrase in lowered:
            reasons.append(f'mentions protected class "{phrase}"')
            break
    return reasons


def classify_row(parsed: dict, row_text: str, policy: str, classes: list[str]) -> dict | None:
    """Return a candidate record, or None when the row is not a candidate."""
    if parsed.get("set_aside") or parsed.get("completed"):
        return None
    if parsed.get("effective_status") not in CANDIDATE_STATES:
        return None
    likelihood = parsed.get("likelihood")
    if likelihood not in parse_status.SET_ASIDE_LIKELIHOODS:
        return None
    reasons = []
    if parsed.get("target") == "THIS":
        reasons.append("blocks the current release (Target THIS)")
    reasons += protection_reasons(parsed, row_text, classes)
    eligibility = "needs-user" if reasons else "policy-eligible"
    if policy == "off":
        action = "none"
    elif policy == "auto" and eligibility == "policy-eligible":
        action = "auto"
    else:
        action = "ask"
    return {"id": parsed.get("id"), "likelihood": likelihood,
            "target": parsed.get("target"), "eligibility": eligibility,
            "action": action, "reasons": reasons}


def row_records(text: str):
    """Yield (parsed, row_text) where row_text is the row plus its detail bullet."""
    details = parse_status.detail_blocks(text)
    for line, headers in parse_status.row_contexts(text):
        rid = parse_status.ROW_ID_RE.match(line)[1]
        detail = details.get(rid, "")
        yield parse_status.parse_row(line, headers, detail), line + "\n" + detail


def summary_line(set_aside_counts: dict) -> str:
    total = sum(set_aside_counts.values())
    if not total:
        return "Set aside: none"
    parts = ", ".join(f"{k} {n}" for k, n in sorted(set_aside_counts.items()))
    return f"Set aside: {total} ({parts})"


def classify(text: str, policy: str, classes: list[str]) -> dict:
    candidates, by_likelihood, ids = [], {}, []
    for parsed, row_text in row_records(text):
        if parsed.get("set_aside") and not parsed.get("completed"):
            key = parsed.get("likelihood") or "unrated"
            by_likelihood[key] = by_likelihood.get(key, 0) + 1
            ids.append(parsed.get("id"))
            continue
        record = classify_row(parsed, row_text, policy, classes)
        if record:
            candidates.append(record)
    counts = {a: sum(1 for c in candidates if c["action"] == a) for a in ("auto", "ask", "none")}
    return {
        "policy": policy,
        "protected_classes": classes,
        "candidates": candidates,
        "counts": counts,
        "set_aside": {"count": len(ids), "by_likelihood": by_likelihood, "ids": ids},
        "summary_line": summary_line(by_likelihood),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify rows for setting aside by likelihood (read-only).")
    sub = parser.add_subparsers(dest="action", required=True)
    c = sub.add_parser("classify", help="list set-aside candidates and the current set-aside count")
    c.add_argument("--file", required=True, help="ledger file")
    c.add_argument("--dir", default=None, help="ledger directory (reads the registry)")
    c.add_argument("--policy", choices=POLICIES, default=None, help="override park_policy")
    c.add_argument("--classes", default=None, help="override park_protected_classes (comma-separated)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(json.dumps({"error": f"file not found: {path}"}), file=sys.stderr)
        return 2
    settings = registry_settings(Path(args.dir) if args.dir else None)
    policy = args.policy or str(settings.get("park_policy") or DEFAULT_POLICY).strip().lower()
    if policy not in POLICIES:
        print(json.dumps({"error": f"unknown park_policy: {policy!r} (expected off, ask or auto)"}), file=sys.stderr)
        return 2
    classes = parse_classes(args.classes if args.classes is not None else settings.get("park_protected_classes"))
    result = {"file": str(path)}
    result.update(classify(path.read_text(encoding="utf-8", errors="replace"), policy, classes))
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
