# Odds Intelligence Live — monitor di rimonte con modello calibrato

Servizio Python 3.12 / Docker che ogni 60 secondi osserva tennis (ATP/WTA/Challenger/ITF), calcio e basket e
**propone** un avviso Telegram quando un favorito pre-partita è in svantaggio e la probabilità di rimonta,
**misurata su uno storico e validata fuori campione**, ha un limite inferiore di confidenza strettamente
superiore al 70%.

> **Stato (v0.2):** codice e 46 test offline funzionanti. **Non è installato su alcun server e non è
> collegato a chiavi reali.** Senza uno storico importato e validato, il servizio **non emette alcun alert**
> (fail closed): raccoglie e archivia dati. `DRY_RUN=true` di default.

## Cosa è cambiato rispetto alla v0.1

| Problema v0.1 | Soluzione v0.2 |
|---|---|
| La "probabilità" era la quota live meno una penalità fissa: ogni alert, per costruzione, indicava una scommessa a valore atteso negativo | Probabilità finale = media pesata fra frequenza storica di rimonta (per stato di gioco e forza pre-partita, con limite inferiore di Wilson) e mercato live. Con `REQUIRE_VALUE=true` l'alert parte solo se la quota live offerta supera la quota equa del modello (+`MIN_EDGE`) |
| Nessuna calibrazione | Comando `validate`: addestramento prima di una data, verifica dopo; Brier, log loss, fasce di calibrazione. Uno stato/esito genera alert **solo se promosso** |
| In DRY_RUN non si archiviava nulla | Ogni valutazione (alert, shadow, blocked + motivo), snapshot di punteggio, quote pre e live ed esito finale vanno in SQLite. `report` misura la calibrazione reale, `import-live` riusa questi dati come storico |
| `.env` copiato nell'immagine Docker | `.dockerignore`, Dockerfile che copia solo `monitor/`, utente non-root, healthcheck |
| Budget esaurito in ~5 ore | Calendario eventi gratuito (`/events`); quote live solo per eventi in corso dove il favorito è sotto e lo stato è modellabile; quote pre al massimo una volta l'ora per campionato |
| Challenger non coperti da The Odds API | Quote pre-partita AllSports (metodo `Odds`) indicizzate per `event_key`, anche Challenger/ITF. Alert Challenger solo con storico Challenger dedicato (`TENNIS_MODEL_TIERS`) |
| Codice morto (`stale`), tornei tennis scelti in ordine alfabetico, retry assenti | Rimossi o corretti; retry con backoff su errori di rete e 429/5xx (mai su Telegram, per non duplicare) |

## Profilo gratuito (predefinito)

Senza alcun abbonamento il servizio usa gli **scoreboard pubblici di ESPN** (`SCORES_PROVIDER=espn`):
punteggi live, quote pre-partita di un bookmaker (DraftKings, calcio e basket) e risultati finali.

- **Accesso educato, nessuna elusione.** Richieste in fila con pause casuali e User-Agent onesto. Ogni
  campionato è letto al massimo una volta al minuto, e solo ogni 15 minuti se non ha partite in corso o
  imminenti. Su 403/429 la fonte si ferma per 30 minuti. Niente rotazione di IP né finti browser. SofaScore è
  escluso perché blocca i programmi automatici.
- **Gli endpoint ESPN non sono ufficiali**: possono cambiare senza preavviso. Se smettono di funzionare, il
  log lo segnala e non partono alert.
- **Cosa manca nel gratuito:**
  - quote live, quindi `REQUIRE_LIVE_MARKET=false` e la probabilità finale è solo quella storica;
  - quote tennis, quindi il criterio "quota pre ≤ 1,20" non è verificabile e **il tennis non genera alert**
    senza una fonte quote;
  - i Challenger/ITF.

  Calcio (all'intervallo, con storico importato) funziona. Il basket resta senza storico.
- Per riattivare le fonti a pagamento: `SCORES_PROVIDER=allsports` con `ALLSPORTS_API_KEY`, e/o
  `ODDS_API_KEY` con `REQUIRE_LIVE_MARKET=true`.

## Come decide (tutte le condizioni devono essere vere)

1. Chi è sotto era il favorito: prob. pre-partita senza margine ≥ `MIN_PREMATCH_PROBABILITY`. Per il tennis
   anche quota pre ≤ `MAX_TENNIS_PREMATCH_ODDS` (1,20). La quota pre usata è l'**ultima osservata prima dell'inizio**.
   Si conservano anche la prima osservata e l'origine.
2. Lo **stato di gioco è coperto dallo storico**:
   - tennis: favorito sotto nei set (0-1; nei 5 set anche 0-2 e 1-2), all'inizio del set successivo
     (≤ `TENNIS_MAX_GAMES_INTO_SET` game giocati, al massimo 1 game di svantaggio). Il formato a 3 o 5 set è
     dedotto da categoria e torneo; se è incerto, niente alert;
   - calcio: **all'intervallo** (o fino a `FOOTBALL_HT_TOLERANCE_MIN` minuti dopo il 45'), con stati -1 e -2+.
     Esiti distinti: **vittoria** e **almeno pareggio**;
   - basket: **nessuno storico calibrato disponibile ⇒ mai alert**. Le situazioni vengono archiviate per
     costruirlo.
3. Modello empirico: esempi storici dello stesso stato con prob. pre entro ±`MODEL_BANDWIDTH`. Servono almeno
   `MODEL_MIN_SAMPLE` esempi.
4. **Probabilità finale = media pesata** fra storico e mercato live senza margine:
   `MODEL_WEIGHT × storico + (1 − MODEL_WEIGHT) × mercato` (default 0,5, cioè media semplice). Lo storico
   misura come sono finite situazioni simili; il mercato vede le notizie di giornata (infortuni, condizioni,
   andamento del set). L'alert richiede che la stessa media, calcolata con il **limite inferiore** di Wilson
   dello storico (z=`MODEL_Z`), sia **> 70%**. Senza mercato live (e `REQUIRE_LIVE_MARKET=false`) conta solo
   lo storico.
5. Lo stato/esito deve essere **promosso dalla validazione fuori tempo** dello storico: almeno
   `VALIDATION_MIN_ALERTS` alert simulati nel test, frequenza osservata > soglia, scarto predetto/osservato
   ≤ `VALIDATION_MAX_GAP`. Ogni nuovo import di storico azzera le promozioni.

   La media con il mercato **non è validabile sullo storico** (i CSV non hanno quote live). La sua
   calibrazione si misura con `report` sui dati raccolti dal servizio, nella colonna "finale media".
6. Mercato live (The Odds API, ≥3 bookmaker freschi, divergenza ≤10%):
   - obbligatorio se `REQUIRE_LIVE_MARKET=true`;
   - con `REQUIRE_VALUE=true` la quota offerta deve essere ≥ (1+`MIN_EDGE`)/probabilità finale;
   - blocco facoltativo `MAX_MODEL_MARKET_GAP` (spento di default) se il mercato è molto sotto lo storico.

   Per "almeno pareggio" non esiste una quota live double chance nei feed: con `REQUIRE_VALUE=true` non parte
   alcun alert su quell'esito.
7. `context.json`: un infortunio confermato o un'alta fatica bloccano l'alert. Senza riscontro il messaggio
   dice "non verificati". Con `REQUIRE_VERIFIED_CONTEXT=true` il riscontro diventa obbligatorio.
8. Una sola segnalazione per partita.

## Dati storici: da dove e come

Nessun download automatico. Scarica tu i file e rispetta i termini delle fonti. football-data.co.uk, per
esempio, dichiara i dati gratuiti "per uso privato, non per prodotti commerciali né per raccolta automatica":
se il servizio è per un cliente, verifica la licenza o acquista dati con licenza adeguata.

- **Calcio** (CSV stile football-data.co.uk): `Date, HomeTeam, AwayTeam, FTHG, FTAG, HTHG, HTAG` e una terna
  di quote 1X2 (`AvgH/D/A`, `BbAvH/D/A`, `PSH/D/A`, `B365H/D/A`, oppure le versioni di chiusura). Il
  risultato usato è quello dei 90'.
- **Tennis** (CSV stile tennis-data.co.uk; colonne **da verificare sul file reale**, sito non consultabile
  durante lo sviluppo): `Date, "Best of", W1..W5, L1..L5, Comment` e una coppia di quote (`AvgW/AvgL`,
  `PSW/PSL`, `B365W/B365L`). Sono usate solo le partite `Completed`. Se il file è .xlsx, salvalo in CSV.
- **Dati raccolti dal servizio**: `import-live` trasforma le valutazioni archiviate con esito noto in storico.
  È l'unica strada per basket e Challenger, se non hai uno storico dedicato.

```bash
mkdir -p history   # copia qui i CSV
docker compose run --rm monitor python -m monitor import-history --sport football /history/E0_2324.csv /history/I1_2324.csv
docker compose run --rm monitor python -m monitor import-history --sport tennis --tier atp /history/atp_2023.csv
docker compose run --rm monitor python -m monitor validate --cutoff 2024-07-01
docker compose run --rm monitor python -m monitor status
```

Scegli `--cutoff` in modo da lasciare nel test almeno una stagione intera. Se nessuno stato viene promosso, il
servizio continua a raccogliere dati senza inviare nulla: è il comportamento voluto.

## Installazione Docker (Linux/VPS)

```bash
cp .env.example .env            # inserisci le chiavi SOLO sul server
cp context.example.json context.json
mkdir -p data history
sudo chown -R 10001:10001 data  # il container gira come utente non-root 10001
docker compose up -d --build
docker compose logs -f --tail=80
docker compose ps               # colonna STATUS: healthy/unhealthy (heartbeat ogni ciclo)
```

Chiavi: nel profilo gratuito servono solo `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. `ALLSPORTS_API_KEY`
(con `SCORES_PROVIDER=allsports`) e `ODDS_API_KEY` (quote live) sono facoltative, a pagamento. Servono anche `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`
(creato con [@BotFather](https://t.me/BotFather)). Non condividere `.env` e non committarlo.

Passa a `DRY_RUN=false` solo dopo `validate` con stati promossi e una revisione di `report` sui dati live, poi
`docker compose up -d --force-recreate`.

## Comandi

| Comando | Cosa fa |
|---|---|
| `python -m monitor run` | servizio (default) |
| `python -m monitor demo` | pipeline completa su dati **sintetici**, nessuna rete |
| `python -m monitor import-history --sport football\|tennis [--tier atp\|wta\|challenger\|itf] FILE...` | importa storico |
| `python -m monitor import-live` | usa le valutazioni live con esito come storico |
| `python -m monitor validate --cutoff AAAA-MM-GG` | validazione fuori tempo e promozione |
| `python -m monitor report` | calibrazione osservata di alert/shadow archiviati |
| `python -m monitor status` | crediti, storico per stato, stati promossi |
| `python -m monitor test-telegram` | invia un messaggio di prova al bot |

Test: `python3 -m unittest discover -s tests -v`

## Costi e copertura (da documentazione ufficiale, verificare sul proprio piano)

- The Odds API: `/sports` ed `/events` non consumano crediti. `/odds` costa mercati × regioni (qui 1). Le
  intestazioni `x-requests-remaining` vengono registrate (`status`). Il tennis è coperto solo per i tornei
  ATP/WTA principali, **non i Challenger/ITF**.
- AllSports: `Livescore`, `Odds` (pre-partita, con from/to), `Fixtures` (esiti). Il tennis include
  Challenger e ITF. Alcuni valori di stato (es. "Half Time", "Quarter 3") **non sono confermati dalla
  documentazione**: il codice li gestisce in modo prudente, ma vanno verificati sui dati reali.
- `MAX_ODDS_REQUESTS_PER_DAY` (default 500) è un tetto rigido. Le chiamate live hanno priorità su quelle
  pre-partita.

## Limiti che restano

- Lo storico misura lo stato "inizio set" o "intervallo": non usa statistiche live (break, xG, rossi, falli),
  forma, calendario o riposo. Il controllo di coerenza col mercato live serve proprio a intercettare
  informazioni che il modello non vede.
- Infortuni e fatica non hanno ancora un feed automatico: c'è solo `context.json` manuale.
- La quota live per "almeno pareggio" non è disponibile.
- L'abbinamento fra feed è per nome (fail closed se ambiguo). Un mapping per ID non è ancora disponibile.
- Il basket non ha storico: niente alert finché `import-live` + `validate` non promuovono qualche stato.

Il programma non piazza scommesse, non garantisce vincite e non è consulenza di gioco.
