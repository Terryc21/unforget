#!/usr/bin/env python3
"""Fuzzy-merge duplicate finding candidates across surfaces.

Reads a JSON candidate list (the output of `scan_surfaces.py`, or any equivalent
producer with the same shape) and merges candidates whose Finding headlines have
substantial token overlap. Each merged candidate carries a `sources` list so the
multi-surface pointer can be rendered into the Finding cell.

Algorithm:
  1. Flatten all candidates from all surfaces into a single list, preserving
     each candidate's original surface name.
  2. Compute a normalized token set per candidate (lowercase, alphanumeric,
     stop-words removed, length >= 3).
  3. Pairwise compare token sets via Jaccard similarity. Merge candidates whose
     similarity >= --threshold (default 0.65).
  4. Merging is greedy (single-pass): each candidate is either added as a new
     cluster or merged into the first existing cluster it overlaps with.
  5. Tie-breaking: when a candidate overlaps with multiple clusters, merge into
     the one with the highest similarity.

The script does not invent Finding text; if a candidate has no `finding` or
`title` field, the script falls back to the `path` (or empty string) as the
headline. Downstream tools should set a real headline before importing.

Usage:
  python3 dedup_findings.py --candidates <file.json>
  python3 dedup_findings.py --candidates <file.json> --threshold 0.7
  cat candidates.json | python3 dedup_findings.py --candidates -
  python3 dedup_findings.py --help

Input shape (subset; matches scan_surfaces.py output):
  {
    "surfaces": {
      "<surface_name>": {"candidates": [{...}, ...]},
      ...
    }
  }

Output (stdout, JSON):
  {
    "input_candidate_count": N,
    "output_candidate_count": M,
    "threshold": 0.65,
    "candidates": [
      {
        "headline": "<headline>",
        "sources": [
          {"surface": "<name>", "candidate": {...original...}, "similarity_to_lead": 1.0},
          ...
        ]
      },
      ...
    ]
  }

Exit codes: 0 on success, 2 on usage error / parse error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "what",
    "which", "their", "there", "here", "have", "has", "had", "are", "was", "were",
    "but", "not", "can", "will", "should", "would", "could", "may", "might",
    "all", "any", "some", "one", "two", "out", "your", "you", "our", "its", "it's",
    "as", "is", "be", "to", "of", "in", "on", "at", "or", "an", "if", "by",
    "md", "yml", "yaml", "json", "txt",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def headline(c: dict) -> str:
    for key in ("headline", "finding", "title", "snippet", "path"):
        if c.get(key):
            return str(c[key])
    return ""


def tokenize(text: str) -> set[str]:
    return {
        t.lower()
        for t in TOKEN_RE.findall(text)
        if len(t) >= 3 and t.lower() not in STOP_WORDS
    }


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fuzzy-merge duplicate finding candidates across surfaces."
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to JSON file (or '-' for stdin)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Jaccard similarity threshold for merging (0.0-1.0; default 0.65)",
    )
    args = parser.parse_args()

    if not (0.0 <= args.threshold <= 1.0):
        print(json.dumps({"error": "--threshold must be in [0.0, 1.0]"}), file=sys.stderr)
        return 2

    if args.candidates == "-":
        raw = sys.stdin.read()
    else:
        path = Path(args.candidates)
        if not path.exists():
            print(json.dumps({"error": f"file not found: {path}"}), file=sys.stderr)
            return 2
        raw = path.read_text(encoding="utf-8", errors="replace")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}), file=sys.stderr)
        return 2

    surfaces = data.get("surfaces", {})
    flat: list[tuple[str, dict, set[str], str]] = []
    for surface_name, payload in surfaces.items():
        for cand in payload.get("candidates", []):
            text = headline(cand)
            tokens = tokenize(text)
            flat.append((surface_name, cand, tokens, text))

    clusters: list[dict] = []
    for surface_name, cand, tokens, text in flat:
        best_idx = -1
        best_sim = 0.0
        for idx, cluster in enumerate(clusters):
            sim = jaccard(tokens, cluster["tokens"])
            if sim > best_sim:
                best_sim = sim
                best_idx = idx
        if best_idx >= 0 and best_sim >= args.threshold:
            cluster = clusters[best_idx]
            cluster["sources"].append(
                {
                    "surface": surface_name,
                    "candidate": cand,
                    "similarity_to_lead": round(best_sim, 3),
                }
            )
            cluster["tokens"] |= tokens
        else:
            clusters.append(
                {
                    "headline": text,
                    "tokens": tokens,
                    "sources": [
                        {
                            "surface": surface_name,
                            "candidate": cand,
                            "similarity_to_lead": 1.0,
                        }
                    ],
                }
            )

    # Strip token sets from output (they're internal)
    output_clusters = [
        {"headline": c["headline"], "sources": c["sources"]} for c in clusters
    ]

    result = {
        "input_candidate_count": len(flat),
        "output_candidate_count": len(output_clusters),
        "threshold": args.threshold,
        "candidates": output_clusters,
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
