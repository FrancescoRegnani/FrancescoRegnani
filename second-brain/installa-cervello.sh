#!/usr/bin/env bash
# Crea o aggiorna un second brain da questo modello. Funziona su Mac (Terminale) e
# Windows (Git Bash). I dati restano FUORI da questo repository: niente va su GitHub.
#
# Uso:
#   bash second-brain/installa-cervello.sh --profilo studio      # PC dello studio  → ~/SecondBrain-Studio
#   bash second-brain/installa-cervello.sh --profilo personale   # Mac di casa      → ~/SecondBrain
#   bash second-brain/installa-cervello.sh --aggiorna [--profilo …] [cartella]
#
#   --aggiorna  sostituisce con l'ultima versione SOLO procedure (.claude) e modelli
#               (_modello-cliente, _modello-immobile). Mappa, memoria e dati restano intatti.
set -euo pipefail
BASE="$(cd "$(dirname "$0")/cervello" && pwd)"

AGGIORNA=0; PROFILO=""; DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --aggiorna) AGGIORNA=1 ;;
    --profilo) shift; PROFILO="${1:-}" ;;
    *) DEST="$1" ;;
  esac
  shift
done

# Se la cartella esiste già, ricorda il profilo usato la prima volta
if [ -z "$PROFILO" ] && [ -n "$DEST" ] && [ -f "$DEST/.profilo" ]; then PROFILO="$(cat "$DEST/.profilo")"; fi
if [ -z "$PROFILO" ]; then
  for d in "$HOME/SecondBrain-Studio" "$HOME/SecondBrain"; do
    if [ "$AGGIORNA" = 1 ] && [ -f "$d/.profilo" ]; then PROFILO="$(cat "$d/.profilo")"; DEST="$d"; break; fi
  done
fi
case "$PROFILO" in
  studio)    DEST="${DEST:-$HOME/SecondBrain-Studio}" ;;
  personale) DEST="${DEST:-$HOME/SecondBrain}" ;;
  *) echo "Errore: indica il profilo: --profilo studio  oppure  --profilo personale" >&2; exit 1 ;;
esac

mkdir -p "$DEST"
copia() { # $1 = cartella sorgente; copia file per file, anche nascosti
  local src="$1"
  (cd "$src" && find . -type f) | while IFS= read -r f; do
    case "$f" in
      ./.claude/*|./clienti/_modello-cliente/*|./immobili/_modello-immobile/*) aggiornabile=1 ;;
      *) aggiornabile=0 ;;
    esac
    if [ ! -e "$DEST/$f" ] || { [ "$AGGIORNA" = 1 ] && [ "$aggiornabile" = 1 ] && [ "$src" = "$BASE/$PROFILO" ]; } \
       || { [ "$AGGIORNA" = 1 ] && [ "$aggiornabile" = 1 ] && [ ! -e "$BASE/$PROFILO/$f" ]; }; then
      mkdir -p "$DEST/$(dirname "$f")"
      cp -p "$src/$f" "$DEST/$f"
    fi
  done
}
copia "$BASE/$PROFILO"   # prima il profilo: i suoi file hanno la precedenza
copia "$BASE/comune"

# Con --aggiorna rimuove procedure e modelli dell'ALTRO profilo (es. il vecchio cervello unico),
# ma solo se identici al modello: ciò che hai modificato tu non viene toccato.
if [ "$AGGIORNA" = 1 ]; then
  ALTRO=studio; [ "$PROFILO" = studio ] && ALTRO=personale
  (cd "$BASE/$ALTRO" && find . -type f) | while IFS= read -r f; do
    case "$f" in ./.claude/*|./clienti/_modello-cliente/*|./immobili/_modello-immobile/*) ;; *) continue ;; esac
    [ -e "$BASE/$PROFILO/$f" ] || [ -e "$BASE/comune/$f" ] && continue
    if [ -f "$DEST/$f" ] && cmp -s "$BASE/$ALTRO/$f" "$DEST/$f"; then
      rm -f "$DEST/$f"; rmdir -p "$(dirname "$DEST/$f")" 2>/dev/null || true
    fi
  done
fi
echo "$PROFILO" > "$DEST/.profilo"
chmod +x "$DEST/.claude/hooks/apertura.sh" 2>/dev/null || true

# Cronologia locale delle modifiche (solo su questo computer, nessun invio online)
if command -v git >/dev/null 2>&1; then
  if [ ! -d "$DEST/.git" ]; then
    git -C "$DEST" init -q
    git -C "$DEST" add -A
    git -C "$DEST" -c user.name="Second Brain" -c user.email="brain@localhost" commit -qm "Second brain ($PROFILO): struttura iniziale"
  elif [ "$AGGIORNA" = 1 ]; then
    git -C "$DEST" add -A
    git -C "$DEST" -c user.name="Second Brain" -c user.email="brain@localhost" commit -qm "Aggiornate procedure e modelli" >/dev/null 2>&1 || true
  fi
fi

echo "Second brain ($PROFILO) pronto in: $DEST"
