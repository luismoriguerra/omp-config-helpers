# Shared helpers for omp-sync / omp-status / omp-restore. Sourced, not executed.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXCLUDE="$REPO/rsync-exclude.txt"

# Prints "<live> <repo-relative>" per manifest entry, with ~ expanded.
manifest_entries() {
  local live dst
  while read -r live dst; do
    case "$live" in ''|'#'*) continue ;; esac
    [ -n "$dst" ] || { echo "manifest.txt: missing repo path for $live" >&2; return 1; }
    case "$live" in '~/'*) live="$HOME/${live#\~/}" ;; esac
    printf '%s %s\n' "$live" "$dst"
  done < "$REPO/manifest.txt"
}

# rsync <src> <dst> [extra rsync flags].
# Directory entries (trailing /) mirror contents, including deletions.
# File entries sync into dst's parent directory: macOS openrsync reports a phantom
# transfer for every file-to-file-path copy, so both sides must share a basename.
mirror() {
  local src="$1" dst="$2"
  shift 2
  case "$src" in
    */) rsync -a --delete --exclude-from="$EXCLUDE" "$@" "$src" "$dst" ;;
    *)
      [ "$(basename "$src")" = "$(basename "$dst")" ] || {
        echo "manifest.txt: $src and $dst must have the same file name" >&2; return 1; }
      rsync -a --exclude-from="$EXCLUDE" "$@" "$src" "$(dirname "$dst")/" ;;
  esac
}

has_remote() { [ -n "$(git -C "$REPO" remote)" ]; }
