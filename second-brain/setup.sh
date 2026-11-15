#!/usr/bin/env bash
# Crea ~/.honcho/config.json configurato come un unico "second brain" condiviso
# tra Claude Code, Codex e Cursor. Uso: bash second-brain/setup.sh
set -euo pipefail

CONFIG_DIR="${HONCHO_CONFIG_DIR:-$HOME/.honcho}"
CONFIG_FILE="$CONFIG_DIR/config.json"

echo "== Second Brain (Honcho) — configurazione =="

default_peer="${HONCHO_PEER_NAME:-${USER:-me}}"
read -r -p "Il tuo nome nella memoria (peerName) [$default_peer]: " peer
peer="${peer:-$default_peer}"
# solo lettere, numeri, - e _
peer="$(printf '%s' "$peer" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | sed 's/-*$//')"

read -r -p "Usi Honcho Cloud (c) o locale (l)? [c]: " mode
mode="${mode:-c}"

if [[ "$mode" == "l" || "$mode" == "L" ]]; then
  key_line=""
  endpoint='{ "environment": "local" }'
else
  key="${HONCHO_API_KEY:-}"
  if [[ -z "$key" ]]; then
    read -r -s -p "Incolla la API key di app.honcho.dev (hch-...): " key
    echo
  fi
  if [[ "$key" != hch-* ]]; then
    echo "Errore: la chiave deve iniziare con 'hch-'." >&2
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
    "claude_code": { "aiPeer": "claude", "rememberTool": true },
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
