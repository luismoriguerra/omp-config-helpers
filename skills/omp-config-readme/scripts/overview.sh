#!/usr/bin/env bash
# Live, read-only overview of the omp model setup: global roles, presets, wiring, skills, snapshot.
set -euo pipefail
unset PI_CONFIG_FILES   # an inherited overlay would otherwise be reported as "global"
cd "$(mktemp -d)"   # scratch cwd so no project .omp/config.yml layer interferes
P="$HOME/.omp/presets"
CFG="$HOME/.omp/agent/config.yml"
KEYS='default plan slow smol advisor'

get() {  # get <key> [overlay]
  if [[ -n "${2:-}" ]]; then PI_CONFIG_FILES="$2" omp config get "$1"; else omp config get "$1"; fi
}
summary() {  # summary [overlay]
  local roles; roles=$(get modelRoles "${1:-}")
  for k in $KEYS; do
    printf '  %-9s %s\n' "$k" "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get(sys.argv[2],"(auto)"))' "$roles" "$k")"
  done
  printf '  %-9s thinking=%s advisor=%s syncBacklog=%s prewalk=%s\n' "settings" \
    "$(get defaultThinkingLevel "${1:-}")" "$(get advisor.enabled "${1:-}")" \
    "$(get advisor.syncBacklog "${1:-}")" "$(get prewalk.enabled "${1:-}")"
}

echo "omp: $(omp --version)"
echo "global config: $CFG"
for b in "$CFG".bak-*; do [[ -e "$b" ]] && echo "  backup: $b"; done
echo "disabledProviders: $(get disabledProviders)"

echo; echo "## global (plain \`omp\`)"; summary
for f in "$P"/*.yml; do
  [[ -e "$f" ]] || continue
  n=$(basename "$f" .yml)
  echo; echo "## preset $n  (ompp $n$( [[ -n $(grep -s "^omp-$n()" "$P/omp-presets.sh") ]] && echo " | omp-$n"))  $f"
  summary "$f"
done

echo; echo "## wiring"
if grep -qs 'omp-presets.sh' "$HOME/.zshrc"; then echo "  ~/.zshrc sources omp-presets.sh: yes"; else echo "  ~/.zshrc sources omp-presets.sh: NO"; fi
for s in omp-config-audit omp-model-refresh omp-config-readme; do
  [[ -f "$HOME/.claude/skills/$s/SKILL.md" ]] && echo "  skill $s: installed" || echo "  skill $s: MISSING"
done
snap="$P/catalog-snapshot.json"
if [[ -f "$snap" ]]; then
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("  catalog snapshot: %s (%d models)" % (d["taken"], len(d["models"])))' "$snap"
else
  echo "  catalog snapshot: none (run omp-model-refresh)"
fi
