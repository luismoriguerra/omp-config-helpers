#!/usr/bin/env python3
"""Diff the omp model catalog for allowed providers against the last saved snapshot.

  catalog_diff.py               # show added / removed / changed models since the snapshot
  catalog_diff.py --refresh     # run `omp models refresh` first (network)
  catalog_diff.py --save        # after showing the diff, store the current catalog as the new snapshot

First run (no snapshot) saves a baseline and exits.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT = Path.home() / ".omp" / "presets" / "catalog-snapshot.json"
CONFIG_FILES = [Path.home() / ".omp" / "agent" / "config.yml", *sorted((Path.home() / ".omp" / "presets").glob("*.yml"))]
FIELDS = ("contextWindow", "maxTokens", "thinking", "input", "cost")


def omp(*args):
    res = subprocess.run(["omp", *args], capture_output=True, text=True, cwd=tempfile.gettempdir())
    if res.returncode != 0:
        sys.exit(f"omp {' '.join(args)} failed: {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout


def current(allowed):
    models = json.loads(omp("models", "--kind", "all", "--json"))["models"]
    out = {}
    for m in models:
        if m["provider"] in allowed:
            cost = m.get("cost") or {}
            out[m["selector"]] = {
                "kind": m.get("kind"),
                "name": m.get("name"),
                "contextWindow": m.get("contextWindow"),
                "maxTokens": m.get("maxTokens"),
                "thinking": m.get("thinking"),
                "input": m.get("input"),
                "cost": {"input": cost.get("input"), "output": cost.get("output")},
            }
    return out


def fmt(sel, m):
    def k(n):
        return "-" if not n else (f"{n / 1_000_000:g}M" if n >= 1_000_000 else f"{n // 1000}K")
    cost = m.get("cost") or {}
    img = "img" if "image" in (m.get("input") or []) else "text"
    return (f"{sel:45} ctx {k(m.get('contextWindow')):>5}  out {k(m.get('maxTokens')):>5}  {img:4}  "
            f"thinking {','.join(m.get('thinking') or ['-'])}  $in/out {cost.get('input')}/{cost.get('output')}")


def referenced_selectors():
    """Selectors used in active YAML (comments stripped; selectors never contain '#')."""
    found = set()
    for path in CONFIG_FILES:
        if path.exists():
            for line in path.read_text().splitlines():
                active = line.split("#", 1)[0]
                found.update(re.findall(r"[a-z0-9-]+/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)?", active))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allowed", default=os.environ.get("OMP_ALLOWED_PROVIDERS", "github-copilot,cursor"))
    ap.add_argument("--refresh", action="store_true", help="run `omp models refresh` before reading the catalog")
    ap.add_argument("--save", action="store_true", help="store the current catalog as the new snapshot after diffing")
    args = ap.parse_args()
    allowed = {p.strip() for p in args.allowed.split(",") if p.strip()}

    if args.refresh:
        omp("models", "refresh")
    now = current(allowed)
    print(f"omp {omp('--version').strip()}; providers {sorted(allowed)}; {len(now)} models now")

    if not SNAPSHOT.exists():
        SNAPSHOT.write_text(json.dumps({"taken": datetime.now(timezone.utc).isoformat(), "models": now}, indent=1))
        print(f"no snapshot yet; saved baseline to {SNAPSHOT}")
        return 0

    old_doc = json.loads(SNAPSHOT.read_text())
    old = old_doc["models"]
    print(f"snapshot from {old_doc['taken']}: {len(old)} models")

    added = sorted(set(now) - set(old))
    removed = sorted(set(old) - set(now))
    changed = []
    for sel in sorted(set(now) & set(old)):
        diffs = [f"{f}: {old[sel].get(f)} -> {now[sel].get(f)}" for f in FIELDS if old[sel].get(f) != now[sel].get(f)]
        if diffs:
            changed.append((sel, diffs))

    print(f"\n## Added ({len(added)})")
    for sel in added:
        print("  + " + fmt(sel, now[sel]))
    print(f"\n## Removed ({len(removed)})")
    refs = referenced_selectors()
    for sel in removed:
        flag = "  <-- REFERENCED IN YOUR CONFIG/PRESETS" if sel in refs else ""
        print(f"  - {sel}{flag}")
    print(f"\n## Changed ({len(changed)})")
    for sel, diffs in changed:
        print(f"  ~ {sel}: " + "; ".join(diffs))

    broken = [s for s in refs if s.split("/", 1)[0] in allowed and s not in now and not s.endswith("/*")]
    if broken:
        print(f"\n## Config references not in the current catalog: {sorted(broken)}")

    if args.save:
        SNAPSHOT.write_text(json.dumps({"taken": datetime.now(timezone.utc).isoformat(), "models": now}, indent=1))
        print(f"\nsnapshot updated: {SNAPSHOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
