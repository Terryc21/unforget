#!/usr/bin/env python3
r"""The deferral gate's deterministic half: tripwire routing + session accounting.

Implements the mechanical parts of the deferral gate (see
reference/deferral-gate.md, from the Deferral Gate design spec). The gate fires
at `add` — the moment work is about to become a row — and has three jobs:

  1. TRIPWIRE (§2): a would-be row that is Trivial-effort AND ⚪ 1-file does not
     get deferred; it routes to DO-IT-NOW. UNLESS it is destructive (on the
     always-stop list), in which case it routes to NEEDS-APPROVAL (trivial ≠
     safe) — never auto-done.
  2. WHY-NOT-NOW (§3): everything that clears the tripwire must name an allow-list
     deferral reason; a would-be row with no valid reason routes to DO-IT-NOW.
     (The *judgment* of whether a stated reason really holds is the LLM's, per the
     spec's honest-limit note §3d — this script records the reason and enforces
     that SOME allow-list reason was named, not that it is true.)
  3. ACCOUNTING (§4): a per-session defer/fix tally is the load-bearing backstop.
     A single well-worded justification hides a bad deferral; a 7:2 defer/fix
     ratio does not. This script keeps the tally and flags a defer-heavy session.

Deterministic → here. Judgment (is this trivial? is the reason legitimate?) →
the LLM, guided by reference/deferral-gate.md. This script is given the
classification and does the routing + counting math.

The tally lives in a small `.unforget-session.json` state file in the ledger
directory — EPHEMERAL, per-session, git-ignored (it is churn, not a record). The
registry (README-canonical) holds the *thresholds*; the state file holds the
*counts*. The two threshold knobs (ratio_flag_threshold default 3,
stale_trivial_sessions) are read from the registry global block when a --dir is
given, else defaults apply.

Usage:
  # Route a would-be deferral through the tripwire + why-not-now gate:
  python3 defer_tally.py gate \
      --effort Trivial --blast "⚪ 1 file" \
      [--destructive] [--reason external-block] [--policy aggressive]

  # Record an outcome into the session tally (call after the gate resolves):
  python3 defer_tally.py record --dir <ledger-dir> \
      --outcome deferred --reason external-block
  python3 defer_tally.py record --dir <ledger-dir> --outcome fixed-now

  # Read the current session readout (for `list` / session-end summary):
  python3 defer_tally.py readout --dir <ledger-dir>

  # Start a fresh session tally (zeroes the counts, keeps threshold config):
  python3 defer_tally.py reset --dir <ledger-dir>

  python3 defer_tally.py --help

Output (gate, stdout, JSON):
  {
    "route": "do-now" | "defer" | "needs-approval",
    "reason_required": true|false,     # true when route=defer and no reason named
    "reason": "<allow-list key>"|null,
    "reason_valid": true|false,        # the named reason is on the allow-list
    "trivial": true|false,             # tripwire matched (Trivial + 1-file)
    "destructive": true|false,
    "advisory": "<one-line explanation of the routing>"
  }

Output (record/readout, stdout, JSON):
  {
    "session": {"fixed_now": N, "deferred": M, "reasons": {"<key>": N, ...}},
    "ratio": <deferred/fixed or null when fixed=0>,
    "flag": true|false,                # deferred >= ratio_threshold * fixed
    "threshold": <ratio_flag_threshold>,
    "readout": "This session: N fixed inline · M deferred (reasons: ...).",
    "advisory": "<flag prompt when flag=true, else ''>"
  }

Exit codes:
  0  ok (gate resolved / tally read/written)
  1  gate wants a reason it didn't get (route=defer, reason_required=true), OR
     a defer-heavy session flag is raised (readout/record with flag=true)
  2  usage error / dir not found
"""
import argparse
import json
import sys
from pathlib import Path

STATE_NAME = ".unforget-session.json"

# The allow-list — the ONLY valid reasons to defer (spec §3a). Keys are the tags
# stored in a row's `Deferred because:` field; the descriptions are for the
# readout and for the reference doc's cross-check.
ALLOW_LIST = {
    "user-decision": "needs a decision only the user can make (one-way door, product call, naming)",
    "scaffolding": "needs tools / a device / a second account / a build this session can't produce",
    "scope": "genuinely out of scope AND non-trivial — doing it now would balloon the task",
    "external-block": "blocked on something external (CI, a third party, a deploy, another person)",
}

# The trivial tripwire reads the two columns the row would carry anyway (§2). A
# blast-radius cell counts as "1 file" when it names one file; the ⚪ marker and
# the words "1 file" are the recognized forms.
TRIVIAL_EFFORTS = {"trivial"}
ONE_FILE_MARKERS = ("⚪", "1 file", "1-file", "single file", "one file")

# Policy 1 settings (spec §5). Only "aggressive" is the recommended default;
# the others relax the tripwire but never the always-stop rule.
POLICIES = {"aggressive", "conservative", "same-file-only"}

DEFAULT_RATIO_THRESHOLD = 3


# --- tripwire + gate -------------------------------------------------------

def is_trivial(effort: str, blast: str) -> bool:
    """§2: Trivial effort AND a 1-file blast radius."""
    effort_trivial = (effort or "").strip().lower() in TRIVIAL_EFFORTS
    blast_lc = (blast or "").lower()
    one_file = any(m in blast_lc for m in ONE_FILE_MARKERS)
    return effort_trivial and one_file


def run_gate(effort: str, blast: str, destructive: bool,
             reason: str | None, policy: str, file_open: bool) -> dict:
    trivial = is_trivial(effort, blast)
    reason_key = (reason or "").strip().lower() or None
    reason_valid = reason_key in ALLOW_LIST if reason_key else False

    # Destructive ALWAYS wins over the do-now tripwire (§2, §7). Trivial ≠ safe:
    # a trivial-but-destructive change (delete a file, force-push, prod deploy)
    # is never auto-done — it routes to needs-approval and is raised at the end.
    if destructive:
        return {
            "route": "needs-approval",
            "reason_required": False,
            "reason": reason_key,
            "reason_valid": reason_valid,
            "trivial": trivial,
            "destructive": True,
            "advisory": "destructive change — never auto-done; log needs-approval and raise at end",
        }

    # The tripwire (§2), modulated by Policy 1 (§5).
    if trivial:
        if policy == "aggressive":
            do_now = True  # trivial → do-now regardless of scope
        elif policy == "same-file-only":
            do_now = file_open  # do-now only if the file is already open
        else:  # conservative — trivial-out-of-scope may defer, but do-now is still offered
            do_now = True
        if do_now:
            return {
                "route": "do-now", "reason_required": False,
                "reason": reason_key, "reason_valid": reason_valid,
                "trivial": True, "destructive": False,
                "advisory": "trivial + 1-file → do it now (report as an out-of-scope line if out of scope)",
            }
        # policy declined the do-now: fall through to the why-not-now gate.

    # WHY-NOT-NOW (§3): a non-trivial (or policy-deferred-trivial) item must name
    # an allow-list reason. No valid reason → do-now is the default, not a row.
    if reason_valid:
        return {
            "route": "defer", "reason_required": False,
            "reason": reason_key, "reason_valid": True,
            "trivial": trivial, "destructive": False,
            "advisory": f"legitimate deferral — {ALLOW_LIST[reason_key]}; record the reason in the row",
        }
    return {
        "route": "defer", "reason_required": True,
        "reason": reason_key, "reason_valid": False,
        "trivial": trivial, "destructive": False,
        "advisory": ("no valid deferral reason — do it now, or name which allow-list reason "
                     f"applies ({', '.join(ALLOW_LIST)})"),
    }


# --- session tally ---------------------------------------------------------

def _empty_tally() -> dict:
    return {"fixed_now": 0, "deferred": 0, "reasons": {}}


def load_state(dir_path: Path) -> dict:
    state_file = dir_path / STATE_NAME
    if not state_file.exists():
        return _empty_tally()
    try:
        obj = json.loads(state_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return _empty_tally()
    # normalize shape so a corrupt/partial file can't crash a record
    return {
        "fixed_now": int(obj.get("fixed_now", 0) or 0),
        "deferred": int(obj.get("deferred", 0) or 0),
        "reasons": dict(obj.get("reasons", {})),
    }


def save_state(dir_path: Path, tally: dict) -> None:
    (dir_path / STATE_NAME).write_text(
        json.dumps(tally, indent=2) + "\n", encoding="utf-8")


def read_ratio_threshold(dir_path: Path) -> int:
    """Read ratio_flag_threshold from the registry global block; else default."""
    try:
        # Local import so the script stays runnable if registry.py is absent.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import registry  # type: ignore
        reg = registry.read_registry(dir_path)
        val = (reg.get("global") or {}).get("ratio_flag_threshold")
        if val is not None:
            return int(str(val).strip())
    except (ImportError, ValueError, TypeError, OSError):
        pass
    return DEFAULT_RATIO_THRESHOLD


def summarize(tally: dict, threshold: int) -> dict:
    fixed = tally["fixed_now"]
    deferred = tally["deferred"]
    reasons = tally["reasons"]
    ratio = (deferred / fixed) if fixed else None
    # Flag when deferrals dominate. With zero fixes and any deferrals the pattern
    # can't be dismissed as "nothing was do-now", so we flag at >= threshold too.
    flag = (deferred >= threshold * fixed) if fixed else (deferred >= threshold)

    reason_bits = ", ".join(f"{n} {k}" for k, n in sorted(reasons.items())) or "none"
    readout = (f"This session: {fixed} fixed inline · {deferred} deferred "
               f"(reasons: {reason_bits}).")
    advisory = ""
    if flag and deferred > 0:
        advisory = (f"{deferred} deferred vs {fixed} fixed this session — worth a pass "
                    f"to see if any are actually do-now? (advisory, not blocking)")
    return {
        "session": tally,
        "ratio": round(ratio, 2) if ratio is not None else None,
        "flag": bool(flag and deferred > 0),
        "threshold": threshold,
        "readout": readout,
        "advisory": advisory,
    }


def record(dir_path: Path, outcome: str, reason: str | None) -> dict:
    tally = load_state(dir_path)
    if outcome == "fixed-now":
        tally["fixed_now"] += 1
    elif outcome == "deferred":
        tally["deferred"] += 1
        key = (reason or "unspecified").strip().lower()
        tally["reasons"][key] = tally["reasons"].get(key, 0) + 1
    save_state(dir_path, tally)
    return summarize(tally, read_ratio_threshold(dir_path))


# --- CLI -------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deferral gate: tripwire routing + session defer/fix accounting.")
    sub = parser.add_subparsers(dest="action", required=True)

    g = sub.add_parser("gate", help="route a would-be deferral (tripwire + why-not-now)")
    g.add_argument("--effort", default="", help="Fix Effort column value (e.g. Trivial/Small)")
    g.add_argument("--blast", default="", help="Blast Radius column value (e.g. '⚪ 1 file')")
    g.add_argument("--destructive", action="store_true",
                   help="the change is on the always-stop list (deletion/force-push/prod deploy)")
    g.add_argument("--reason", default=None, help="named allow-list deferral reason")
    g.add_argument("--policy", default="aggressive", choices=sorted(POLICIES),
                   help="Policy 1 strictness (default aggressive)")
    g.add_argument("--file-open", action="store_true",
                   help="(same-file-only policy) the target file is already open in the task")

    r = sub.add_parser("record", help="record an outcome into the session tally")
    r.add_argument("--dir", required=True, help="ledger directory (holds the session state file)")
    r.add_argument("--outcome", required=True, choices=["fixed-now", "deferred"])
    r.add_argument("--reason", default=None, help="allow-list reason (required for deferred)")

    ro = sub.add_parser("readout", help="print the current session tally readout")
    ro.add_argument("--dir", required=True, help="ledger directory")

    rs = sub.add_parser("reset", help="zero the session tally (keeps threshold config)")
    rs.add_argument("--dir", required=True, help="ledger directory")

    args = parser.parse_args()

    if args.action == "gate":
        result = run_gate(args.effort, args.blast, args.destructive,
                          args.reason, args.policy, args.file_open)
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 1 if result["reason_required"] else 0

    # every non-gate action needs a valid dir
    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(json.dumps({"error": f"not a directory: {dir_path}"}), file=sys.stderr)
        return 2

    if args.action == "record":
        result = record(dir_path, args.outcome, args.reason)
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 1 if result["flag"] else 0

    if args.action == "readout":
        tally = load_state(dir_path)
        result = summarize(tally, read_ratio_threshold(dir_path))
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 1 if result["flag"] else 0

    if args.action == "reset":
        save_state(dir_path, _empty_tally())
        result = summarize(_empty_tally(), read_ratio_threshold(dir_path))
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
