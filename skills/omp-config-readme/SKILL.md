---
name: omp-config-readme
description: >-
  Teaches and explains Luis's omp (Oh My Pi) model setup on demand: model roles,
  presets (omp-fast, omp-smart, omp-balanced, omp-anthropic, omp-openai, omp-gemini, ompp), config layers and merge
  rules, fallback chains, advisor, prewalk, provider boundary, and the
  omp-config-audit / omp-model-refresh skills. Use when the user asks how
  something in their omp config works, what a role or setting means, how to use
  a preset or skill, where a file lives, or "remind me how my omp setup works".
  Explain-only; route changes to omp-config-audit or omp-model-refresh.
---

# omp config readme

Answer questions about the omp model setup, and teach the concepts behind it.

## How to answer

1. **Find the topic** in `reference.md` (same directory) and read only the sections you need:
   1. big picture
   2. files
   3. daily use
   4. concepts (roles, selectors, merge rules, profiles vs overlays, fallback chains, advisor, prewalk, boundary)
   5. how-to recipes
   6. gotchas
   7. why the setup looks like this
   8. sources
2. **Get live values** whenever the answer involves what is configured *now* (which model a role or preset uses, settings, wiring, snapshot age):
   ```bash
   bash ~/.claude/skills/omp-config-readme/scripts/overview.sh
   ```
   Never state current models from memory or from section 7, which is a dated history.
3. **Answer short and concretely.** Use the user's actual commands and paths, plus one example. For "how does X work", give the rule, then what it means in this setup.
4. **Route actions.** This skill only explains.
   - Evaluate or fix the config: the `omp-config-audit` skill.
   - Find newer or better models: the `omp-model-refresh` skill.
   - When the user asks how to use those skills, use reference §5 and their own `SKILL.md`.

## Quick answers

- **"Which preset should I use?"** Answer from reference §3 "Which preset when". In short: `omp` by default, `omp-fast` for obvious small edits, `omp-smart` for hard or risky work, `omp-balanced` for planned mechanical changes, and `omp-anthropic` / `omp-openai` / `omp-gemini` to switch model family (second opinion, quota or outage).
- **"What model am I on?"** Inside a session, `/model` → Roles. From the shell, run `overview.sh`.
- **"Why didn't my change apply?"** Running sessions don't reload presets, a project `.omp/config.yml` may override, or `omp config get` was used with `--config`, which it ignores. See reference §6.
- **"Is my code staying within GitHub and Cursor?"** Not enforced while `disabledProviders` is empty. See reference §4 (Provider boundary), and run the audit.
