# Odds Intelligence Live — istruzioni per Claude Code

## Scopo e utente

Progetto commissionato da un utente italiano (Karim) che vuole un servizio autonomo su VPS, capace di monitorare OGNI MINUTO gli incontri in diretta di tennis ATP/WTA/Challenger (maschile e femminile), calcio e basket, e inviare su Telegram solo segnalazioni di rimonte sufficientemente documentate. L'utente desidera massima precisione, nessuna notifica se manca evidenza, nessun duplicato. Rispondi in italiano.

## Requisiti concordati

1. Analizzare i match in cui il favorito o la squadra tecnicamente superiore è **attualmente in svantaggio**.
2. Per tennis e basket: probabilità di **rimontare e vincere**; per il calcio: **vincere** e **raggiungere almeno il pareggio** come due esiti distinti.
3. Un alert è ammissibile solo se la probabilità FINALE stimata è **strettamente >70%**, fondata su dati aggiornati e frequenze storiche pertinenti, con fiducia sufficiente. Non usare percentuali false o precisione ingiustificata.
4. Controllare pre-match e quote live, score e set/minuto/quarto, tecnica e forma, assenze/infortuni, riposo e affaticamento, statistiche live, esempi storici simili, timestamp e URL delle fonti.
5. Per il tennis, nella versione iniziale, restringere ai favoriti con **quota pre-match osservata <=1.20**.
6. Se un incontro già segnalato evolve, evitare duplicati; in futuro si potranno autorizzare update soltanto con variazioni sostanziali.
7. Non promettere copertura globale o latenza reale senza verifica del contratto dei feed. Non piazzare automaticamente scommesse.

## Stato effettivo del codice (v0.2)

**Testato offline (50 test, Python 3.12 e 3.13); NON distribuito su server, NON collegato a chiavi reali, build Docker non ancora provata.** `DRY_RUN=true` di default. Senza storico importato e validato non parte **nessun alert** (fail closed).

- `monitor/espn.py`: fonte GRATUITA predefinita (`SCORES_PROVIDER=espn`): scoreboard pubblici ESPN (non ufficiali) convertiti nel formato AllSports; accesso educato (fila, pause, cache, stop su 403/429), niente elusione. Verificato dal vivo il 17/11/2026: 47 quote pre e una partita WTA live letta. Niente quote live, niente quote tennis, niente Challenger.
- `monitor/betfair.py`: Betfair Exchange API ufficiale (chiave "delayed" gratuita): login interattivo, listMarketCatalogue/listMarketBook, probabilità dal punto medio back/lay con filtri di liquidità e forbice. Priorità sulle altre fonti quote. NON provato con un conto reale: dall'ambiente cloud di sviluppo api/identitysso .it e .com rispondevano 403 (probabile blocco geografico): il VPS deve stare in Europa/Italia. Comando `test-betfair`.
- `monitor/engine.py`: parsing livescore AllSports (set/game, minuto/intervallo, punteggio), mercati The Odds API, quote pre AllSports (`Odds`), esiti finali (`Fixtures`), de-vig, abbinamento nomi.
- `monitor/model.py`: modello empirico per stato di gioco + prob. pre-partita (finestra ±bandwidth), limite inferiore di Wilson, validazione fuori tempo (Brier, log loss, fasce, promozione).
- `monitor/history.py`: import di CSV locali (football-data / tennis-data). Nessun download automatico.
- `monitor/decision.py`: regole fail-closed (favorito pre-partita sotto, stato coperto, campione, media pesata storico/mercato live `MODEL_WEIGHT` con limite inferiore >70%, promozione, valore, contesto). La media col mercato non è validabile sullo storico: si misura con `report`.
- `monitor/app.py`: ciclo; calendario `/events` gratuito, quote live solo dove servono, archivio completo, risoluzione esiti, heartbeat.
- `monitor/storage.py`: SQLite (prematch first/last, odds_snapshots, score_snapshots, evaluations, results, history, validations, quota, kv).
- `monitor/__main__.py`: CLI `run | demo | import-history | import-live | validate | report | status`.

## LIMITI ESSENZIALI

- La probabilità è valida solo quanto lo storico importato: va scelto un dataset pertinente (livello, periodo) e rispettata la sua licenza (football-data: solo uso privato, no raccolta automatica).
- Colonne tennis-data.co.uk **non verificate** (sito 403 in sviluppo); stati AllSports "Half Time"/"Quarter N" e `event_winner="Second Player"` **non confermati** dalla documentazione: verificare con chiave reale.
- Basket: nessuno storico ⇒ mai alert finché `import-live` + `validate` non promuovono uno stato.
- Challenger/ITF: quote pre da AllSports; quote live non disponibili su The Odds API ⇒ con `REQUIRE_LIVE_MARKET=true` niente alert.
- Nessun feed automatico per infortuni/forma/riposo/statistiche live: solo `context.json` manuale e controllo di coerenza col mercato live.
- "Almeno pareggio": nessuna quota live double chance ⇒ con `REQUIRE_VALUE=true` mai alert su quell'esito.

## Come verificare

Nella root della cartella progetto:

```bash
python3 -m unittest discover -s tests -v
python3 -m monitor demo
python3 -m monitor status
```

Per distribuire su server Linux con Docker:

```bash
cp .env.example .env
cp context.example.json context.json
mkdir -p data history && sudo chown -R 10001:10001 data
# Impostare localmente chiavi valide in .env; NON committare né condividere!
docker compose up -d --build
docker compose logs -f --tail=80
```

Profilo gratuito: servono `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` e, per tennis e quote live, il conto Betfair (`BETFAIR_APP_KEY/USERNAME/PASSWORD`) (l'utente vuole solo fonti gratuite). `ALLSPORTS_API_KEY` e `ODDS_API_KEY` restano facoltative. Non chiedere all'utente di incollare segreti in chat; guidalo nell'inserimento sicuro sul server. Non passare da `DRY_RUN=true` a `false` senza dati validati e decisione esplicita dell'utente.

## Roadmap residua

1. Prova reale in DRY_RUN con chiavi: verificare schemi AllSports/The Odds API, stati partita, consumo crediti; build Docker sul VPS.
2. Importare storico calcio/tennis con licenza adeguata, `validate`, rivedere stati promossi.
3. Dopo settimane di raccolta: `report` e `import-live` (basket, Challenger).
4. Feed per statistiche live, infortuni, riposo; mapping ID fra provider; quote live per tennis minore.
5. Solo dopo decisione esplicita dell'utente: `DRY_RUN=false`.

## Stile di collaborazione

- In italiano, spiegazioni complete ma pratiche.
- Distingui chiaramente «già implementato e testato», «ipotesi», «da fare» e «attivato in produzione».
- Non inventare token, partite, probabilità, risultati, quote o fonti.
- Mantieni compatibilità Python 3.12 e Docker; non fare operazioni distruttive su server/db.
- Prima di modificare sistema o credenziali chiedi il contesto minimo necessario; mai pubblicare `.env`.
