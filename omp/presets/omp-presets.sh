# Source from ~/.zshrc:  source "$HOME/.omp/presets/omp-presets.sh"
# Each preset is a read-only overlay (omp --config) on top of ~/.omp/agent/config.yml,
# so login, sessions and everything not listed in the overlay are shared with plain `omp`.
_omp_preset() {
  local name="$1"; shift
  omp --config "$HOME/.omp/presets/$name.yml" "$@"
}
omp-fast()     { _omp_preset fast "$@"; }
omp-smart()    { _omp_preset smart "$@"; }
omp-balanced() { _omp_preset balanced "$@"; }
omp-anthropic() { _omp_preset anthropic "$@"; }
omp-openai()   { _omp_preset openai "$@"; }
omp-gemini()   { _omp_preset gemini "$@"; }
# generic form: ompp <fast|smart|balanced|anthropic|openai|gemini|your-own> [omp args...]
ompp()         { _omp_preset "$@"; }
