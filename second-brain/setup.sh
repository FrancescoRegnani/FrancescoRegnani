#!/usr/bin/env bash
# Crea ~/.honcho/config.json configurato come un unico "second brain" condiviso
# tra Claude Code, Codex e Cursor. Uso: bash second-brain/setup.sh <nome> [cloud|locale]
set -euo pipefail

CONFIG_DIR="${HONCHO_CONFIG_DIR:-$HOME/.honcho}"
CONFIG_FILE="$CONFIG_DIR/config.json"

echo "== Second Brain (Honcho) — configurazione =="

# Uso senza domande:
#   1) copia la API key (hch-...) da app.honcho.dev
#   2) bash second-brain/setup.sh francesco        (cloud, chiave letta dagli appunti)
#      bash second-brain/setup.sh francesco locale (Honcho in locale, nessuna chiave)
peer="${1:-${HONCHO_PEER_NAME:-${USER:-me}}}"
mode="${2:-cloud}"
# solo lettere, numeri, - e _
peer="$(printf '%s' "$peer" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | sed 's/-*$//')"

if [[ "$mode" == "locale" || "$mode" == "local" || "$mode" == "l" ]]; then
  key_line=""
  endpoint='{ "environment": "local" }'
else
  key="${HONCHO_API_KEY:-}"
  # Mac: prende la chiave dagli appunti (quello che hai copiato con Cmd+C)
  if [[ -z "$key" ]] && command -v pbpaste >/dev/null 2>&1; then
    key="$(pbpaste | tr -d '[:space:]')"
  fi
  if [[ "$key" != hch-* ]]; then
    echo "Errore: non trovo la API key." >&2
    echo "Copia la chiave (inizia con hch-) da app.honcho.dev con Cmd+C e rilancia il comando." >&2
    exit 1
  fi
  key_line="  \"apiKey\": \"$key\","
  endpoint='{ "environment": "production" }'
fi

mkdir -p "$CONFIG_DIR"
if [[ -f "$CONFIG_FILE" ]]; then
  backup="$CONFIG_FILE.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CONFIG_FILE" "$backup"
  echo "Config esistente salvata in: $backup"
fi

{
  echo "{"
  [[ -n "$key_line" ]] && echo "$key_line"
  cat <<EOF
  "peerName": "$peer",
  "globalOverride": true,
  "workspace": "second-brain",
  "hosts": {
    "claude_code": { "aiPeer": "claude", "rememberTool": false },
    "codex": { "aiPeer": "codex" },
    "cursor": { "aiPeer": "cursor" }
  },
  "observationMode": "unified",
  "sessionStrategy": "per-directory",
  "saveMessages": true,
  "saveToolUse": false,
  "saveGitEvents": false,
  "reasoningLevel": "medium",
  "injection": {
    "sessionStart": ["directives", "summary", "peerCard"],
    "perTurn": ["userContext"]
  },
  "endpoint": $endpoint,
  "statusline": "on",
  "enabled": true,
  "logging": true
}
EOF
} > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"

echo
echo "Creato $CONFIG_FILE (workspace condiviso: second-brain, peer: $peer)"
echo
echo "Prossimi passi in Claude Code:"
echo "  /plugin marketplace add plastic-labs/claude-honcho"
echo "  /plugin install honcho@honcho"
echo "  (riavvia claude)"
echo "  /honcho:interview"
