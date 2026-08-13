#!/usr/bin/env python3
r"""Display-preference resolution: saved registry prefs -> effective list/scan settings.

Implements the deterministic half of the display-preference interview (see
reference/commands.md § Display-preference interview). The split is the same one
defer_tally.py draws: the JUDGMENT (which questions to ask, how to word them,
whether the user's answer makes sense) belongs to the LLM running the interview;
the MECHANICS (precedence, defaults, validation, building a safe merge payload)
belong here.

Three jobs:

  1. RESOLVE (the hot path): given the registry's saved prefs and whatever flags
     were explicitly passed on this call, compute the settings `list`/`scan`
     should actually use. Precedence is fixed and non-negotiable:

         explicit flag  >  saved registry pref  >  hardcoded default

     An explicit flag wins for THAT CALL ONLY and is never written back — the
     saved pref is changed only by an interview (`--fresh`), never as a side
     effect of a one-off `--view=next`.

  2. FRAMING: report whether this is a true first run (no display_prefs_set in
     the registry) or a re-run, so `--fresh` can lead with the right line. The
     spec calls this presentation-only, one code path, not two.

  3. BUILD-PATCH: turn a set of interview answers into a payload for
     `registry.py write --merge`. Only answered keys are included; skipped
     questions are omitted so the merge leaves their prior value untouched.
     display_prefs_set is always set on any completed interview.

     !! The emitted payload is ONLY safe with `registry.py write --merge`. !!
     A bare write of a partial payload replaces the whole block: measured
     2026-08-13, a one-key write against a 9-key/3-ledger registry left 9 nulls
     and 0 registered ledgers. `--merge` is not optional here; `build-patch`
     says so in its own output (`requires_merge: true`) so a caller that
     forwards the payload blindly still carries the warning.

Usage:
  # Resolve effective settings (pass only the flags the user actually gave):
  python3 display_prefs.py resolve --dir <ledger-dir> \
      [--view MODE] [--group-by AXIS] [--section NAME] [--verbosity MODE] \
      [--term-width N]

  # Ask which framing --fresh should use:
  python3 display_prefs.py framing --dir <ledger-dir>

  # Build a --merge payload from interview answers (omit what was skipped):
  python3 display_prefs.py build-patch \
      [--view MODE] [--group-by AXIS] [--section NAME] [--verbosity MODE] \
      [--archive-nudge N] [--stale-this N] [--stale-next N] \
      [--stale-later N] [--stale-someday N]

  python3 display_prefs.py --help

Output (resolve, stdout, JSON):
  {
    "view": "all", "group_by": "target", "section": null,
    "verbosity": "auto", "effective_width": "full"|"compact"|null,
    "archive_nudge_threshold": 5,
    "stale_days": {"this": 30, "next": 90, "later": 180, "someday": 365},
    "sources": {"view": "flag"|"registry"|"default", ...},
    "prefs_set": true|false,
    "advisory": "<one-line summary>"
  }

Exit codes:
  0  ok
  2  usage error / bad value / dir not found
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # noqa: E402

# --- the enums, mirroring the flags these resolve into ----------------------
VIEWS = ("all", "open", "done", "split", "next")
GROUP_BYS = ("target", "section", "none")
# `auto` keeps the terminal-width auto-detection (reference/commands.md §
# Terminal-aware rendering). It is the DEFAULT and the skip-value on purpose: a
# pinned `full` permanently defeats the <120-column fallback that exists because
# the 10-column table is unreadable there.
VERBOSITIES = ("auto", "full", "compact")
# `--section=` is singular in every documented usage, so a saved pref is one
# section or all -- never an arbitrary subset (that would imply a filter
# capability the underlying flag does not have).
SECTIONS = ("all", "paused", "spillover", "audit", "observed")

DEFAULTS = {
    "view": "all",
    "group_by": "target",
    "section": None,          # None == every section, matching a bare `list`
    "verbosity": "auto",
    "archive_nudge_threshold": 5,
    "stale_days": {"this": 30, "next": 90, "later": 180, "someday": 365},
}

# Width at which the auto-fallback switches to the 6-column projection.
COMPACT_BELOW_COLS = 120

_STALE_KEYS = {
    "this": "stale_days_this",
    "next": "stale_days_next",
    "later": "stale_days_later",
    "someday": "stale_days_someday",
}


def _read_global(dir_path: Path) -> tuple[dict, str | None]:
    """Return (global config, error). A missing registry is NOT an error --
    it just means no saved prefs, so everything falls back to defaults."""
    reg = registry.read_registry(dir_path)
    if "error" in reg:
        return {}, reg["error"]
    return reg.get("global") or {}, None


def _as_int(val, fallback: int) -> int:
    """Registry values are strings (they come from a markdown table). A
    non-numeric or absent value falls back rather than raising -- a malformed
    tunable must never take down a read command."""
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return fallback


def _prefs_set(global_cfg: dict) -> bool:
    return str(global_cfg.get("display_prefs_set") or "").strip().lower() == "true"


def resolve(dir_path: Path, flags: dict, term_width: int | None) -> dict:
    global_cfg, err = _read_global(dir_path)
    prefs_set = _prefs_set(global_cfg)
    sources: dict[str, str] = {}

    def pick(name: str, reg_key: str, valid: tuple[str, ...] | None):
        """explicit flag > saved registry pref > hardcoded default."""
        flag_val = flags.get(name)
        if flag_val:
            sources[name] = "flag"
            return flag_val
        # A saved pref only applies once an interview has actually completed.
        # A stray display_* key with no display_prefs_set is treated as absent,
        # so a half-written registry can't silently change how `list` renders.
        if prefs_set:
            reg_val = (global_cfg.get(reg_key) or "").strip() or None
            if reg_val and (valid is None or reg_val in valid):
                sources[name] = "registry"
                return reg_val
        sources[name] = "default"
        return DEFAULTS[name]

    view = pick("view", "display_view", VIEWS)
    group_by = pick("group_by", "display_group_by", GROUP_BYS)
    verbosity = pick("verbosity", "display_verbosity", VERBOSITIES)

    section = pick("section", "display_sections", SECTIONS)
    # `all` is how the registry spells "every section"; the flag layer spells it
    # as absence. Normalize to the flag layer's vocabulary.
    if section == "all":
        section = None

    # Resolve `auto` against the actual terminal only when a width is supplied;
    # otherwise report null and let the caller do its own detection.
    if verbosity == "auto":
        effective_width = (None if term_width is None
                           else ("compact" if term_width < COMPACT_BELOW_COLS else "full"))
    else:
        effective_width = verbosity

    nudge_src = "registry" if (prefs_set and global_cfg.get("archive_nudge_threshold")) else "default"
    archive_nudge = _as_int(global_cfg.get("archive_nudge_threshold"),
                            DEFAULTS["archive_nudge_threshold"]) if prefs_set \
        else DEFAULTS["archive_nudge_threshold"]
    sources["archive_nudge_threshold"] = nudge_src

    stale_days = {}
    for tier, reg_key in _STALE_KEYS.items():
        fallback = DEFAULTS["stale_days"][tier]
        stale_days[tier] = (_as_int(global_cfg.get(reg_key), fallback)
                            if prefs_set else fallback)
    sources["stale_days"] = ("registry" if prefs_set and any(
        global_cfg.get(k) for k in _STALE_KEYS.values()) else "default")

    flagged = [k for k, v in sources.items() if v == "flag"]
    if not prefs_set:
        advisory = ("no saved display preference (run `list --fresh` to set one); "
                    "using defaults" + (f", overridden by flag: {', '.join(flagged)}" if flagged else ""))
    else:
        advisory = ("saved preference applied"
                    + (f"; overridden this call by flag: {', '.join(flagged)}" if flagged else ""))
    if err:
        advisory = f"{err}; using defaults"

    return {
        "view": view,
        "group_by": group_by,
        "section": section,
        "verbosity": verbosity,
        "effective_width": effective_width,
        "archive_nudge_threshold": archive_nudge,
        "stale_days": stale_days,
        "sources": sources,
        "prefs_set": prefs_set,
        "advisory": advisory,
    }


def framing(dir_path: Path) -> dict:
    """Which lead-in `--fresh` should use. Presentation only -- the questions
    themselves are identical either way (spec: one code path, not two)."""
    global_cfg, err = _read_global(dir_path)
    prefs_set = _prefs_set(global_cfg)
    current = {k: global_cfg.get(f"display_{k}") for k in ("view", "group_by", "verbosity", "sections")}
    current = {k: v for k, v in current.items() if v}
    if prefs_set:
        summary = ", ".join(f"{k}={v}" for k, v in current.items()) or "(no fields set)"
        lead = f"Currently: {summary}. Want to change it?"
    else:
        lead = "No display preference saved yet for this ledger."
    return {
        "first_run": not prefs_set,
        "current": current,
        "lead_in": lead,
        "advisory": err or ("re-run framing" if prefs_set else "first-run framing"),
    }


def build_patch(answers: dict) -> dict:
    """Interview answers -> a registry.py --merge payload.

    Only answered keys are emitted. A skipped question must NOT appear, so the
    merge leaves its prior value alone -- emitting an explicit null would CLEAR
    it, which is the opposite of skipping.
    """
    global_patch: dict[str, str] = {}
    mapping = {
        "view": "display_view",
        "group_by": "display_group_by",
        "verbosity": "display_verbosity",
        "section": "display_sections",
        "archive_nudge": "archive_nudge_threshold",
        "stale_this": "stale_days_this",
        "stale_next": "stale_days_next",
        "stale_later": "stale_days_later",
        "stale_someday": "stale_days_someday",
    }
    for ans_key, reg_key in mapping.items():
        val = answers.get(ans_key)
        if val is not None and str(val) != "":
            global_patch[reg_key] = str(val)

    # Always stamp this, even for a 1-answer Quick interview: it is what makes
    # the NEXT --fresh use re-run framing instead of first-run framing.
    global_patch["display_prefs_set"] = "true"

    return {
        "global": global_patch,
        "requires_merge": True,
        "write_command": ("python3 scripts/registry.py write --dir <ledger-dir> "
                          "--json <payload> --merge"),
        "advisory": (f"{len(global_patch) - 1} answered key(s) + display_prefs_set; "
                     "MUST be written with --merge (a bare write replaces the whole "
                     "block and empties the Ledgers table)"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve saved display preferences into effective list/scan settings.")
    sub = parser.add_subparsers(dest="action", required=True)

    r = sub.add_parser("resolve", help="compute effective settings for this call")
    r.add_argument("--dir", required=True, help="ledger directory (holds README.md)")
    r.add_argument("--view", choices=VIEWS, default=None, help="explicit --view for this call")
    r.add_argument("--group-by", dest="group_by", choices=GROUP_BYS, default=None)
    r.add_argument("--section", choices=SECTIONS, default=None)
    r.add_argument("--verbosity", choices=VERBOSITIES, default=None)
    r.add_argument("--term-width", dest="term_width", type=int, default=None,
                   help="terminal columns; resolves verbosity=auto to full/compact")

    f = sub.add_parser("framing", help="first-run vs re-run lead-in for --fresh")
    f.add_argument("--dir", required=True, help="ledger directory")

    b = sub.add_parser("build-patch", help="interview answers -> a --merge payload")
    b.add_argument("--view", choices=VIEWS, default=None)
    b.add_argument("--group-by", dest="group_by", choices=GROUP_BYS, default=None)
    b.add_argument("--section", choices=SECTIONS, default=None)
    b.add_argument("--verbosity", choices=VERBOSITIES, default=None)
    b.add_argument("--archive-nudge", dest="archive_nudge", type=int, default=None)
    b.add_argument("--stale-this", dest="stale_this", type=int, default=None)
    b.add_argument("--stale-next", dest="stale_next", type=int, default=None)
    b.add_argument("--stale-later", dest="stale_later", type=int, default=None)
    b.add_argument("--stale-someday", dest="stale_someday", type=int, default=None)

    args = parser.parse_args()

    if args.action == "build-patch":
        result = build_patch(vars(args))
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 0

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(json.dumps({"error": f"not a directory: {dir_path}"}), file=sys.stderr)
        return 2

    if args.action == "framing":
        result = framing(dir_path)
    else:
        flags = {"view": args.view, "group_by": args.group_by,
                 "section": args.section, "verbosity": args.verbosity}
        result = resolve(dir_path, flags, args.term_width)

    json.dump(result, sys.stdout); sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
