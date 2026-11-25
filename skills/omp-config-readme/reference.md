# omp model setup — reference

Teaching material for Luis's omp (Oh My Pi) model setup. For **current values** (which model a role uses right now), run `scripts/overview.sh`. Do not quote models from this file as current; sections marked "as of" are history.

---

## 1. The big picture

```mermaid
flowchart LR
  A[built-in defaults] --> B[global<br/>~/.omp/agent/config.yml]
  B --> C[project<br/>&lt;repo&gt;/.omp/config.yml]
  C --> D[PI_CONFIG_FILES overlays]
  D --> E[--config overlays<br/>= presets]
  E --> F[CLI flags<br/>--model, --smol, --thinking]
```

Later layers win. A preset is just a `--config` overlay on top of the global config. Login, sessions and every key the preset does not set are shared with plain `omp`.

## 2. Files

| Path | What |
|---|---|
| `~/.omp/agent/config.yml` | Global config: roles, fallback chains, advisor, prewalk |
| `~/.omp/agent/config.yml.bak-*` | Backups taken before edits |
| `~/.omp/presets/fast.yml`, `smart.yml`, `balanced.yml`, `anthropic.yml`, `openai.yml`, `gemini.yml` | Preset overlays |
| `~/.omp/presets/omp-presets.sh` | Shell functions `omp-fast`, `omp-smart`, `omp-balanced`, `omp-anthropic`, `omp-openai`, `omp-gemini`, `ompp <name>` |
| `~/.zshrc` | Last lines `source` the functions file |
| `~/.omp/presets/catalog-snapshot.json` | Model-catalog baseline for `omp-model-refresh` |
| `~/.claude/skills/omp-config-audit/` | Audit skill and `scripts/audit.py` |
| `~/.claude/skills/omp-model-refresh/` | Refresh skill and `scripts/catalog_diff.py` |
| `~/.claude/skills/omp-config-readme/` | This skill |

## 3. Daily use

```sh
omp                      # global config
omp-fast                 # near-smart quality, faster default model than balanced's: Cursor Opus 5.5 fast tier, GPT-6.2-sol advisor
omp-smart                # hard problems: Opus xhigh default, Fable 5.2 for slow/plan, GPT advisor
omp-balanced             # general work: Sonnet medium + Opus planning + GPT advisor
omp-anthropic            # Claude-only coding: Sonnet medium throughout + Opus planning/review/advisor
omp-openai               # GPT-only coding: GPT-6.2-sol medium throughout + GPT-6.2-astra planning/review/advisor
omp-gemini               # Gemini-only coding: Gemini 4 Hydrogen high driver + Gemini 4 Carbon planning/review + Gemini 4 Neon advisor
ompp <name>              # any ~/.omp/presets/<name>.yml
omp-smart -p "question"  # every omp flag passes through
omp-fast --resume        # sessions are shared across presets
```

- **Presets apply at launch.** You cannot switch presets inside a running session. Inside a session, `/model` (or `Alt+M`) → **Roles** shows the effective models, `Ctrl+P` cycles `smol → default → slow`, and `/switch` changes the model for that session only.
- **New terminal needed.** Open one, or run `source ~/.zshrc`, after editing the functions file.

### Which preset when

Inferred from each preset's models, effort, advisor and prewalk settings, plus catalog list prices (2026-11-04; GPT-6.2 and Cursor Opus fast tier 2026-11-25). Speed was measured only for the fast, gemini and openai picks (§7). The hidden-test races in §7 barely separated the models (one Sonnet run missed 2 of 35 tests; every config scored 62/62 in the 2026-11-25 race), so treat quality judgments as [INFERENCE].

| Command | Use it for | Avoid it for | Main cost per turn (list in/out per 1M) |
|---|---|---|---|
| `omp` | Default daily work in any repo: features, normal bugs, reviews. Fable 5.2 `:medium` default, Opus plans, Haiku utility work, cross-family GPT-6.2-sol advisor, GPT-6.2-astra review roles. | Security-sensitive work: Fable blocks high-risk cyber requests (see `omp-smart`); use `omp-openai`. | Fable 8/40 + GPT-6.2-sol advisor 2/10 |
| `omp-fast` | Real work where you want quality close to `omp-smart` with a default model measured faster than `omp-balanced`'s (default-model race, see §7): Cursor Opus 5.5 fast tier at `:medium`, `:high` for plan/slow, non-blocking GPT-6.2-sol advisor. | Cost-sensitive sessions: Opus fast tier is the priciest per run (≈ $0.18 per benchmark run, 2026-11-04). Security-sensitive work, as with `omp-smart`: use `omp-openai`. | Cursor Opus fast tier 8/40 (catalog 2026-11-25) + GPT-6.2-sol advisor 2/10 |
| `omp-smart` | Hard bugs, migrations, architecture, unfamiliar large codebases. Opus `:xhigh` for main work; Fable 5.2 `:xhigh` on slow and plan. **Not for security-sensitive work:** Fable blocks high-risk cyber requests and Opus 4.8 answers them upstream, outside the Opus 5.5 fallback chain (Copilot behavior unverified). Use `omp-openai` for security review. | Routine work: slowest preset, and the advisor can pause turns for up to 30 s. | Opus 4/20 default; Fable 8/40 on slow/plan; GPT-6.2-astra advisor 8/40 |
| `omp-balanced` | Planned multi-file changes whose execution is mechanical: call-site updates, tests, boilerplate. Sonnet plans; Haiku implements after the first edit. | Iterative debugging, where each result changes the plan. Start such sessions with `omp-balanced --no-prewalk`, or use `omp` or `omp-smart`. | Sonnet 2/10, then Haiku 0.1/0.5 after the handoff + GPT advisor 2/10 |
| `omp-anthropic` | Claude-only sessions: comparing vendors, Claude-tuned prompts or skills, or when Copilot GPT quota is exhausted. Sonnet `:medium` throughout. | Wanting a cross-family second opinion: the reviewer is Opus, the same family. | Sonnet 2/10 + Opus advisor 4/20 |
| `omp-openai` | GPT-only sessions: a second attempt when Claude gets stuck, comparing vendors, or when Copilot Claude quota is exhausted. | Long or cost-sensitive sessions: the GPT-6.2-astra advisor (8/40) reviews every turn. | GPT-6.2-sol 2/10 + GPT-6.2-astra advisor 8/40 |
| `omp-gemini` | Gemini-only sessions: a third-family second opinion, or when Copilot Claude and GPT quota are exhausted. Hydrogen `:high` codes, Carbon `:high` plans and reviews, non-blocking Neon advisor. Prices as of 2026-11-24. | Speed-sensitive work: in the default-model race (§7) Hydrogen `:high` averaged 224 s against 42 s for `omp-balanced`'s Sonnet `:medium`. Gemini code quality beyond that task is unverified. | Hydrogen 1.5/7.5 + Neon advisor 3/15; Carbon 2/10 on plan and review (4/20 after 2026-11-30) |

Rules of thumb:
- **Start with `omp`.** Escalate to `omp-smart` when a task resists two attempts or touches security, data or migrations. Use `omp-fast` when you want near-`omp-smart` quality with shorter turns and cost doesn't matter.
- **Use `omp-balanced` when the plan is the hard part,** not the edits. For a task you already know is debugging, launch with `omp-balanced --no-prewalk`. If a running session has already handed off to Haiku and turns into debugging, `--no-prewalk` can't help, because it's a launch flag. Switch back yourself with `/switch` (this session only) or `/model`, and pick Sonnet or Opus.
- **Use the vendor presets to switch model family:** for a second opinion on a stuck task, or around a quota or outage on one family. Every preset falls back to Cursor for its own roles.
- **Treat `omp-gemini` as a slower second opinion, not a speed pick.** Hydrogen `:high` drives, Carbon `:high` plans and reviews, and a Neon advisor reviews every turn without pausing Hydrogen. Its default averaged 224 s on the §7 race task against 42 s for `omp-balanced`'s Sonnet.
- **Use `omp-openai` for security review or a GPT-only second attempt, not for speed.** GPT-6.2-sol `:medium` drives; GPT-6.2-astra plans, reviews and advises on every turn. Every role tops out at 400K context, against 1M for the Claude `-1m` defaults. Its default averaged 80.7 s on the 2026-11-25 race task (§7) against 36.5 s for `omp-balanced`'s Sonnet.
- **List prices may not match subscription billing.** Copilot and Cursor plans can charge differently.

## 4. Concepts

### Model roles
A role names the kind of work. omp picks the model assigned to that role.

| Role | Work |
|---|---|
| `default` | main session |
| `smol` | fast, cheap utility work; prewalk handoff target |
| `slow` | thorough reasoning |
| `plan` | plan mode |
| `vision` | image inspection |
| `commit` | commit messages |
| `tiny` | titles, small classifications, memory support |
| `task` | subagents with no model of their own |
| `advisor` | second model that reviews the main agent |
| `designer` | designer subagent |
| `web`, `image`, `speech`, `dictation`, `judge` | **model-kind** roles: search runners, image generation and similar |

Extensions add custom roles. In this setup those are `code-review`, `pr-fixes`, `fast`, `memory` and `widget`.

**An unset role auto-resolves** from any available, authenticated model. Auto choices change when credentials or the catalog change, so pin any role whose behavior must stay stable.

### Selectors and thinking levels
- The format is `provider/model-id:level`, where level is one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` or `auto`. omp clamps a level the model doesn't support.
- IDs differ by provider. Copilot uses dots (`github-copilot/claude-haiku-5.5`) and Cursor uses dashes (`cursor/claude-haiku-5-5`). Copy IDs from `omp models <provider>` or `omp models find <text>`.
- Since omp v18.14.0, a provider-qualified selector must match exactly. Near misses fail rather than picking a sibling model.
- `-1m` variants have a 1M-token context. Cursor `-fast` variants are fast-mode tiers and are premium-priced.
- Role aliases: `"@default"`, `"@slow"` and so on reuse another role.

### Merge rules
- **Mappings deep-merge:** `modelRoles` and `retry.fallbackChains`. A preset inherits every role and chain it does not set.
- **Scalars and arrays replace.** A preset or project `disabledProviders: [x]` throws away the global list.

### Profiles vs overlays (why the presets are overlays)
- `--profile <name>` replaces the global scope and isolates auth, sessions and caches, so each profile needs its own login. Exported API-key environment variables still leak in.
- `--config <file>` adds a read-only layer on top of your normal setup, with the same logins and sessions. This is what the presets use.

### Fallback chains (`retry.fallbackChains`)
- When a model fails (quota, outage), omp walks the chain for that role, in order.
- The `default` chain is **also used by every chat role without its own chain**. Give each role a same-class chain (Haiku to Haiku, Opus to Opus) so a failure doesn't silently upgrade or downgrade the model.
- An explicit `[]` means no fallback for that role.
- Model-kind roles (`web` and the others) never use `default`.
- Recovery is not a boundary: entries still pass through `disabledProviders`.

### Advisor
- A second model reviews prompts, agent output, reasoning and tool results, so it is a **data-egress path** to its provider.
- Prefer a different model family from `default` for an independent review.
- `advisor.syncBacklog`: `"off"` never waits. `"1"`, `"3"` or `"5"` pause the main agent for up to 30 s when review falls that many turns behind.
- `WATCHDOG.yml` rosters can add advisors with their own models. In a session, `/advisor status` shows the models actually in use.

### Prewalk
`prewalk.enabled: true` arms a one-time handoff. Once the model has made a todo list and finished its first file edit, omp switches the session to `@smol` **for the rest of the session**, including later debugging and tests. It saves cost only when `smol` is smaller than `default`, and it trades away quality. The docs recommend keeping the capable model for debugging, security-sensitive work, and changes with hidden invariants.
- Per session, at launch: `--no-prewalk` skips the handoff, and `--prewalk` or `--prewalk-into <model>` arms it. Inside a running session, `/prewalk` arms it. Nothing undoes a handoff that already happened: pick the model again with `/switch` or `/model`.
- On omp 18.13.3 the target is always `@smol`. A `prewalk.into` setting arrived in v18.14.0.
- In this setup: off in global, fast and smart; on in balanced (Sonnet → Haiku `:low`).

### Provider boundary
- Roles are **preferences**, not an allowlist.
- `disabledProviders` is the only boundary. It is checked before credentials and is a denylist you have to keep complete.
- `enabledProviders` controls discovery sources (rules and skills), not models.
- `omp models --kind all` lists everything selectable, including `web` search runners and `local` on-device models.
- An allowed provider ID doesn't say which server receives requests, because `models.yml` `baseUrl` overrides can redirect it.

## 5. How to…

| Goal | Do |
|---|---|
| See what's configured now | `bash ~/.claude/skills/omp-config-readme/scripts/overview.sh` |
| See one preset's merged roles | `PI_CONFIG_FILES=~/.omp/presets/smart.yml omp config get modelRoles` (note: `omp config get` **ignores** `--config`) |
| Check which model really answers | `cd /tmp; omp-fast -p --no-session --mode json "reply with the single word ok" \| grep -o -E '"(provider\|model)":"[^"]+"' \| sort \| uniq -c` |
| Add a preset | Create `~/.omp/presets/<name>.yml` with only the keys to change, then run `ompp <name>`. The audit picks it up. |
| Change a role | Ask for **omp-config-audit**, or edit the YAML, then run the audit script |
| Find better or new models | Ask for **omp-model-refresh** |
| Compare model speed | `omp bench a b --runs 3 --max-tokens 256 --par 1 --prompt "…"`. Compare within one provider only. |
| Enforce GitHub + Cursor only | Add `disabledProviders` listing every other provider from `omp models --kind all`, and give `web` and `image` an in-policy model or disable them |
| Roll back the global config | `cp ~/.omp/agent/config.yml.bak-20261104 ~/.omp/agent/config.yml` |
| Change the provider policy for the skills | `export OMP_ALLOWED_PROVIDERS=github-copilot,cursor` (or `--allowed`) |

## 6. Gotchas

- **`omp config get` ignores `--config`.** Use `PI_CONFIG_FILES` to inspect a preset.
- **Overlays are strict.** Bad YAML or a missing preset file stops omp at startup. The global config is different: broken YAML is moved to a `.broken-*` backup.
- **Running sessions don't pick up edits** to presets. Start a new session.
- **Project layer.** A repo's `.omp/config.yml` sits between global and the preset. Run checks from `/tmp` to exclude it.
- **Cursor benchmarks.** Cursor requests carry about 12–20K wrapper tokens and ignored `--max-tokens` in testing, so TTFT and cost per run aren't comparable with Copilot.
- **Bench measures speed and cost, not code quality.**
- **Same model in two roles.** `smol` or `advisor` equal to `default` gains nothing.
- **Unused providers.** An entry for a provider you aren't logged into is skipped silently. The audit reports it.

## 7. Why the setup looks like this (as of 2026-11-04)

- **Global (roles refreshed 2026-11-25):** Fable 5.2 `:medium` `default`, Opus 5.5 1m `slow` (`:high`) and `plan` (`:max`), Haiku 5.5 for `smol`, `memory`, `widget`, `commit` and `fast`, `tiny` on local `falcon-h1-90m`, a GPT-6.2-sol `:high` advisor (different family) and GPT-6.2-astra `:max` review roles. On 2026-11-25 the advisor moved from GPT-6.1-sol (same list price, 2/10) and the review roles from GPT-6-astra (8/40 vs 10/50); GPT-6.2-astra has 400K context against 1.05M, below Fable's 1M. Fallbacks go to Cursor: Sonnet 5.5 1m `:high` for `default` (Cursor has no Fable, so a failure steps down a class), Opus for `slow`, `plan` and the advisor, Haiku for the small roles; the review roles and `tiny` have `[]`. `syncBacklog` is `"off"`. Prewalk is **off**: with `smol` on Haiku it would hand everyday sessions to Haiku after the first edit. Use `omp --prewalk` when you want that.
- **fast (reworked 2026-11-18):** the goal changed from cheapest-and-fastest to quality close to smart with a faster default model than balanced's, cost not a constraint. A real-task race of **default models only** (each run with `--model` on top of the global config, not the full presets; 2 runs each; spec-only task graded by 15 hidden tests, which every config passed) measured Cursor `claude-opus-5-5-fast:medium` at 28.1 s mean against 33.6 s for balanced's default Sonnet 5.5 1m `:medium`, 67.4 s for smart's default Opus 5.5 1m `:xhigh`, and 35.9 s for the old Composer 2.5 `:low` default. Full-preset behavior was not raced: balanced's prewalk handoff to Haiku after the first edit, and each preset's advisor settings, were not exercised. `gpt-6.2-astra` was slower than balanced's default in the agent loop (easy task 29.9 s `:medium` vs 20.2 s), despite ranking well on third-party indexes. Opus fast tier `:high` takes plan and slow, Sonnet 5.5 `:low` the utility roles, and a `gpt-6.2-sol:medium` advisor runs with `syncBacklog: "off"`. Prewalk stays off. Fallbacks go to Copilot Opus 5.5 (non-1m), keeping the model family through a Cursor outage; its speed in this preset is not measured. That fast-tier Opus matches standard Opus quality is [INFERENCE].
- **smart:** Opus 5.5 1m on Copilot, which has 128K max output against 64K on Cursor. GPT-6.x is only on Copilot among the two providers. The advisor is GPT-6.2-astra (since 2026-11-18; trial) with `syncBacklog: "1"`. The review roles (`code-review`, `pr-fixes`) run GPT-6.2-sol `:max` since 2026-11-25, replacing GPT-6.1-sol at the same list price; GitHub reports that 6.2 Sol catches about twice as many real review issues, unverified here ([INFERENCE]). The preset overrides the inherited fallbacks with same-class Cursor models: Opus `xhigh`/`max` for `default`, `slow` and `plan`; Sonnet for `smol` and `fast`; `gpt-5.6-sol-1m` for the advisor and review roles, so the fallback reviewer stays a different family from Opus. Trade-offs while a fallback is active: Opus output drops to 64K; for the review roles the GPT fallback lists at 4/20 per 1M tokens against 2/10 for Copilot GPT-6.2-sol (2×), and for the advisor at half the price of Copilot GPT-6.2-astra (8/40), a tier down. Cursor Sonnet has no listed price.
- **balanced:** Sonnet medium, Opus planning, Haiku utility work, a GPT-6.2-sol advisor (since 2026-11-18), and prewalk **on**, so implementation after the first edit runs on Haiku `:low`. Use `omp-balanced --no-prewalk` to keep Sonnet throughout. Fallbacks are same-class Cursor models: Sonnet `:medium` for `default` and `pr-fixes`, Opus for `code-review`, and `gpt-5.6-sol-1m` for the advisor (2× list price vs Copilot GPT-6.2-sol).
- **anthropic:** Claude models only, through Copilot with same-class Cursor Claude fallbacks. Sonnet 5.5 1m `:medium` codes the whole session (prewalk off). Opus 5.5 1m `:high` plans, handles `slow` and does `code-review`; Opus `:medium` is the advisor, a different model from Sonnet but the same family, so the review is less independent than a GPT reviewer. Haiku handles utility work. `vision`, `task` and `designer` are pinned to Sonnet, and image generation is off because no Claude model generates images. Web search stays on the inherited Google model by choice: tested on 2026-11-04, Copilot Claude failed (`IDE token is malformed`), Cursor has no web-search model, and direct `anthropic/claude-haiku-4-5` worked but is outside the GitHub-and-Cursor policy.
- **openai (refreshed 2026-11-25):** GPT models only, through Copilot with GPT fallbacks on Cursor. Copilot GPT-6.x tiers by list price (in/out per 1M, 2026-11-25): `gpt-6-luna` 0.1/0.5 < `gpt-6.1-terra` 1/5 < `gpt-6.2-sol` 2/10 < `gpt-6.2-astra` 8/40. `gpt-6.2-sol:medium` codes the whole session (prewalk off) and runs `task` and `designer`, plus `vision` at `:low`. `gpt-6.2-astra:high` plans, handles `slow` and does `code-review`; `gpt-6.2-astra:medium` is the advisor, the main cost driver because it lists at 4× `sol` and reviews every turn. `gpt-6-luna:low` handles all small-work roles. **2026-11-25 refresh:** GPT-6.2 replaced `gpt-6.1-sol` and `gpt-6-astra`. A real-task race of **default models only** (`--model` over the global config, whose non-blocking advisor stayed on; 2 runs each; spec-only cron task graded by 62 hidden tests, validated against a reference solution and 6 mutants; every run answered only by the requested model) gave `gpt-6.2-sol:medium` 62/62 twice at 80.7 s mean and about $0.08 per run, `gpt-6.1-sol:medium` 62/62 twice at 90.8 s and $0.08, `omp-balanced`'s Sonnet 5.5 1m `:medium` 62/62 twice at 36.5 s and $0.09, and `omp-smart`'s Opus 5.5 1m `:xhigh` 62/62 twice at 232.2 s and $0.56 (omp's list-price estimates for the default model; advisor calls excluded). The tests did not separate the models, so quality differences are [INFERENCE]. `omp bench` (Copilot, 3 runs, 256 tokens): `gpt-6.2-sol:medium` 1.1 s TTFT and 60 tok/s against 5.1 s and 39 tok/s for `gpt-6.1-sol`; `gpt-6.2-astra:high` 8.6 s and 30 tok/s against 10.7 s and 21 tok/s for `gpt-6-astra`. GPT-6.2-astra has 400K context against 1.05M for GPT-6-astra, the same as the `sol` default. Every chat chain is overridden, because the global small-role chains point to Claude Haiku. Cursor has no GPT-6, so fallbacks use `gpt-5.6-sol-1m` (4/20) and `gpt-5.6-luna-1m` (0.2/1.2); astra roles therefore drop a tier on failure. The advisor's fallback is `gpt-5.5-1m:high` (5/30), a different model from `default`'s fallback, so a Copilot outage doesn't leave the reviewer reviewing its own model's output. Image generation is off (no OpenAI image model in either catalog). Web search stays on the inherited Google model: Copilot GPT returned `OpenAI API web search is unavailable`, and Cursor has none.
- **gemini (added 2026-11-10, refreshed 2026-11-13 and 2026-11-24):** Gemini models only, through Copilot with Gemini fallbacks on Cursor. `gemini-4-hydrogen:high` codes the session (prewalk off, since `smol` is also Hydrogen). `gemini-4-carbon:high` plans, handles `slow` and does `code-review`. `gemini-4-neon-1m:medium` is the advisor with `syncBacklog: "off"`: a third model next to Hydrogen and Carbon, but the same family, so less independent than a GPT or Claude reviewer. Hydrogen `:medium` runs subagents (`task`), and Hydrogen `:low` handles `vision` and every small-work role. Hydrogen and Neon replaced Gemini 3.8 Flash and Gemini 4 Argon, which Copilot retires on 2026-12-14. Copilot list prices (in/out per 1M, 2026-11-24): Hydrogen 1.5/7.5, Carbon 2/10 (Google raises it to 4/20 after 2026-11-30), Neon 3/15. `omp bench` (Copilot, 2026-11-24, 3 runs, 256-token prompt): Hydrogen `:low` 1.7 s TTFT and 153 tok/s against 3.8 Flash 1m `:low` 2.2 s and 80 tok/s; Neon `:medium` 2.4 s and 110 tok/s against Argon 1m `:medium` 3.0 s and 37 tok/s and Carbon `:medium` 3.1 s and 42 tok/s. **Default stays Hydrogen:** a real-task race of **default models only** (one model in every agent role, advisor and prewalk off, no fallbacks; 2 runs each on a spec-only spreadsheet-engine task graded by 35 hidden tests, validated against a reference solution and 4 mutations; all Copilot) gave Hydrogen `:high` 35/35 twice at 224 s mean and about $0.31 per run, Neon 1m `:high` 35/35 twice at 435 s and about $0.89, `omp-balanced`'s Sonnet 5.5 1m `:medium` 35 and 33 at 42 s and about $0.14, and `omp-smart`'s Opus 5.5 1m `:xhigh` 35/35 twice at 565 s and about $1.69 (costs are omp's list-price estimates). The hidden tests did not separate Hydrogen and Neon, so any quality difference between them is [INFERENCE]. Every chat chain is overridden, because the global small-role chains point to Claude Haiku. Cursor's base `gemini-4-*` selectors have 300K context (observed 2026-11-24), so the Hydrogen and Neon chains use the `-1m` selectors (same price) to match their 1M Copilot primaries; the Carbon chains keep the base selector, whose 300K covers Copilot Carbon's 264K. Image generation is off. Web search stays on the inherited global `web` chain, untested in this preset. Copilot Hydrogen answered a smoke test through `omp-gemini` on 2026-11-24.
- **Open item:** the `web` role (`google-antigravity`) and its fallback chain still reach providers outside GitHub and Cursor.

## 8. Sources

- omp docs: https://omp.sh/docs/roles, https://omp.sh/docs/settings, https://omp.sh/docs/advisor, https://omp.sh/docs/cli
- Providers and settings reference: https://raw.githubusercontent.com/can1357/oh-my-pi/main/docs/providers.md, https://raw.githubusercontent.com/can1357/oh-my-pi/main/docs/settings.md
- omp releases: https://github.com/can1357/oh-my-pi/releases
- Article: https://luismori.dev/article/omp-model-roles-are-preferences-not-provider-boundaries/
