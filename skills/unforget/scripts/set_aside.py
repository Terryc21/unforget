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
      * its rating has no `@basis:`, or only `@basis:reasoned` (one judgment from
        reading code); a standing policy needs measured, reproduced or reviewed;
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
  python3 set_aside.py convert --file <UNFORGET.md> [--dir <ledger-dir>] [--apply]

`convert` turns written "Likelihood: Rare (…)" prose into tokens. It previews by
default. For each unfinished row whose prose names exactly one value on the
scale, it proposes `@likelihood:<value>` plus a `@basis:` read from the same
prose (measured / reproduced / reviewed words, else reasoned). Rows naming
several values, none, or with no status token are listed for a person. With
--apply it writes a timestamped backup, inserts only the tokens, and refuses if
any row's status, completion or release gating would change. It never sets a
row aside and never changes a Target.

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
import datetime as dt
import json
import os
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
    basis = parsed.get("basis")
    if basis not in parse_status.POLICY_BASES:
        reasons.append("rating rests on reasoning only (@basis:reasoned)" if basis == "reasoned"
                       else "rating has no @basis: recorded")
    reasons += protection_reasons(parsed, row_text, classes)
    eligibility = "needs-user" if reasons else "policy-eligible"
    if policy == "off":
        action = "none"
    elif policy == "auto" and eligibility == "policy-eligible":
        action = "auto"
    else:
        action = "ask"
    return {"id": parsed.get("id"), "likelihood": likelihood, "basis": basis,
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


# --- convert: written likelihood prose -> tokens ---------------------------------

DEFAULT_REVIEWED_WORDS = ["reviewed", "reviewer", "second opinion", "fresh-context", "fresh context"]
DEFAULT_MEASURED_WORDS = ["measured", "census", "telemetry", "crash report", "crash data",
                          "analytics", "sentry"]
PROSE_RE = re.compile(r"Likelihood:\s*(.*)", re.I)
SCALE_WORD_RE = re.compile(
    r"(?<![\w-])(not applicable|certain|probable|likely|unlikely|rare|improbable|uncertain|n/a)(?![\w-])",
    re.I)
LEADING_TOKENS_RE = re.compile(r"^(\s*(?:`?@(?:status|verified):[a-z-]+`?\s*)+)")
# Most likely first: a multi-part row takes its most likely part.
FREQUENCY_ORDER = ("certain", "probable", "likely", "unlikely", "rare", "improbable")
NEUTRAL_KEYS = ("status", "effective_status", "completed", "archivable", "blocks_release",
                "issues", "target", "verified")


def word_list(value, default):
    if value is None:
        return list(default)
    return [w.strip().lower() for w in str(value).split(",") if w.strip()]


def prose_segment(text: str) -> str | None:
    """The rating clause after "Likelihood:", up to the end of its sentence."""
    match = PROSE_RE.search(text)
    if not match:
        return None
    rest = match.group(1)
    end = re.search(r"\.(?:\s|$)", rest)
    return (rest[:end.start()] if end else rest).strip()


def read_basis(segment: str, reviewed: list[str], measured: list[str]) -> str:
    low = segment.lower()
    if any(w in low for w in measured):
        return "measured"
    if re.search(r"(?<!not )(?<!un)\breproduced\b", low):
        return "reproduced"
    if any(w in low for w in reviewed):
        return "reviewed"
    return "reasoned"


def plan_conversion(text: str, reviewed: list[str], measured: list[str]) -> dict:
    lines = text.split("\n")
    details = parse_status.detail_blocks(text)
    add, needs_person, already = [], [], []
    row_no = {}
    for n, line in enumerate(lines):
        if parse_status.ROW_ID_RE.match(line):
            row_no.setdefault(line, []).append(n)
    for line, headers in parse_status.row_contexts(text):
        parsed = parse_status.parse_row(line, headers)
        rid = parsed["id"]
        if parsed["completed"]:
            continue
        cells = parse_status.data_cells(line)
        status = parse_status.status_cell(line)
        segment = None
        for source in [status] + cells + [details.get(rid, "")]:
            segment = prose_segment(source)
            if segment is not None:
                break
        if segment is None:
            continue
        if parsed.get("likelihood"):
            already.append(rid)
            continue
        values = {("n/a" if v.lower() == "not applicable" else v.lower())
                  for v in SCALE_WORD_RE.findall(segment)}
        evidence = segment[:160]
        if len(values) != 1:
            record = {"id": rid, "evidence": evidence,
                      "reason": "names several values" if values else "names no value on the scale"}
            # The format's rule is "the most likely part decides". Suggest it only when
            # every part is on the frequency scale; an uncertain or n/a part needs a person.
            if values and values <= set(FREQUENCY_ORDER):
                record["suggested"] = min(values, key=FREQUENCY_ORDER.index)
            needs_person.append(record)
            continue
        if not parsed["token_present"]:
            needs_person.append({"id": rid, "evidence": evidence,
                                 "reason": "no @status token to place it after"})
            continue
        add.append({"id": rid, "value": values.pop(), "basis": read_basis(segment, reviewed, measured),
                    "evidence": evidence, "line": row_no[line].pop(0)})
    return {"add": add, "needs_person": needs_person, "already_tokened": already}


def insert_tokens(line: str, value: str, basis: str) -> str | None:
    """Insert the tokens after the status/verified tokens of the Status cell."""
    parts = parse_status.split_row(line)
    for i in range(len(parts) - 1, -1, -1):
        if parse_status.STATUS_RE.search(parts[i]):
            match = LEADING_TOKENS_RE.match(parts[i])
            if not match:
                return None
            head = match.group(1)
            sep = "" if head.endswith(" ") else " "
            parts[i] = head + sep + f"`@likelihood:{value}` `@basis:{basis}` " + parts[i][match.end():]
            return "|".join(parts)
    return None


def apply_conversion(path: Path, text: str, plan: dict) -> dict:
    lines = text.split("\n")
    refused = []
    for item in plan["add"]:
        new = insert_tokens(lines[item["line"]], item["value"], item["basis"])
        if new is None:
            refused.append(item["id"])
            continue
        lines[item["line"]] = new
    new_text = "\n".join(lines)
    # Lossless: removing exactly the inserted tokens must give back the original.
    stripped = re.sub(r"`@likelihood:[a-z/-]+` `@basis:[a-z-]+` ", "", new_text)
    if stripped != text and stripped.replace("` `@likelihood", "``@likelihood") != text:
        return {"applied": False, "error": "refused: the edit would change more than the inserted tokens"}
    before = parse_status.parse_file(text)
    after = parse_status.parse_file(new_text)
    if len(before) != len(after) or any(
            a[k] != b[k] for a, b in zip(before, after) for k in NEUTRAL_KEYS):
        return {"applied": False, "error": "refused: a row's status, completion or release gating would change"}
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    if backup.exists():
        return {"applied": False, "error": f"refused: backup {backup.name} already exists"}
    backup.write_text(text, encoding="utf-8")
    tmp = path.with_name(f".{path.name}.convert-tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)
    return {"applied": True, "backup": str(backup), "refused": refused}


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify rows for setting aside by likelihood (read-only).")
    sub = parser.add_subparsers(dest="action", required=True)
    c = sub.add_parser("classify", help="list set-aside candidates and the current set-aside count")
    c.add_argument("--file", required=True, help="ledger file")
    c.add_argument("--dir", default=None, help="ledger directory (reads the registry)")
    c.add_argument("--policy", choices=POLICIES, default=None, help="override park_policy")
    c.add_argument("--classes", default=None, help="override park_protected_classes (comma-separated)")
    v = sub.add_parser("convert", help="turn written likelihood prose into tokens (preview unless --apply)")
    v.add_argument("--file", required=True, help="ledger file")
    v.add_argument("--dir", default=None, help="ledger directory (reads likelihood_*_words from the registry)")
    v.add_argument("--apply", action="store_true", help="write the tokens (after a timestamped backup)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(json.dumps({"error": f"file not found: {path}"}), file=sys.stderr)
        return 2
    settings = registry_settings(Path(args.dir) if args.dir else None)
    if args.action == "convert":
        text = path.read_text(encoding="utf-8")
        plan = plan_conversion(text,
                               word_list(settings.get("likelihood_reviewed_words"), DEFAULT_REVIEWED_WORDS),
                               word_list(settings.get("likelihood_measured_words"), DEFAULT_MEASURED_WORDS))
        result = {"file": str(path), "applied": False,
                  "counts": {"add": len(plan["add"]), "needs_person": len(plan["needs_person"]),
                             "already_tokened": len(plan["already_tokened"])},
                  "add": [{k: v for k, v in a.items() if k != "line"} for a in plan["add"]],
                  "needs_person": plan["needs_person"]}
        if args.apply and plan["add"]:
            result.update(apply_conversion(path, text, plan))
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0 if not result.get("error") else 1
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
