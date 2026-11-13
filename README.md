# omp-config-helpers

My [omp](https://omp.sh) setup: global config, model presets, and my custom omp skills, plus the scripts that keep them in sync with this repo.

The live files stay where omp reads them. This repo is a **snapshot**: `omp-sync` copies the live files in, scans them for secrets, commits, and pushes. `omp-restore` copies the repo back out (new machine, rollback, or an edit made on GitHub). Nothing is symlinked, so omp can rewrite `config.yml` however it likes without breaking anything.

This repo is **public**: every `omp-sync` push is published immediately. When unsure, run `omp-sync --no-push`, inspect the commit with `git show`, then run `omp-sync` again to push it.

```
live files  --omp-sync-->  this repo  --git push-->  GitHub (public)
live files  <-omp-restore--  this repo  <--git pull--  GitHub
```

## Background

This setup is based on my post [omp Model Roles Are Preferences, Not Boundaries: Locking Your Coding Agent to One Provider](https://luismori.dev/article/omp-model-roles-are-preferences-not-provider-boundaries/) (Nov 3, 2026). The ideas from it that shape this repo:

- **`modelRoles` is a preference, not an allowlist.** Unset roles auto-resolve from any authenticated provider, so the config and presets pin every role they care about.
- **`disabledProviders` is the boundary.** It is a denylist you maintain, and arrays replace across layers, so a preset or project file that sets it drops the global list.
- **Layers merge.** Presets are `--config` overlays: `modelRoles` and `retry.fallbackChains` deep-merge with the global config, scalars and arrays replace.
- **The advisor is a data-egress decision.** It receives prompts, output, and tool results, so it stays inside the allowed providers.
- **Verify instead of trusting the YAML.** `omp-config-audit` and the smoke test in its skill implement the post's checks: effective config, catalog, and which provider actually answered.

## What is tracked

Defined in [`manifest.txt`](manifest.txt):

| Live path | Repo path |
|---|---|
| `~/.omp/agent/config.yml` | `omp/config.yml` |
| `~/.omp/presets/` (`fast`, `smart`, `balanced`, `anthropic`, `openai`, `gemini`, `omp-presets.sh`) | `omp/presets/` |
| `~/.claude/skills/omp-config-audit/` | `skills/omp-config-audit/` |
| `~/.claude/skills/omp-config-readme/` | `skills/omp-config-readme/` |
| `~/.claude/skills/omp-model-refresh/` | `skills/omp-model-refresh/` |

Never copied (see [`rsync-exclude.txt`](rsync-exclude.txt)): `*.bak-*` backups, `*.lock`, `__pycache__/`, `*.pyc`, `.DS_Store`, and `catalog-snapshot.json`.

Deliberately **not** tracked:

- omp state: `~/.omp/agent/*.db` (auth tokens, history, model cache), `sessions/`, `blobs/`, `logs/`, `run/`, `cache/`.
- Vendor skill packs in `~/.claude/skills` (`cloudflare*`, `wrangler`, `agents-sdk`, …): reinstall them from their source.
- Skills that are symlinks into other git repos: they are already versioned there.
- `~/.omp/presets/catalog-snapshot.json`: `omp-model-refresh`'s baseline of the Copilot and Cursor model catalogs (vendor data). On a new machine the skill's first run saves a fresh baseline.
- `~/.omp/agent/extensions/orca-*.ts` (installed by Orca) and `~/.omp/agent/tools/yt-dlp` (binary).

## Requirements

- macOS or Linux with `bash`, `git`, `rsync`
- [`gitleaks`](https://github.com/gitleaks/gitleaks) for the secret scan: `brew install gitleaks`
- [`gh`](https://cli.github.com) logged in, to clone the private repo

## Install

### On this machine (already set up)

Add the scripts to your `PATH` in `~/.zshrc`:

```bash
export PATH="$HOME/github/luismoriguerra/omp-config-helpers/bin:$PATH"
```

Optional reminder when the repo falls behind the live files, also in `~/.zshrc`:

```bash
omp-status >/dev/null 2>&1 || echo "omp-config-helpers: unsynced omp changes (run omp-status / omp-sync)"
```

### On a new machine

```bash
brew install gitleaks
gh repo clone luismoriguerra/omp-config-helpers ~/github/luismoriguerra/omp-config-helpers
echo 'export PATH="$HOME/github/luismoriguerra/omp-config-helpers/bin:$PATH"' >> ~/.zshrc
exec zsh

omp-restore            # preview, confirm, copy repo -> live paths
```

Then wire the preset shell functions (they are restored to `~/.omp/presets/omp-presets.sh`):

```bash
echo 'source "$HOME/.omp/presets/omp-presets.sh"' >> ~/.zshrc
```

Log in to your providers in omp again: credentials live in omp's databases and are never in this repo.

Machine-specific roles (for example `tiny: local/falcon-h1-90m`, which needs the local model) may need editing after a restore.

## Usage

### Save local changes (the normal direction)

Edit config, presets, or skills in place (or let omp change them), then:

```bash
omp-status                    # optional: what changed since the last sync (read-only)
omp-sync                      # copy in, secret-scan, commit "sync <date>", push
omp-sync "fast: composer-2.5" # same, with your own commit message
omp-sync --no-push            # commit locally only
```

`omp-sync` prints `no changes` and exits when the repo already matches.

### Bring repo changes back to the live files

Use this after editing in GitHub, on another machine, or to roll back:

```bash
omp-restore            # git pull --ff-only, preview, ask, apply
omp-restore --no-pull  # apply the current checkout (for example after `git checkout <commit> -- omp/`)
omp-restore -y         # skip the confirmation
```

Before changing anything, `omp-restore` copies each live path it is about to change into `~/.omp-config-helpers-backups/<timestamp>/` (outside `~/.claude/skills`, so backups are never loaded as duplicate skills).

Rolling back one file to an older version:

```bash
cd ~/github/luismoriguerra/omp-config-helpers
git log --oneline -- omp/presets/fast.yml
git checkout <commit> -- omp/presets/fast.yml
omp-restore --no-pull
omp-sync "revert fast preset"   # record the rollback
```

### Track another file or skill

Add a line to [`manifest.txt`](manifest.txt) (`<live path> <repo path>`), then run `omp-sync`. Directories need a trailing `/` on both sides; a single file must keep the same file name on both sides.

To stop tracking something, remove its line and delete its repo copy (`git rm -r <repo path>`), then commit. The live files are not touched.

## Example prompts

The skills run from `~/.claude/skills/`; this repo is their backup. Ask the agent in plain language; naming the skill makes the match certain.

### `omp-config-readme`: explain the setup (never changes anything)

- "Remind me how my omp setup works."
- "What's the difference between `omp-fast` and `omp-balanced`?"
- "What does the `smol` role do, and when does omp use it?"
- "How do presets merge with my global `config.yml`?"
- "What does `prewalk` do in my balanced preset?"
- "Where do my fallback chains live, and what happens when Copilot is down?"
- "How do I create my own preset and run it with `ompp`?"

### `omp-config-audit`: check config and presets (report-only unless you say apply)

- "Audit my omp config."
- "Run omp-config-audit on the fast preset only and tell me what to change."
- "Is any of my config sending data outside Copilot and Cursor?"
- "Check whether my gemini preset is really Gemini-only."
- "Audit my config and propose the YAML to remove the Anthropic web fallback. Don't apply."
- "Apply the audit's proposed fix for the `web` chain, then run omp-sync."

### `omp-model-refresh`: new or changed models (report-only unless you say apply)

- "Refresh my omp models. What changed in the Copilot and Cursor catalogs?"
- "Gemini 4 Hydrogen just came out. Should any of my presets use it?"
- "Are there better models now for my fast preset? Benchmark the candidates."
- "Compare composer-2.5 and composer-2.5-fast for my `default` role."
- "Do a monthly model check and recommend role changes per preset."
- "Apply the recommended `fast.yml` changes, save the catalog snapshot, then omp-sync."

### This repo: `omp-sync`, `omp-status`, `omp-restore`

- "Run omp-status and tell me what changed since my last sync."
- "omp-sync with message 'smart: bump advisor to gpt-6.1-sol'."
- "Show the git history of my fast preset in omp-config-helpers."
- "Roll my fast preset back to its previous version using omp-config-helpers, then omp-sync the rollback."
- "Add my `disk-space-audit` skill to omp-config-helpers and sync it."
- "Set up omp-config-helpers on this new machine." (clone, `omp-restore`, `PATH`, re-login)

### Chained

- "Check for new models, audit my config against them, and give me one report. Don't change anything."
- "Apply the recommendations I approved: back up, edit, smoke-test, re-run the audit, then omp-sync."

### Notes

- Audit and refresh never change anything until you say "apply" with the exact change.
- After editing a skill, its `SKILL.md`, or a preset by hand, run `omp-sync`. The repo only updates when sync runs.
- To change a skill, edit it in `~/.claude/skills/<name>/`, not the repo copy: `omp-sync` copies from the live folder and overwrites the repo copy.

## Secret scanning

`omp-sync` runs `gitleaks git --pre-commit --staged` on every sync, using the default gitleaks rules ([`.gitleaks.toml`](.gitleaks.toml)). The rules look for real credential shapes (API key formats, high-entropy values), not words, so settings such as `maxTokens` or `--max-tokens` do not trigger it.

If it blocks a sync, nothing is committed and the staged changes are unstaged:

- **Real secret:** remove it from the live file, then rerun `omp-sync`.
- **False positive:** copy the `Fingerprint:` line from the report into [`.gitleaksignore`](.gitleaksignore), then rerun `omp-sync`. Fingerprints pin one finding at one location, so the allowlist never hides a different secret.

## Layout

```
bin/omp-sync         live -> repo, scan, commit, push
bin/omp-status       read-only drift check (exit 1 when live differs from repo)
bin/omp-restore      repo -> live, with preview, confirmation and backups in ~/.omp-config-helpers-backups/
bin/lib.sh           shared manifest parsing and the rsync wrapper
manifest.txt         what is tracked
rsync-exclude.txt    never copied in either direction
.gitleaks.toml       secret scan rules (gitleaks defaults)
.gitleaksignore      reviewed false positives, by fingerprint
omp/                 snapshot of ~/.omp config and presets
skills/              snapshot of custom omp skills
```
