#!/usr/bin/env bash
# SessionStart: dà all'agente data di oggi, ultime voci di memoria e inbox da smistare.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
echo "Oggi è $(date +%Y-%m-%d)."
if [ -f MEMORY.md ]; then
  echo "--- Ultime voci di MEMORY.md ---"
  head -n 40 MEMORY.md
fi
n=$(find inbox -type f ! -name '.gitkeep' 2>/dev/null | wc -l | tr -d ' ')
[ "$n" != "0" ] && echo "--- Inbox: $n file da smistare ---"
exit 0
