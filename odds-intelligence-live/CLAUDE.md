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

## Stato effettivo del codice

**MVP scritto e testato localmente; NON distribuito su un server e NON collegato a chiavi API reali.** Parte in modalità `DRY_RUN=true`, non invia notifiche Telegram. Nessun processo in esecuzione in background al momento dell'esportazione.

- `monitor/feeds.py`: client REST con standard library per AllSports `Livescore`, The Odds API sports/odds `h2h`, Telegram `sendMessage`.
- `monitor/engine.py`: parsing di punteggi tennis/calcio/basket, associazione nomi, normalizzazione delle probabilità senza margine, mediana di più bookmaker, euristica conservativa per candidati, calcio 1X2/doppia chance stimata.
- `monitor/storage.py`: SQLite per snapshot delle prime quote pre-match osservate, record notifiche, budget giornaliero delle richieste quote.
- `monitor/config.py`: configurazione via variabili ambiente (`.env.example`).
- `monitor/__main__.py`: ciclo di verifica ogni `POLL_SECONDS` (min 60), interrogazioni concorrenti, avvisi, demo sintetica completamente offline.
- `tests/test_monitor.py`: 15 test automatici passati al momento della consegna.
- `Dockerfile` e `compose.yaml`: servizio container per VPS Linux, nessuna porta in ascolto, volume persistente per database.
- `README.md`: manuale italiano, formule, limiti, istruzioni e roadmap.

## LIMITI SCIENTIFICI ESSENZIALI — prima priorità

- La percentuale finale nel codice oggi è una **euristica**: probabilità implicita live senza margine meno penalità (3 punti base + spread/2 + 1.5 punti su infortuni ignoti + 1.5 punti su fatica ignota). NON esiste una calibrazione empirica; NON presentarla come probabilità statistica provata. Prima di attivare allerta reale >70% servono un dataset storico, analisi di campioni comparabili, backtest temporalmente corretto e calibrazione fuori campione per sport/situazione.
- Non è ancora integrato un provider affidabile automatico per infortuni, forma recente, calendario, minuti giocati, xG/possessi/break point. `context.json` può aggiungere informazioni manuali recenti con URL HTTPS, ma NON sostituisce la verifica della fonte.
- The Odds API può non coprire Challenger/ITF o tornei minori. I dati del solo AllSports non permettono di stimare probabilità con tre bookmaker senza un feed odds alternativo.
- Per il calcio `almeno pareggio` è una probabilità calcolata come `P(vittoria)+P(pareggio)` dal mercato 1X2: **non** è una quota double chance realmente offerta; il codice indica `n/d` per questa quota.
- Le quote pre-match salvate non sono necessariamente *opening odds*; sono le PRIME osservate dal processo prima dell'avvio del match. Se il servizio parte durante il match non esiste dato pre in DB: niente segnalazione.
- Nome squadre/giocatori fra provider e score feed può non corrispondere; in caso di ambiguità il codice blocca il segnale. Serve riconciliazione ID robusta per coperture grandi.
- La verifica al minuto è una schedulazione dei cicli, non garanzia di quote aggiornate al secondo: dipende dai feed e dal rate limit. Il budget quote predefinito è 4000 richieste/giorno; con molti campionati può esaurirsi presto.

## Come verificare

Nella root della cartella progetto:

```bash
python3 -m unittest discover -s tests -v
python3 -m monitor demo
```

Per distribuire su server Linux con Docker:

```bash
cp .env.example .env
cp context.example.json context.json
mkdir -p data
# Impostare localmente chiavi valide in .env; NON committare né condividere!
docker compose up -d --build
docker compose logs -f --tail=80
```

Le chiavi richieste sono `ALLSPORTS_API_KEY`, `ODDS_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Non chiedere all'utente di incollare segreti in chat; guidalo nell'inserimento sicuro sul server. Non passare da `DRY_RUN=true` a `false` senza dati validati e decisione esplicita dell'utente.

## Roadmap consigliata a Claude

1. **Audit tecnico** del progetto, verificare schemi reali dei feed e copertura concreta ATP/WTA/Challenger, calcio e basket sui piani API disponibili; correggere eventuali regressioni. Fai i test prima e dopo ogni intervento.
2. Aggiungere uno **storico etichettato**: evento+provider ID canonico, prequote e time-series quote live, momento della prima perdita di set/svantaggio, score/statistiche, riposo, outcome finale; rispetto dei termini delle API.
3. Costruire un modello calibrato per sport con probabilità baseline del mercato, tempo rimasto, magnitudine svantaggio, difficoltà avversario e forma, più le altre variabili disponibili. Test out-of-time, calibration curves, Brier/log loss e intervalli di confidenza per fascia >70%. Impostare *fail closed* senza campione ed evidence sufficiente.
4. Espandere il modulo **fonti**: quote live affidabili su tennis minore, goal/rosso/xG per calcio, vantaggio e tempo residuo per basket, dettagli servizio/break per tennis, absences ufficiali, riposo e calendario.
5. Inviare alert solo con probabilità convalidata e spiegazione osservato/derivato, timestamp in Europe/Rome, fonte diretta per partita se disponibile. Un test su dati storici deve coprire falsi match e ritardi quote.
6. Valutare gestione provider cost, osservabilità, retry/backoff, rotazione chiavi sport, rate limit, healthcheck e provisioning sul VPS scelto dall'utente.

## Stile di collaborazione

- In italiano, spiegazioni complete ma pratiche.
- Distingui chiaramente «già implementato e testato», «ipotesi», «da fare» e «attivato in produzione».
- Non inventare token, partite, probabilità, risultati, quote o fonti.
- Mantieni compatibilità Python 3.12 e Docker; non fare operazioni distruttive su server/db.
- Prima di modificare sistema o credenziali chiedi il contesto minimo necessario; mai pubblicare `.env`.
