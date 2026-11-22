---
name: brief-cliente
description: Scrive o aggiorna il brief di un cliente leggendo email (Gmail) e documenti (Google Drive) tramite MCP. Usala con /brief-cliente o quando l'utente chiede "fammi il punto su <cliente>".
---

# Brief cliente

1. Apri `clienti/<cliente>/AGENTS.md` e `MEMORY.md`.
2. Se i connettori Gmail/Drive sono disponibili, **solo in lettura**:
   - cerca le email degli ultimi 90 giorni con il cliente (nome, dominio, referente);
   - cerca su Drive i documenti con il nome del cliente.
   Se non sono collegati, usa solo i file locali e dillo.
3. Scrivi `clienti/<cliente>/brief.md` con:
   - **Situazione in 3 righe**
   - **Pratiche aperte** (con scadenze)
   - **Ultimi contatti** (data, canale, tema — con link/ID email)
   - **Documenti chiave** (link Drive)
   - **Cose in sospeso e prossimi passi**
   - **Fonti** usate
4. Segnala esplicitamente ciò che è incerto. Non inviare email, non modificare file su Drive.
5. Aggiungi una voce in `MEMORY.md` del cliente.
