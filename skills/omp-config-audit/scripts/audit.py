#!/usr/bin/env python3
"""Read-only audit of omp model routing: global config plus every preset overlay.

Checks each role and fallback-chain selector against the live catalog, the
provider policy, and the routing rules in SKILL.md. Prints findings; never edits.
Exit code 1 when any ERROR is found.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

LEVELS = {"off", "minimal", "low", "medium", "high", "xhigh", "max", "auto", "inherit"}
MODEL_KIND_ROLES = {"web", "image", "speech", "dictation", "judge"}
SMALL_WORK_ROLES = ("tiny", "memory", "widget", "commit")
SEVERITIES = ["ERROR", "WARN", "INFO"]
PRESETS_DIR = Path.home() / ".omp" / "presets"


def omp(args, cwd, overlay=None):
    env = dict(os.environ)
    env.pop("PI_CONFIG_FILES", None)
    if overlay:
        # `omp config get` ignores --config; PI_CONFIG_FILES applies the same overlay layer.
        env["PI_CONFIG_FILES"] = str(overlay)
    res = subprocess.run(["omp", *args], capture_output=True, text=True, env=env, cwd=cwd)
    if res.returncode != 0:
        raise RuntimeError(f"omp {' '.join(args)} failed: {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout.strip()


def config_get(key, cwd, overlay=None):
    raw = omp(["config", "get", key], cwd, overlay)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def split_selector(value):
    """Return (selector, thinking) for one role entry."""
    head, sep, tail = value.rpartition(":")
    if sep and str(tail) in LEVELS:
        return head, tail
    return value, None


class Auditor:
    def __init__(self, catalog, allowed):
        self.catalog = catalog
        self.allowed = allowed
        self.providers = {m["provider"] for m in catalog.values()}

    def check(self, where, value, findings):
        """Validate one selector; return the bare selector when it is a concrete model."""
        sel, level = split_selector(value)
        if sel.startswith("@") or sel == "*":
            return None
        if "/" not in sel:
            findings.append(("WARN", where, f"`{value}` is not provider-qualified; fuzzy matches can drift"))
            return None
        provider = sel.split("/", 1)[0]
        model = self.catalog.get(sel)
        if provider not in self.providers:
            findings.append(("WARN", where, f"`{sel}`: provider `{provider}` is not available (not logged in or disabled); entry is skipped"))
        elif model is None and not sel.endswith("/*"):
            findings.append(("ERROR", where, f"`{sel}` is not in the `{provider}` catalog (removed or renamed); run `omp models find`"))
        if provider not in self.allowed and provider in self.providers and provider not in {"web", "local"}:
            findings.append(("WARN", where, f"`{sel}` sends data to `{provider}`, outside allowed {sorted(self.allowed)}"))
        if model and level and level not in {"off", "auto", "inherit"}:
            supported = model.get("thinking") or []
            if level not in supported:
                findings.append(("WARN", where, f"`{value}`: level `{level}` not in supported {supported}; omp clamps it"))
        return sel

    def scope(self, cwd, overlay):
        findings = []
        roles = config_get("modelRoles", cwd, overlay) or {}
        chains = config_get("retry.fallbackChains", cwd, overlay) or {}
        disabled = config_get("disabledProviders", cwd, overlay) or []
        adv_enabled = config_get("advisor.enabled", cwd, overlay)
        adv_backlog = config_get("advisor.syncBacklog", cwd, overlay)
        thinking = config_get("defaultThinkingLevel", cwd, overlay)

        resolved = {}   # role -> bare selector of its first entry
        effective = {}  # role -> (selector, thinking); omp treats a handoff as a no-op only if both match
        for role, value in roles.items():
            for i, part in enumerate(str(value).split(",")):
                sel = self.check(f"modelRoles.{role}", part.strip(), findings)
                if i == 0 and sel:
                    resolved[role] = sel
                    effective[role] = (sel, split_selector(part.strip())[1] or thinking)
        for key, entries in chains.items():
            runners = [e for e in entries or [] if e.startswith("web/") and e in self.catalog]
            for entry in entries or []:
                if entry not in runners:
                    self.check(f"retry.fallbackChains.{key}", entry, findings)
            if runners:
                findings.append(("INFO", f"retry.fallbackChains.{key}",
                                 f"{len(runners)} third-party search runners (`web/*`) receive search queries"))

        default = resolved.get("default")
        if default and effective.get("smol") == effective.get("default"):
            findings.append(("WARN", "modelRoles.smol", "same model and thinking as default: utility work and the prewalk handoff gain nothing"))
        prewalk = config_get("prewalk.enabled", cwd, overlay)
        if prewalk is True and default and "smol" in effective and effective["smol"] != effective["default"]:
            findings.append(("INFO", "prewalk.enabled",
                             f"on: after the todo list and first edit, the rest of the session runs on smol "
                             f"`{roles['smol']}` instead of `{roles['default']}`; launch debugging sessions with --no-prewalk, "
                             f"or after a handoff switch back with /switch"))
        if adv_enabled is True and default and resolved.get("advisor") == default:
            findings.append(("WARN", "modelRoles.advisor", "same model as default: the reviewer shares the main agent's blind spots"))
        if adv_enabled is True and chains.get("default"):
            # an advisor without its own chain inherits the default chain
            adv_chain = chains.get("advisor", chains["default"])
            d_head = split_selector(chains["default"][0])[0]
            a_head = split_selector(adv_chain[0])[0] if adv_chain else None
            if a_head == d_head:
                findings.append(("WARN", "retry.fallbackChains.advisor",
                                 f"first fallback `{d_head}` is the same model as default's: during a primary-provider "
                                 f"outage the reviewer is the main agent's own model"))
        if adv_enabled is True and "advisor" not in roles:
            findings.append(("WARN", "modelRoles.advisor", "unset: omp auto-picks a separate strong model from any authenticated provider"))
        if adv_enabled is True and str(adv_backlog) not in ("off", "None"):
            findings.append(("INFO", "advisor.syncBacklog", f"`{adv_backlog}`: main agent can pause up to 30 s for review catch-up"))
        for role in SMALL_WORK_ROLES:
            if role not in roles:
                findings.append(("INFO", f"modelRoles.{role}", "unset: auto-resolves (often to a large model); pin it for predictable cost"))
        fast = roles.get("fast")
        if fast and split_selector(fast)[1] in {"xhigh", "max"}:
            findings.append(("WARN", "modelRoles.fast", f"`{fast}`: a fast role at high effort defeats its purpose"))
        if chains.get("default"):
            inheriting = sorted(r for r in roles if r not in chains and r != "default" and r not in MODEL_KIND_ROLES)
            if inheriting:
                findings.append(("WARN", "retry.fallbackChains.default",
                                 f"also catches roles without their own chain: {inheriting}; give each a same-class chain or `[]`"))
        if not disabled:
            findings.append(("INFO", "disabledProviders", "empty: roles are preferences only; no provider boundary is enforced"))

        summary = {
            "modelRoles": roles,
            "retry.fallbackChains": {k: (v if len(v) <= 4 else f"<{len(v)} entries>") for k, v in chains.items()},
            "disabledProviders": disabled,
            "advisor.enabled": adv_enabled,
            "advisor.syncBacklog": adv_backlog,
            "prewalk.enabled": prewalk,
            "defaultThinkingLevel": thinking,
        }
        return summary, findings


def print_findings(findings):
    for sev, where, msg in sorted(findings, key=lambda f: SEVERITIES.index(f[0])):
        print(f"- [{sev}] {where}: {msg}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allowed", default=os.environ.get("OMP_ALLOWED_PROVIDERS", "github-copilot,cursor"),
                    help="comma-separated provider IDs allowed by policy (env OMP_ALLOWED_PROVIDERS)")
    ap.add_argument("--project", help="also apply this directory's .omp/config.yml layer")
    ap.add_argument("--quiet", action="store_true", help="findings only, no effective-config dumps")
    args = ap.parse_args()
    allowed = {p.strip() for p in args.allowed.split(",") if p.strip()}

    cwd = args.project or tempfile.mkdtemp(prefix="omp-audit-")
    project_layer = (Path(cwd) / ".omp" / "config.yml").exists()
    print(f"omp: {omp(['--version'], cwd)}")
    print(f"allowed providers: {sorted(allowed)}")
    print("layers: global ~/.omp/agent/config.yml" + (f" + project {cwd}/.omp/config.yml" if project_layer else ""))

    catalog = {m["selector"]: m for m in json.loads(omp(["models", "--kind", "all", "--json"], cwd))["models"]}
    groups = {}
    for m in catalog.values():
        groups[m["provider"]] = groups.get(m["provider"], 0) + 1
    print(f"selectable providers: {dict(sorted(groups.items()))}")
    outside = sorted(set(groups) - allowed - {"web", "local"})
    if outside:
        print(f"selectable but outside policy: {outside}")
    watchdog = sorted((Path.home() / ".omp" / "agent").glob("WATCHDOG.y*ml"))
    if watchdog:
        print(f"advisor roster files (may name other models): {[str(p) for p in watchdog]}")

    auditor = Auditor(catalog, allowed)
    total = dict.fromkeys(SEVERITIES, 0)
    base = None
    for name, overlay in [("global", None)] + [(f"preset:{p.stem}", p) for p in sorted(PRESETS_DIR.glob("*.yml"))]:
        summary, findings = auditor.scope(cwd, overlay)
        print(f"\n## {name}" + (f"  ({overlay})" if overlay else ""))
        if not args.quiet:
            print(json.dumps(summary, indent=2))
        if base is None:
            base = set(findings)
            shown = findings
        else:
            shown = [f for f in findings if f not in base]
            inherited = len(findings) - len(shown)
            if inherited:
                print(f"- ({inherited} findings inherited from global, not repeated)")
        for sev, *_ in shown:
            total[sev] += 1
        print_findings(shown) if shown else print("- no findings of its own")
    print(f"\ntotals: {total}")
    return 1 if total["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
