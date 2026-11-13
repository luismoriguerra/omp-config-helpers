#!/usr/bin/env python3
"""Regression checks for audit.py's smol/prewalk logic, run against the live omp catalog.

  python3 ~/.claude/skills/omp-config-audit/scripts/test_audit.py

Each case writes a throwaway overlay, audits it as a scope, and asserts on the findings.
omp treats a prewalk handoff as a no-op only when model AND thinking level match.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit", HERE / "audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

SONNET = "github-copilot/claude-sonnet-5.5-1m"
HAIKU = "github-copilot/claude-haiku-5.5"
C_SONNET = "cursor/claude-sonnet-5-5-1m"
C_OPUS = "cursor/claude-opus-5-5-1m"

CASES = [
    # (name, default, smol, prewalk, expect smol WARN, expect prewalk INFO)
    ("same model, different thinking", f"{SONNET}:high", f"{SONNET}:low", True, False, True),
    ("same model and thinking", f"{SONNET}:high", f"{SONNET}:high", True, True, False),
    ("no suffix on either: both use defaultThinkingLevel", SONNET, SONNET, True, True, False),
    ("different model", f"{SONNET}:medium", f"{HAIKU}:low", True, False, True),
    ("different model, prewalk off", f"{SONNET}:medium", f"{HAIKU}:low", False, False, False),
]

ADVISOR_CASES = [
    # (name, advisor enabled, default chain, advisor chain, expect WARN on retry.fallbackChains.advisor)
    ("same first fallback", True, f"[{C_SONNET}:medium]", f"[{C_SONNET}:medium]", True),
    ("same model, different effort", True, f"[{C_SONNET}:medium]", f"[{C_SONNET}:high]", True),
    ("distinct reviewer fallback", True, f"[{C_SONNET}:medium]", f"[{C_OPUS}:medium]", False),
    ("advisor disabled", False, f"[{C_SONNET}:medium]", f"[{C_SONNET}:medium]", False),
    ("advisor has no fallback", True, f"[{C_SONNET}:medium]", "[]", False),
]


def main():
    cwd = tempfile.mkdtemp(prefix="omp-audit-test-")
    catalog = {m["selector"]: m for m in json.loads(audit.omp(["models", "--kind", "all", "--json"], cwd))["models"]}
    for sel in (SONNET, HAIKU, C_SONNET, C_OPUS):
        assert sel in catalog, f"fixture model {sel} missing from catalog; update the test fixtures"
    auditor = audit.Auditor(catalog, {"github-copilot", "cursor"})

    failures = 0
    for name, default, smol, prewalk, want_warn, want_info in CASES:
        overlay = Path(cwd) / "case.yml"
        overlay.write_text(
            f"modelRoles:\n  default: {default}\n  smol: {smol}\n"
            f"defaultThinkingLevel: high\nprewalk:\n  enabled: {str(prewalk).lower()}\n"
        )
        _, findings = auditor.scope(cwd, overlay)
        got_warn = any(sev == "WARN" and where == "modelRoles.smol" for sev, where, _ in findings)
        got_info = any(where == "prewalk.enabled" for _, where, _ in findings)
        ok = got_warn == want_warn and got_info == want_info
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: smol WARN={got_warn} (want {want_warn}), prewalk INFO={got_info} (want {want_info})")

    for name, enabled, d_chain, a_chain, want in ADVISOR_CASES:
        overlay = Path(cwd) / "case.yml"
        overlay.write_text(
            f"modelRoles:\n  default: {SONNET}:medium\n  advisor: {HAIKU}:low\n"
            f"advisor:\n  enabled: {str(enabled).lower()}\n"
            f"retry:\n  fallbackChains:\n    default: {d_chain}\n    advisor: {a_chain}\n"
        )
        _, findings = auditor.scope(cwd, overlay)
        got = any(sev == "WARN" and where == "retry.fallbackChains.advisor" for sev, where, _ in findings)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  advisor fallback, {name}: WARN={got} (want {want})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
