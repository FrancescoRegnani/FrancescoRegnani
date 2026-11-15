# Second Brain con Claude — Guida passo passo

Ricostruzione del metodo del video **"DON'T Use Obsidian, Build a Claude Second Brain! (Tutorial)"**
(https://www.youtube.com/watch?v=kG_CoTjCC98).

L'idea del video: il 99% dei "second brain" con l'AI si limita a **ricordare** (una pila di note
collegate, tipo Obsidian). Il problema è che tu cambi — lavoro, gusti, progetti — e un archivio di
note non sa cosa è ancora vero. Il video propone invece un cervello che:

1. **ragiona** su tutto quello che gli dici (non solo lo archivia);
2. **si aggiorna da solo** quando qualcosa cambia;
3. è **uno solo, condiviso** tra Claude Code, Codex e qualsiasi altro strumento userai in futuro.

Lo strumento usato è **[Honcho](https://honcho.dev)** (di Plastic Labs, open source), collegato a
Claude Code tramite il plugin ufficiale `claude-honcho`, che lavora con gli **hook** di Claude Code.

---

## I concetti del video (in breve)

| Capitolo del video | Cosa significa in pratica |
|---|---|
| **Il mito di Obsidian** | Le note collegate sono statiche: nessuno ti dice quando una nota è diventata falsa. |
| **I 4 problemi della memoria** | La memoria classica è: frammentata per strumento, statica, solo "archivio", e va alimentata a mano. |
| **Un unico cervello condiviso** | Tutti gli strumenti scrivono e leggono dallo **stesso workspace** Honcho, con la **stessa identità** (peer) per te. |
| **Peer card** | Honcho mantiene una "scheda" strutturata su di te (chi sei, preferenze, progetti) che viene iniettata a inizio sessione. |
| **Sogna ("It dreams")** | In background Honcho rielabora le conversazioni ("dreaming"), consolida le conclusioni e scarta quelle superate. |
| **Un avvertimento** | Tutto ciò che dici a Claude finisce nella memoria: attenzione a dati sensibili (vedi sezione *Privacy*). |
| **Perché servono gli hook** | Gli hook salvano automaticamente ogni conversazione e reiniettano il contesto: non devi ricordarti di "salvare". |
| **Locale o cloud?** | Honcho Cloud (API key, zero manutenzione) oppure Honcho in locale con Docker (privato, gratis a parte il modello LLM). |

---

## Cosa trovi in questa cartella

| File | A cosa serve |
|---|---|
| `README.md` | Questa guida. |
| `setup.sh` | Script che crea `~/.honcho/config.json` già configurato come "cervello unico condiviso". |
| `config.example.json` | Esempio commentato della configurazione condivisa (Claude Code + Codex + Cursor). |
| `AGENTS.md.example` | Istruzioni da copiare in `~/.codex/AGENTS.md` per far usare la memoria anche a Codex. |
| `../.claude/settings.json` | Fa sì che, aprendo questo repo in Claude Code, ti venga proposto il plugin Honcho. |

> Tutto questo va eseguito **sul tuo computer** (Mac/PC), dove usi Claude Code ogni giorno.
> La memoria vive in `~/.honcho/` sul tuo computer e nel server Honcho, non in questo repository.

---

## Passo 0 — Prerequisiti

- **Claude Code** installato (`claude` nel terminale).
- **Node.js** installato (serve agli hook del plugin): https://nodejs.org
- Solo per l'opzione locale: **Docker Desktop** e **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

## Passo 1 — Scegli: cloud o locale

### Opzione A — Honcho Cloud (consigliata per iniziare)

1. Vai su https://app.honcho.dev, registrati, copia la API key (inizia con `hch-`).
2. Nel terminale:

```bash
export HONCHO_API_KEY="hch-la-tua-chiave"
```

### Opzione B — Honcho in locale (privato)

Serve una chiave di un provider LLM (es. OpenAI, oppure OpenRouter/Ollama compatibili) che Honcho
usa per estrarre conclusioni, riassumere e "sognare".

```bash
uv tool install honcho-cli
```

```bash
honcho start --setup
```

Il wizard avvia API, deriver (il processo che "ragiona" in background), Postgres e Redis in Docker,
su `http://localhost:8000`.

## Passo 2 — Crea la configurazione del cervello unico

Dalla cartella di questo repository:

```bash
bash second-brain/setup.sh
```

Lo script ti chiede il tuo nome (la tua identità nella memoria) e se usi cloud o locale, poi scrive
`~/.honcho/config.json`. Se il file esiste già ne fa una copia di backup prima di sovrascriverlo.

Il punto chiave (quello del capitolo *"One shared brain"*) è che la config imposta:

- `globalOverride: true` + `workspace: "second-brain"` → **tutti** gli strumenti usano lo stesso workspace;
- lo stesso `peerName` per te ovunque → Honcho costruisce **una sola** rappresentazione di te;
- `observationMode: "unified"` → le conclusioni su di te sono portabili tra agenti.

> Di default ogni plugin Honcho usa un workspace separato per strumento: senza questi tre punti
> avresti tanti cervelli piccoli invece di uno solo.

## Passo 3 — Installa il plugin in Claude Code

Apri Claude Code e scrivi:

```
/plugin marketplace add plastic-labs/claude-honcho
```

```
/plugin install honcho@honcho
```

Poi esci (`/exit`) e riavvia `claude`. All'avvio vedrai il logo Honcho e il caricamento della memoria.

> Se apri **questo repository** in Claude Code, il file `.claude/settings.json` ti propone già il
> marketplace e il plugin: basta accettare.

### Cosa fanno gli hook (capitolo *"Why hooks matter"*)

Il plugin registra degli hook di Claude Code che, senza che tu faccia nulla:

- **a inizio sessione** iniettano: istruzioni sull'uso della memoria, il riassunto della sessione e la tua **peer card**;
- **a ogni messaggio** cercano nella tua memoria le conclusioni rilevanti per quella domanda e le aggiungono al contesto;
- **dopo ogni scambio** salvano la conversazione in Honcho, che in background ne ricava conclusioni.

## Passo 4 — Riempi il cervello (intervista iniziale)

In Claude Code:

```
/honcho:interview
```

Claude ti fa domande su di te, il tuo lavoro e le tue preferenze e crea la prima peer card.
Vale per tutti i progetti, perché è legata al tuo `peerName`.

Opzionale — importa le vecchie sessioni di Claude Code:

```
/honcho:import
```

## Passo 5 — Collega anche Codex (stesso cervello)

```bash
npm install -g @honcho-ai/codex-honcho
```

```bash
codex-honcho install
```

Poi copia il contenuto di `second-brain/AGENTS.md.example` in `~/.codex/AGENTS.md` e riavvia Codex.
Codex legge lo stesso `~/.honcho/config.json`, quindi lavora sullo stesso workspace `second-brain`.

## Passo 6 — Usalo ogni giorno

Comandi utili in Claude Code:

| Comando | A cosa serve |
|---|---|
| `/honcho:status` | Stato della memoria e connessione. |
| `/honcho:config` | Menu di configurazione (cosa iniettare, strategia sessioni…). |
| `/honcho:insights` | Trasforma la memoria in modifiche a `CLAUDE.md`, regole di stile e idee di skill. |

Cose che puoi chiedere direttamente:

- *"Cosa sai di me?"* → usa la ricerca/dialettica sulla tua rappresentazione.
- *"Ricordati che da oggi lavoro su ProExam invece che su X"* → crea una nuova conclusione; quelle vecchie vengono superate.
- *"Dimentica che…"* → Claude può cancellare una conclusione (`delete_conclusion`).
- *"Imposta rememberTool a true"* → abilita lo strumento `honcho_remember` per richiami più profondi (richiede riavvio).

---

## Privacy (il "warning" del video)

- Con Honcho Cloud le conversazioni vengono inviate ai server di Plastic Labs. Se lavori con dati
  di clienti dello studio, valuta **l'opzione locale** oppure disattiva il salvataggio dove serve.
- Disattivare temporaneamente: `/plugin` → disabilita `honcho`, oppure `export HONCHO_ENABLED=false`.
- Leggere ma non scrivere: `"saveMessages": false` in `~/.honcho/config.json`.
- Il plugin oscura automaticamente segreti comuni (API key, token) dai riepiloghi degli strumenti;
  puoi aggiungere pattern tuoi in `redactPatterns`.
- I log sono in `~/.honcho/`.

## Risoluzione problemi

| Problema | Soluzione |
|---|---|
| "Not configured" / nessuna memoria all'avvio | Controlla `~/.honcho/config.json` (apiKey o endpoint locale), poi `/honcho:setup`. |
| Il plugin non parte | Verifica che `node --version` funzioni nel terminale da cui lanci `claude`. |
| Codex non vede la memoria di Claude | Controlla che in `config.json` ci siano `globalOverride: true` e lo stesso `peerName`. |
| Contesto iniettato poco pertinente | Abbassa `injection.searchMaxDistance` (es. 0.5); se è troppo scarso, alzalo o aumenta `searchTopK`. |

Fonti: documentazione ufficiale Honcho per
[Claude Code](https://honcho.dev/docs/v3/guides/integrations/claude-code),
[Codex](https://honcho.dev/docs/v3/guides/integrations/codex),
[memoria unificata](https://honcho.dev/docs/v3/guides/recipes/unified-memory-setup) e
[installazione locale](https://honcho.dev/docs/v3/contributing/self-hosting).
