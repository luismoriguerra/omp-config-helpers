---
name: omp-config-audit
description: >-
  Audits the local omp (Oh My Pi) model routing — global ~/.omp/agent/config.yml
  plus every preset overlay in ~/.omp/presets — against the live model catalog
  and the allowed-provider policy, then proposes YAML fixes. Use when the user
  asks to evaluate, review, check, or fix their omp config, model roles,
  presets, fallback chains, advisor, or provider boundary. Report-only unless
  the user explicitly asks to apply changes.
---

# omp config audit

Evaluate omp model routing and recommend changes. Measure the live config; never reason from memory of what the file "should" contain.

## Context

- **Policy:** allowed providers are `github-copilot` and `cursor`. Override with `--allowed a,b` or env `OMP_ALLOWED_PROVIDERS`.
- **Global config:** `~/.omp/agent/config.yml`.
- **Presets:** every `~/.omp/presets/*.yml` (today: fast, smart, balanced, anthropic, openai, gemini). These are read-only `--config` overlays, run via the `omp-<name>` and `ompp <name>` shell functions in `~/.omp/presets/omp-presets.sh`.
- **Merge rules:** overlays sit on top of global config. Mappings (`modelRoles`, `retry.fallbackChains`) deep-merge, so a preset inherits every role and chain it does not set. Scalars and arrays replace.

## Run

```bash
python3 ~/.claude/skills/omp-config-audit/scripts/audit.py          # full: effective config + findings
python3 ~/.claude/skills/omp-config-audit/scripts/audit.py --quiet  # findings only
python3 ~/.claude/skills/omp-config-audit/scripts/audit.py --project /path/to/repo  # include that repo's .omp/config.yml
```

The script is read-only. It exits 1 when any ERROR exists. Presets show only the findings they add on top of global.

After changing `audit.py`, run its regression checks (they use the live catalog and throwaway overlays):
```bash
python3 ~/.claude/skills/omp-config-audit/scripts/test_audit.py
```

## What the script checks (mechanical)

| Check | Severity |
|---|---|
| Selector not in the catalog of an available provider (renamed or removed) | ERROR |
| Provider not available (not logged in or disabled), so the entry is skipped | WARN |
| Selector sends data to a provider outside policy | WARN |
| Thinking suffix not supported by the model (omp clamps it) | WARN |
| `smol` same model **and** thinking level as `default` (a suffix-less role uses `defaultThinkingLevel`) | WARN |
| `advisor` same model as `default`, or unset while the advisor is enabled | WARN |
| Advisor enabled and its first fallback is the same model as `default`'s first fallback (an advisor without its own chain inherits `default`'s) | WARN |
| `fast` role at `xhigh` or `max` | WARN |
| `retry.fallbackChains.default` silently catching roles without their own chain | WARN |
| `tiny`, `memory`, `widget` or `commit` unset (auto-resolve) | INFO |
| `advisor.syncBacklog` not `off` (pauses of up to 30 s) | INFO |
| `prewalk.enabled` with `smol` different from `default`: the session continues on `smol` after the first edit | INFO |
| `disabledProviders` empty, so there is no enforced boundary | INFO |
| `web/*` search runners in chains | INFO (one line) |

## Judgment rules (apply on top of the script)

These come from omp docs (omp.sh/docs/roles, /docs/settings, /docs/advisor, docs/providers.md) and verified local runs.

1. **Roles are preferences, not boundaries.** Unset roles auto-resolve from *any* authenticated provider. Only `disabledProviders` enforces a boundary, and it is a denylist. Every non-allowed provider must be listed. `enabledProviders` is for discovery sources (rules and skills), not models.
2. **Arrays replace across layers.** A project or preset `disabledProviders` array discards the global one entirely. Repeat the global IDs if you mean to add to it.
3. **Pin roles whose behavior must stay stable.** Do not rely on auto-follow (for example, "unset `tiny` follows `smol`"). The hub shows `auto → …` for unpinned roles.
4. **Fallback chains:** the `default` chain is reused by every chat role without its own chain. Give each role a same-class chain (small to small, Opus to Opus). An explicit `[]` means no fallback. Model-kind roles (`web`, `image`, `speech`, `dictation`, `judge`) never use `default`.
5. **The advisor is a data-egress path.** It receives prompts, agent output, reasoning and tool results. Keep it inside policy, and prefer a different model family from `default` for an independent review. Check `~/.omp/agent/WATCHDOG.yml` and any project `WATCHDOG.yml` rosters, which can name their own models.
6. **Speed presets:** `advisor.enabled: false` or `syncBacklog: "off"`, `prewalk` off, low default thinking.
7. **`web` and `image` roles** often resolve to `google-antigravity` or other vendors. Flag them under the policy, but do not "fix" them by pointing at a chat model without testing a real search or image call.
8. **Selector formats differ by provider.** Copilot uses dots (`claude-haiku-5.5`) and Cursor uses dashes (`claude-haiku-5-5`). Always copy selectors from `omp models <provider>` or `omp models find <text>`.
9. **Single-family presets (anthropic, openai, gemini) must override every chat role and chain.** Merged-in global values can carry another family; for example, the global small-role chains point to Claude Haiku. Check with `PI_CONFIG_FILES=<preset> omp config get modelRoles` and `… retry.fallbackChains`, and confirm that every non-`web` entry belongs to the family.

## Report format

1. One-line verdict.
2. A table of findings worth acting on, with columns Scope | Key | Issue | Proposed value | Why. Skip INFO noise unless the user cares about the boundary.
3. A ready-to-paste YAML block per scope, containing only the keys that change.
4. Anything you could not verify, labeled as such.

## Applying changes (only when the user asks)

1. Back up the file: `cp ~/.omp/agent/config.yml ~/.omp/agent/config.yml.bak-$(date +%Y%m%d-%H%M%S)`. Do the same for preset files.
2. Edit only the keys in the proposal. Keep comments and unrelated keys.
3. Verify effective values. Note that `omp config get` **ignores `--config`**, so check presets with `PI_CONFIG_FILES=~/.omp/presets/<name>.yml omp config get modelRoles`.
4. Smoke-test each changed scope with one tiny real request, and confirm the provider and model that answered:
   ```bash
   f=$(mktemp); omp [--config ~/.omp/presets/<name>.yml] -p --no-session --mode json "reply with the single word ok" > "$f"; \
     grep -o -E '"(provider|model)":"[^"]+"' "$f" | sort | uniq -c; rm -f "$f"
   ```
   Run it from a scratch directory (`cd /tmp`) so no project `.omp/config.yml` interferes.
5. Re-run the audit script. Report the before and after totals.
