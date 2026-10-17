#!/usr/bin/env bash
# Privacy scan: run before every push (CI runs it too). Exits 1 on any hit.
# Scans every file git would ship (tracked + untracked, minus .gitignore) for: home-directory paths, key-looking
# strings, private client / cast names, and any file over 2 MB.
# usage: bash tools/scan_private.sh
# Excluded: this file (it has to name the patterns).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2

# Patterns are assembled from pieces so this file does not match itself if the exclusion is ever dropped.
home="/User""s/"
user="douglas""feirstein"
keys='\bsk-[A-Za-z0-9_-]{16,}|\bsk_[A-Za-z0-9]{16,}|xi-api-key["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|\bhf_[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9._-]{20,}'
names="Dry""ver|Jerk""Check|Jerk Check|Jee""vz|Mah""jong|Casey Re""ed"

files=()
while IFS= read -r f; do
  case "$f" in
    tools/scan_private.sh) continue ;;
  esac
  [ -f "$f" ] && files+=("$f")
done < <(git ls-files -co --exclude-standard)

hits=0
report() { echo "HIT [$1] $2"; hits=$((hits + 1)); }

while IFS= read -r line; do [ -n "$line" ] && report "path" "$line"; done \
  < <(grep -nIF -e "$home" -e "$user" -- "${files[@]}" 2>/dev/null)
while IFS= read -r line; do [ -n "$line" ] && report "key" "$line"; done \
  < <(grep -nIE -e "$keys" -- "${files[@]}" 2>/dev/null)
while IFS= read -r line; do [ -n "$line" ] && report "name" "$line"; done \
  < <(grep -nIiE -e "$names" -- "${files[@]}" 2>/dev/null)
for f in "${files[@]}"; do
  size=$(wc -c < "$f" | tr -d ' ')
  [ "$size" -gt 2097152 ] && report "size" "$f ($size bytes)"
done

echo "scanned ${#files[@]} files; excluded tools/scan_private.sh"
if [ "$hits" -gt 0 ]; then
  echo "FAIL: $hits hit(s)"
  exit 1
fi
echo "PASS: 0 hits"
