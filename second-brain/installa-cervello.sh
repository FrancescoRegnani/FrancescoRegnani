#!/usr/bin/env bash
# Copia il modello del second brain in ~/SecondBrain (fuori da questo repository:
# i dati dei clienti NON devono finire su GitHub). Non sovrascrive mai file esistenti.
# Uso: bash second-brain/installa-cervello.sh [--aggiorna] [cartella-destinazione]
#   --aggiorna  sostituisce con l'ultima versione SOLO procedure (.claude) e modelli
#               (_modello-cliente, _modello-immobile). Mappa, memoria e dati restano intatti.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/cervello" && pwd)"
AGGIORNA=0
if [ "${1:-}" = "--aggiorna" ]; then AGGIORNA=1; shift; fi
DEST="${1:-$HOME/SecondBrain}"

mkdir -p "$DEST"
# Copia file per file, anche quelli nascosti (.claude), saltando quelli che esistono già
(cd "$SRC" && find . -type f) | while IFS= read -r f; do
  case "$f" in
    ./.claude/*|./clienti/_modello-cliente/*|./immobili/_modello-immobile/*) aggiornabile=1 ;;
    *) aggiornabile=0 ;;
  esac
  if [ ! -e "$DEST/$f" ] || { [ "$AGGIORNA" = 1 ] && [ "$aggiornabile" = 1 ]; }; then
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

if [ "$AGGIORNA" = 1 ] && [ -d "$DEST/.git" ]; then
  git -C "$DEST" add -A
  git -C "$DEST" -c user.name="Second Brain" -c user.email="brain@localhost" commit -qm "Aggiornate procedure e modelli" || true
fi

echo "Second brain pronto in: $DEST"
echo
echo "Prossimi passi:"
echo "  cd \"$DEST\""
echo "  claude"
echo "  /intervista"
