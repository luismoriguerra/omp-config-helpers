---
name: omp-model-refresh
description: >-
  Detects new, removed, or changed LLMs in the GitHub Copilot and Cursor model
  catalogs that omp (Oh My Pi) sees, researches the releases, measures the
  candidates, and recommends role changes for the global omp config and the
  presets in ~/.omp/presets. Use when the user mentions a new model release,
  asks "are there better models now", "refresh my omp models", "what changed in
  the catalog", or wants periodic model recommendations. Report-only unless the
  user explicitly asks to apply.
---

# omp model refresh

Turn catalog changes and new releases into evidence-backed role recommendations. Recommend from measured facts, not model names or hype.

## Context

- **Allowed providers:** `github-copilot` and `cursor`. Override with `--allowed` or env `OMP_ALLOWED_PROVIDERS`.
- **Scopes to recommend for:** global `~/.omp/agent/config.yml`, plus every preset in `~/.omp/presets/*.yml` (today: fast, smart, balanced, anthropic, openai, gemini). Keep the anthropic preset Claude-only, the openai preset GPT-only and the gemini preset Gemini-only.
- **Catalog snapshot:** `~/.omp/presets/catalog-snapshot.json`. Update it only after the user has seen the report.
- **Companion skill:** `omp-config-audit`. Use its script for validation and its "Applying changes" steps.

## Workflow

### 1. Diff the catalog

```bash
python3 ~/.claude/skills/omp-model-refresh/scripts/catalog_diff.py --refresh
```

The output has three sections: **Added**, **Removed** (with `<-- REFERENCED IN YOUR CONFIG/PRESETS` when a role or chain uses the model) and **Changed** (context, max output, thinking levels, image input, price).

- **Referenced removals are urgent.** That role or chain entry is broken. Propose a same-family replacement first.
- **Named release not in the catalog.** If the user named a model that is not listed, run `omp models refresh` and `omp models find <name>`. If it is still missing, say so: omp or the provider has not shipped it yet. Check the omp releases page.

### 2. Research what changed

Use primary sources only, and cite links:
- **omp releases:** https://github.com/can1357/oh-my-pi/releases. Look for catalog additions, selector rules, role defaults and breaking changes.
- **GitHub Copilot changelog:** https://github.blog/changelog/. Look for model availability, preview or GA status, and premium-request multipliers.
- **Cursor changelog:** https://cursor.com/changelog. Look for new models, `-fast` modes and pricing.
- **Vendor announcements:** the model maker's own release post, for capability claims and intended use.

Record for each candidate: provider IDs and exact selectors, context, max output, thinking levels, image input, listed price, and status (preview or GA).

### 3. Map candidates to role slots

| Slot | Needs | Typical tier |
|---|---|---|
| `default` | strong everyday coding, tool use | Sonnet-class |
| `slow`, `plan` | best reasoning; latency OK | Opus-class or the top GPT tier |
| `smol`, `tiny`, `memory`, `widget`, `commit` | lowest latency and cost | Haiku-class or a small GPT tier |
| `fast` | throughput at low effort | Haiku-class or Cursor `-fast` |
| `advisor` | strong reviewer from a **different family** than `default` | top GPT if `default` is Claude, and vice versa |
| `code-review`, `pr-fixes` | strong reviewer | top tier |
| fast preset `default` | highest measured tok/s and low TTFT at acceptable cost | Cursor `composer-*-fast` and similar |

Selector formats differ: Copilot uses dots (`claude-haiku-5.5`) and Cursor uses dashes (`claude-haiku-5-5`). `-1m` variants trade max output for context. Cursor `-fast` variants are premium-priced (`claude-opus-5-5-fast` measured about 8× `composer-2.5-fast` per run on 2026-11-04).

### 4. Measure

Each step below sends a few small paid requests. Tell the user first, and ask before benchmarking more than 6 models.

```bash
cd /tmp
omp bench <cand1> <cand2> <incumbent> --runs 3 --max-tokens 256 --par 1 \
  --prompt "Write a TypeScript function that deduplicates an array of objects by a key, with tests."
```

- Always include the **incumbent** for the slot, so the comparison is relative.
- **Compare within a provider.** Cursor requests carry about 12–20K tokens of wrapper input and ignored `--max-tokens` in a 2026-11-04 test, so TTFT and per-run cost are not comparable with Copilot.
- `omp bench` measures speed and cost, not code quality. Do not claim quality from it. Quality claims need release-note evidence or a real task run on the user's repo, and otherwise get an `[INFERENCE]` label.
- Drop any candidate with a failed run, and report the error.

Then smoke-test each finalist in a throwaway overlay:

```bash
printf 'modelRoles:\n  default: <selector>:<level>\n' > /tmp/cand.yml
f=$(mktemp); omp --config /tmp/cand.yml -p --no-session --mode json "reply with the single word ok" > "$f"; \
  grep -o -E '"(provider|model)":"[^"]+"' "$f" | sort | uniq -c; rm -f "$f" /tmp/cand.yml
```

### 5. Report

1. **Catalog changes:** a short summary of the diff.
2. **Recommendations:** one table per scope (global and each preset) with columns Role | Current | Proposed | Evidence | Risk. Evidence is a catalog fact, a bench number with its date, or a cited release note. Leave a role unchanged when no candidate beats the incumbent on evidence.
3. **YAML:** ready-to-paste blocks with only the changed keys. Include matching `retry.fallbackChains` entries (same class, inside policy). The `default` chain catches every role without its own chain.
4. **Unverified items,** labeled as such.

### 6. Apply (only when the user asks), then save the snapshot

1. Follow the "Applying changes" steps in `omp-config-audit` (backup, edit, `PI_CONFIG_FILES` check, smoke test).
2. Run `python3 ~/.claude/skills/omp-config-audit/scripts/audit.py --quiet`. It should show 0 ERRORs.
3. Run `python3 ~/.claude/skills/omp-model-refresh/scripts/catalog_diff.py --save` so the next run diffs from here.

If the user reviewed the report but declined changes, still run `--save`, so the same additions are not reported again.
