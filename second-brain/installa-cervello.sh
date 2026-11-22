#!/usr/bin/env bash
# Copia il modello del second brain in ~/SecondBrain (fuori da questo repository:
# i dati dei clienti NON devono finire su GitHub). Non sovrascrive mai file esistenti.
# Uso: bash second-brain/installa-cervello.sh [cartella-destinazione]
set -euo pipefail
SRC="$(cd "$(dirname "$0")/cervello" && pwd)"
DEST="${1:-$HOME/SecondBrain}"

mkdir -p "$DEST"
# Copia file per file, anche quelli nascosti (.claude), saltando quelli che esistono già
(cd "$SRC" && find . -type f) | while IFS= read -r f; do
  if [ ! -e "$DEST/$f" ]; then
    mkdir -p "$DEST/$(dirname "$f")"
    cp -p "$SRC/$f" "$DEST/$f"
  fi
done
chmod +x "$DEST/.claude/hooks/apertura.sh"

# Cronologia locale delle modifiche (solo sul tuo Mac, nessun invio online)
if command -v git >/dev/null 2>&1 && [ ! -d "$DEST/.git" ]; then
  git -C "$DEST" init -q
  git -C "$DEST" add -A
  git -C "$DEST" -c user.name="Second Brain" -c user.email="brain@localhost" commit -qm "Second brain: struttura iniziale"
fi

echo "Second brain pronto in: $DEST"
echo
echo "Prossimi passi:"
echo "  cd \"$DEST\""
echo "  claude"
echo "  /intervista"
