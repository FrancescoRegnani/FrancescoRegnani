# Il second brain "di ultimo livello"

Unisce due video:

1. **"Ho costruito un Second Brain che ricorda tutto!"** di *IA per tutti* (https://youtu.be/1cEYA04ZvIM):
   il cervello è una **cartella di file** organizzata come un palazzo. Una mappa (`AGENTS.md`) che
   **qualsiasi agente** legge: Claude Code, Codex, ChatGPT Work, Antigravity.
2. **Il video su Honcho** (guida in `README.md`): una **memoria che ragiona** su di te e si aggiorna da sola.

| Livello | Cosa ricorda | Dove vive |
|---|---|---|
| **Il palazzo** (file) | Clienti, documenti, modelli, procedure, decisioni: il *lavoro* | `~/SecondBrain` sul tuo Mac |
| **Honcho** (memoria) | Chi sei, come lavori, le tue preferenze: *te* | `~/.honcho` + server Honcho |

Il palazzo dice all'agente **dove sono le cose**. Honcho gli dice **chi sei**. Le skill gli dicono **come fai le cose**.

---

## Il palazzo, stanza per stanza

```
~/SecondBrain/
├── AGENTS.md          ← la MAPPA: la leggono tutti gli agenti (snella, solo puntatori)
├── CLAUDE.md          ← dice a Claude Code "leggi AGENTS.md" (così la mappa è una sola)
├── MEMORY.md          ← DIARIO DI BORDO generale: decisioni e cose in sospeso
├── reference/         ← BIBLIOTECA: modelli di offerte, pareri, email "buone"
├── clienti/           ← le ALI: una cartella per cliente
│   └── _modello-cliente/   (AGENTS.md + MEMORY.md + chiamate/ consulenza/ documenti/)
├── progetti/          ← progetti personali (es. ProExam)
├── inbox/             ← appunti grezzi e file da smistare
├── archivio/          ← clienti chiusi e memoria vecchia
└── .claude/
    ├── skills/        ← MANUALE DELLE PROCEDURE (vedi sotto)
    ├── hooks/apertura.sh   ← a ogni avvio carica data, ultime memorie e inbox
    └── settings.json
```

Le **strade** sono i collegamenti verso l'esterno: Gmail, Google Drive e gli altri connettori.

### Perché `AGENTS.md` e non solo `CLAUDE.md`
`AGENTS.md` è lo standard letto da Codex, ChatGPT Work, Antigravity e altri. `CLAUDE.md` contiene
solo `@AGENTS.md`, così Claude Code legge **la stessa mappa**. Cambi agente e il cervello resta lo stesso.

### Perché la mappa resta snella
Tutto ciò che sta in `AGENTS.md` occupa spazio in **ogni** conversazione. La mappa indica *dove*
guardare e l'agente apre i file solo quando servono. Così il contesto resta leggero e le risposte più precise.

## Le procedure (skill)

| Comando | Cosa fa |
|---|---|
| `/intervista` | Ti intervista (max 10 domande) e compila la mappa |
| `/nuovo-cliente` | Crea l'ala di un cliente dal modello |
| `/brief-cliente` | Legge Gmail e Drive (solo lettura) e scrive `brief.md` del cliente |
| `/offerta` | Prepara un'offerta seguendo il modello della biblioteca, anche in PDF |
| `/pulisci-dettato` | Trasforma un dettato vocale in una richiesta pulita |
| `/chiudi-sessione` | A fine lavoro aggiorna memoria, mappa, biblioteca e propone nuove skill |

La regola del video: **se fai una cosa due volte, diventa una skill.** `/chiudi-sessione` te lo propone da solo.

---

## Installazione (sul Mac)

### 1. Aggiorna il progetto
```bash
cd ~/FrancescoRegnani
```
```bash
git pull
```

### 2. Crea il cervello in `~/SecondBrain`
```bash
bash second-brain/installa-cervello.sh
```
Non sovrascrive mai file esistenti, quindi puoi rilanciarlo senza problemi. Crea anche una cronologia
locale delle modifiche (git solo sul Mac, niente viene inviato online).

### 3. Aprilo con Claude Code
```bash
cd ~/SecondBrain
```
```bash
claude
```
Alla domanda "Do you trust this folder?" rispondi **Yes**.

### 4. Fai l'intervista
```
/intervista
```

### 5. Collega Gmail e Google Drive (le "strade")
In Claude Code scrivi `/mcp` e collega Gmail e Google Drive, oppure usa i connettori di claude.ai.
Poi prova:
```
/nuovo-cliente
```
```
/brief-cliente
```

### 6. Ogni giorno
- Apri sempre Claude Code **dentro `~/SecondBrain`**.
- Butta appunti e PDF in `inbox/` e chiedi "smista l'inbox".
- Per i modelli: metti un PDF buono in `inbox/` e chiedi di ricavarne la struttura in `reference/`.
- A fine lavoro: `/chiudi-sessione`.

### Usare lo stesso cervello con altri agenti
- **Codex**: `cd ~/SecondBrain && codex` legge `AGENTS.md` da solo.
- **ChatGPT Work / Antigravity**: apri la cartella `~/SecondBrain` come progetto o workspace.
  Le skill sono normali file di istruzioni in `.claude/skills/`, e la mappa dice dove trovarle.
- **Obsidian** (opzionale, per sfogliarlo): apri `~/SecondBrain` come vault. Sono tutti file Markdown.

---

## Privacy (importante per uno studio)
- Il cervello sta in `~/SecondBrain`, **fuori** dal repository GitHub: i dati dei clienti non vanno online.
  Nel repository c'è solo il modello vuoto.
- Il contenuto dei file che l'agente legge viene inviato al fornitore del modello (Anthropic, OpenAI…)
  durante la conversazione. Valuta cosa metterci in base agli obblighi di riservatezza e al GDPR.
- Se Honcho è attivo in cloud, anche le conversazioni vanno ai server Honcho. Per le sessioni sui
  clienti puoi sospenderlo con `/plugin` (disabilita honcho) oppure usare Honcho in locale.
- Connettori Gmail/Drive: le skill li usano **solo in lettura**. L'agente deve chiedere conferma
  prima di inviare, cancellare o condividere.
- Fai un backup di `~/SecondBrain`, per esempio con Time Machine.
