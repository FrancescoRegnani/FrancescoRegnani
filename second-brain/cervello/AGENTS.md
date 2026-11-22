# AGENTS.md — La mappa del mio second brain

> Questo file è la **mappa del palazzo**. Ogni agente (Claude Code, Codex, ChatGPT Work,
> Antigravity…) lo legge per primo. Resta **snello**: indica *dove* sono le cose,
> non le contiene. Leggi gli altri file **solo quando servono** al compito.

## Chi sono
<!-- Compilato da /intervista. Massimo 5 righe. -->
- Nome: Francesco
- Lavoro: _(da completare con /intervista)_
- Come voglio le risposte: italiano, diretto, prima la conclusione poi i dettagli.

## Il palazzo (dove si trova cosa)
| Stanza | Cosa contiene | Quando aprirla |
|---|---|---|
| `MEMORY.md` | Diario di bordo generale: decisioni, cose in sospeso | Sempre, a inizio lavoro (solo le ultime voci) |
| `reference/` | **Biblioteca**: modelli, strutture, esempi buoni (offerte, pareri, email) | Quando produci un documento che ha un modello |
| `clienti/<nome>/` | **Ali** dei clienti: ognuna ha il suo `AGENTS.md` e `MEMORY.md` | Quando il compito riguarda quel cliente |
| `immobili/<nome>/` | Immobili di **famiglia** (personali, separati dallo studio) | Quando il compito riguarda un immobile di famiglia |
| `progetti/<nome>/` | Progetti personali (es. Abilita) | Quando il compito riguarda quel progetto |
| `scadenzari/` | Scadenzari salvati | Quando chiedo le scadenze |
| `inbox/` | Appunti grezzi, dettati, file da smistare | Quando chiedo di "smistare" o "elaborare l'inbox" |
| `archivio/` | Clienti e progetti chiusi | Solo se lo chiedo esplicitamente |
| `.claude/skills/` | **Manuale delle procedure** ripetibili | Vedi sotto |

## Le strade (collegamenti esterni)
- Gmail e Google Drive via MCP: **solo lettura**, salvo mia richiesta esplicita.
- Memoria Honcho (se attiva): ricorda chi sono tra sessioni e strumenti.

## Procedure (skill)
Per altri agenti: le procedure sono file di istruzioni in `.claude/skills/<nome>/SKILL.md`.
- `intervista` — crea o aggiorna questa mappa intervistandomi
- `nuovo-cliente` — apre una nuova ala cliente dal modello (con periodicità mensile/trimestrale)
- `nuovo-immobile` — crea la scheda di un immobile di famiglia
- `scadenzario` — scadenze del periodo per clienti (mensili, trimestrali, enti) e immobili
- `brief-cliente` — scrive il brief di un cliente da email e Drive
- `offerta` — prepara un'offerta seguendo `reference/struttura-offerta.md`
- `pulisci-dettato` — trasforma un dettato vocale in un prompt pulito
- `chiudi-sessione` — a fine lavoro aggiorna memoria, mappa e biblioteca

## Regole del palazzo
1. Non leggere tutto: parti da questa mappa e apri solo i file necessari.
2. Ogni cliente vive nella sua ala; non mescolare informazioni tra clienti.
   Gli affitti dei clienti stanno nell'ala del cliente; gli immobili di famiglia in `immobili/`.
3. Non inventare dati: se manca un'informazione, chiedila o segnalala.
4. Prima di inviare, cancellare o condividere qualcosa all'esterno, chiedi conferma.
5. A fine sessione proponi `chiudi-sessione`.
