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

## Due cervelli, due computer

| | 🏢 PC Windows (studio) | 🏠 Mac (casa) |
|---|---|---|
| Cartella | `SecondBrain-Studio` | `~/SecondBrain` |
| Profilo | `studio` | `personale` |
| Stanze | `clienti/`, `reference/`, `scadenzari/` | `immobili/`, `progetti/`, `scadenzari/` |
| Procedure | intervista, nuovo-cliente, brief-cliente, offerta, scadenzario, pulisci-dettato, chiudi-sessione | intervista, nuovo-immobile, scadenzario, pulisci-dettato, chiudi-sessione |
| Honcho | No, oppure con `saveMessages: false` | Sì, completo |

La **struttura** (mappe, procedure, modelli) arriva su entrambi da questo repository. I **dati** restano
su ciascun computer e non passano mai dall'uno all'altro: i clienti sul PC dello studio, le cose personali sul Mac.

Il modello è in `cervello/`: `comune/` (parti uguali per entrambi), `studio/` e `personale/`.

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
| `/nuovo-cliente` | Crea l'ala di un cliente dal modello (tipo, periodicità mensile/trimestrale, regime) |
| `/nuovo-immobile` | Crea la scheda di un immobile di famiglia |
| `/scadenzario` | Scadenze del periodo: clienti mensili, trimestrali, enti non commerciali, immobili |
| `/brief-cliente` | Legge Gmail e Drive (solo lettura) e scrive `brief.md` del cliente |
| `/offerta` | Prepara un'offerta seguendo il modello della biblioteca, anche in PDF |
| `/pulisci-dettato` | Trasforma un dettato vocale in una richiesta pulita |
| `/chiudi-sessione` | A fine lavoro aggiorna memoria, mappa, biblioteca e propone nuove skill |

La regola del video: **se fai una cosa due volte, diventa una skill.** `/chiudi-sessione` te lo propone da solo.

---

## Installazione sul PC Windows dello studio (app desktop di Claude)

L'app desktop ha la scheda **Code**: è Claude Code con interfaccia grafica, lavora su una cartella del
PC, legge la mappa e usa le procedure. Non serve il terminale.

1. Installa **Git for Windows** (https://git-scm.com/downloads/win, tutte le opzioni predefinite).
   Serve a Claude per eseguire comandi e per l'hook di apertura.
2. Riavvia l'app Claude, apri la scheda **Code** e scegli come cartella `Documenti`.
3. Scrivi a Claude:
   > Clona il repository https://github.com/FrancescoRegnani/FrancescoRegnani (branch `claude/happy-cannon-7ssarz`)
   > in questa cartella, poi esegui con bash: `bash FrancescoRegnani/second-brain/installa-cervello.sh --profilo studio`
4. Apri una **nuova sessione** nella scheda Code e scegli la cartella `SecondBrain-Studio`, nella tua
   cartella utente: `C:\Users\<tuo nome>\SecondBrain-Studio`.
5. Scrivi `/intervista`.

Ogni giorno apri la scheda Code **sulla cartella `SecondBrain-Studio`**.

## Installazione sul Mac di casa

```bash
cd ~/FrancescoRegnani
```
```bash
git pull
```
```bash
bash second-brain/installa-cervello.sh --aggiorna --profilo personale
```
Se `~/SecondBrain` esiste già, viene trasformato in cervello personale: le procedure dello studio
spariscono (solo se non le hai modificate) e arrivano quelle personali. Mappa, memoria e dati restano.
Se la mappa contiene la parte studio dell'intervista, chiedi a Claude:
> Questo è il cervello personale: riscrivi AGENTS.md partendo dal modello del profilo personale,
> tenendo solo le informazioni personali (immobili di famiglia, progetti). Togli quelle sullo studio.

Poi:
```bash
cd ~/SecondBrain
```
```bash
claude
```

## Aggiornare procedure e modelli (entrambi i computer)
Quando nel repository arrivano procedure nuove: `git pull` nella cartella `FrancescoRegnani`, poi
`bash second-brain/installa-cervello.sh --aggiorna`. Il profilo viene riconosciuto da solo.
Sul PC dello studio puoi chiederlo direttamente a Claude nella scheda Code.

## Ogni giorno
- Butta appunti e PDF in `inbox/` e chiedi "smista l'inbox".
- Per i modelli: metti un PDF buono in `inbox/` e chiedi di ricavarne la struttura in `reference/`.
- A fine lavoro: `/chiudi-sessione`.

### Usare lo stesso cervello con altri agenti
- **Codex**: aperto nella cartella del cervello legge `AGENTS.md` da solo.
- **ChatGPT Work / Antigravity**: apri la cartella del cervello come progetto o workspace.
  Le skill sono normali file di istruzioni in `.claude/skills/`, e la mappa dice dove trovarle.
- **Obsidian** (opzionale, per sfogliarlo): apri la cartella come vault. Sono tutti file Markdown.

---

## Privacy (importante per uno studio)
- I cervelli stanno **fuori** dal repository GitHub: i dati non vanno online. Nel repository c'è solo il modello vuoto.
- I dati dei clienti stanno **solo sul PC dello studio**, non sul Mac di casa.
- Il contenuto dei file che l'agente legge viene inviato al fornitore del modello (Anthropic, OpenAI…)
  durante la conversazione. Valuta cosa metterci in base agli obblighi di riservatezza e al GDPR.
- Honcho: sul PC dello studio non installarlo, oppure usalo con `saveMessages: false`. In questo modo legge
  le tue preferenze ma non carica le conversazioni sui clienti. Usare nomi in codice non basta: Claude
  legge e ripete i dati veri, e dal punto di vista GDPR i dati pseudonimizzati restano dati personali.
- Connettori Gmail/Drive: le skill li usano **solo in lettura**. L'agente deve chiedere conferma
  prima di inviare, cancellare o condividere.
- Backup: Time Machine sul Mac; sul PC dello studio, il backup dello studio (o OneDrive aziendale se previsto).
