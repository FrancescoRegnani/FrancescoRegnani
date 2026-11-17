# Odds Intelligence Live — monitor di rimonte ogni 60 secondi

Servizio Python 3.12 / Docker per osservare il tennis maschile e femminile, il calcio e il basket da feed esterni e **proporre** un avviso Telegram solo quando una stima prudenziale supera strettamente il **70%**. Gira in modo autonomo su un server già acceso; non richiede che ChatGPT rimanga aperto.

> **Stato:** prototipo tecnico con test offline. **Non è ancora in funzione sul tuo server.** Le percentuali sono basate sul consenso delle quote live senza margine e su una regola euristica di penalizzazione, **non su un modello storicamente calibrato**. Pertanto **non è corretto trattare un 73% mostrato dal programma come il 73% verificato di successi futuri**. È necessario un periodo di raccolta dati, il backtest e una calibrazione prima dell'uso operativo come modello statistico di betting.

## Fonti e copertura

- [AllSports API](https://allsportsapi.com/) fornisce punteggi e progressi delle partite: tennis, calcio, basket.
- [The Odds API](https://the-odds-api.com/) fornisce mercati `h2h` da diversi bookmaker, quando disponibili. Il progetto acquisisce **almeno tre quote fresche**, elimina matematicamente il margine, usa la mediana e respinge mercati discordanti.
- [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage) invia il messaggio, se `DRY_RUN=false`.
- Informazioni su infortuni e riposo sono **sconosciute**, salvo inserimento manuale di riscontri recenti in `context.json`. Senza riscontro, il punteggio statistico riceve una penalizzazione. Se esiste un infortunio accertato o alta fatica, l'avviso è soppresso.

**Non è un feed universale:** l'esistenza di un punteggio live non garantisce le quote compatibili. I Challenger e i tornei minori, il basket meno seguito o una partita di calcio periferica potrebbero non essere coperti da The Odds API. Il servizio non inventa le quote mancanti. Le verifiche sui precedenti, xG, statistiche live dettagliate, infortuni e riposo automatico **non sono ancora integrate**: la prima versione non soddisfa integralmente il requisito di valutazione multifattoriale. Nessuna notifica viene emessa dove mancano mercato coerente e quote pregara già osservate.

## Logica di selezione

1. Ogni 60 secondi richiede i live score per i tre sport.
2. Chiama solo le competizioni offerte dal provider di quote; tenta l'identificazione dei nomi fra feed. Ambiguità o discordanza = esclusione.
3. Salva le quote **prima dell'inizio** nel database locale. Se il servizio viene avviato a partita già iniziata e non dispone di questo dato, non può segnalare quel match.
4. Cerca una squadra/tennista in svantaggio e inizialmente chiaramente favorito (minimo 62% di quota implied senza margine; parametrizzabile). **Per il tennis impone anche la quota pre-match registrata <=1,20** (`MAX_TENNIS_PREMATCH_ODDS`); se il prezzo pre-gara non è stato registrato, esclude. Attenzione: è la prima quota *osservata dal servizio* prima della partita, non necessariamente la vera quota d'apertura storica.
5. Calcola `P_mercato = mediana(1/quota_esito / somma(1/quote_tutti_esiti))`, cioè probabilità implicita de-vig per ciascun bookmaker. **Non equivale a una frequenza storica misurata.**
6. Penalizzazione prudenziale: 3 punti percentuali + metà divergenza fra bookmaker + 1,5 punti se infortuni non verificati + 1,5 se affaticamento non verificato. Se il valore finale non supera **strettamente** 70%, esclude.
7. Tennis e basket: esito *vittoria finale*. Calcio: *vittoria finale* e, separatamente, *almeno pareggio* (somma matematica degli esiti 1 e X o 2 e X del mercato 1X2). Per l'almeno pareggio non inventa una quota double chance offerta dal bookmaker; mostra `n/d`.
8. Invia al massimo **una segnalazione per partita**; tutte le segnalazioni sono conservate in SQLite.

Il sistema **non garantisce vantaggio sul bookmaker**: per provarlo occorre confrontare una probabilità **calibrata** con la quota realmente offerta sull'esito preciso e tenere conto dei margini e della varianza.

## Installazione Docker (Linux/VPS)

Requisiti: Docker con `docker compose`, una rete HTTPS in uscita, abbonamenti API validi per gli sport interessati, bot Telegram e ID chat. Server con sistema aggiornato e Docker; **non pubblicare alcuna porta in ingresso**.

```bash
unzip odds-intelligence-live.zip
cd odds-intelligence-live
cp .env.example .env
cp context.example.json context.json
mkdir -p data
```

Apri `.env` in un editor e inserisci:

- `ALLSPORTS_API_KEY` → chiave da AllSports API.
- `ODDS_API_KEY` → chiave da The Odds API, con sufficiente credito e supporto degli sport in-play.
- `TELEGRAM_BOT_TOKEN` → creato con il bot ufficiale [@BotFather](https://t.me/BotFather).
- `TELEGRAM_CHAT_ID` → identificativo chat a cui il bot può scrivere (dopo averlo avviato).

**Proteggi `.env`**, non copiarlo in chat e non inviare screenshot con token. Tienilo fuori da backup o repo pubblici. Non impostare ancora `DRY_RUN=false`.

```bash
docker compose up -d --build
docker compose logs -f --tail=80
```

Il log di ogni minuto mostra quante partite in svantaggio e quote valide sono state esaminate, oltre agli eventuali candidati. **In simulazione nessun messaggio viene spedito**, anche se Telegram è configurato.

Solo dopo verifica di dati, modello e soglie, modifica `.env` in `DRY_RUN=false`, poi:

```bash
docker compose up -d --force-recreate
```

Per fermare il monitor: `docker compose stop`. Lo storico delle quote pregara e degli avvisi resta nella cartella `data`.

## Test senza API

Su un PC con Python 3.12 (o altra versione recente che supporti `zoneinfo`):

```bash
python3 -m unittest discover -s tests -v
python3 -m monitor demo
```

La demo usa dati **inventati, riconoscibili** e non contatta alcun bookmaker.

## Copertura e costi

- `WATCH_SPORT_KEYS` = chiavi delle leghe che desideri monitorare. La lista offerta in quel momento si consulta da The Odds API; chiavi inesistenti vengono ignorate. I tennis event `tennis_*` vengono scoperti automaticamente fino a `MAX_AUTO_TENNIS_KEYS`.
- Con **12 sport keys e 60 secondi di intervallo**, il consumo teorico è **17.280 chiamate quote in 24 ore** (prima dei moltiplicatori del piano/provider). Il default `MAX_ODDS_REQUESTS_PER_DAY=4000` limita il consumo, ma il monitor **smetterà di consultare quote** quando avrà raggiunto quel tetto giornaliero. Puoi restringere le leghe o aumentare il budget consapevolmente.
- `POLL_SECONDS=60` non è la latenza garantita del mercato: ogni provider ha ritardi e cicli di aggiornamento propri, e ogni richiesta impiega tempo.
- `MAX_ODDS_AGE_SECONDS=180`: quote più vecchie di 3 minuti sono scartate; non si tratta di conferma tick-by-tick.
- `MIN_BOOKMAKERS=3` e `MAX_BOOKMAKER_SPREAD=0.10` respingono dati troppo scarsi o discordanti.
- `MAX_TENNIS_PREMATCH_ODDS=1.20` mantiene il criterio originario dei grandi favoriti per ATP/WTA/Challenger; si applica al **prezzo pre-gara archiviato** dal servizio.
- `ALERT_THRESHOLD=0.70` è una soglia **stretta**: una stima uguale al 70,00% non viene segnalata.
- In caso di feed inatteso, perdita di connessione o quota insufficiente, il monitor salta quella verifica. Nessuna stima viene inventata.

## Riscontri manuali su forma/infortuni/affaticamento

Facoltativamente, nel `context.json` si possono registrare informazioni controllate entro 24 ore per una singola partita (`event_key` del feed punteggi):

```json
{
  "tennis:1234567": {
    "verified_at": "2026-11-17T14:00:00+01:00",
    "injury": "clear",
    "fatigue": "low",
    "sources": ["https://example.org/fonte-ufficiale-reale"]
  }
}
```

È solo un **esempio di formato**: sostituisci identificativo, data e URL con verifiche reali. Valori ammessi: `injury: clear/confirmed`, `fatigue: low/high`; senza fonti HTTPS e orario recente la dichiarazione viene ignorata. `context.json` non rende automaticamente comprovata una notizia: chi la inserisce deve verificare davvero la fonte.

## Prima del rilascio definitivo

- Raccogliere un archivio di quote pre-match, snapshot live ed esiti finali, con identificativi certi, per almeno diversi mesi e una numerosità sufficiente per sport e condizioni di svantaggio.
- Calibrare probabilità con intervalli d'incertezza e test fuori campione, **soprattutto nella fascia 70–90%**; misurare errore Brier, log loss e calibrazione, scartando le categorie non robuste.
- Integrare statistiche live dello sport (tennis: break e turni servizio; calcio: minuto, xG, rossi, possesso; basket: possessi, tempo e fallo), più dati affidabili su assenze, forma, calendario e affaticamento.
- Implementare validazione più profonda degli identificativi e aggiornamenti per eventi sostanziali, eventuale fallback sui bookmaker in-play dove permesso.
- Valutare la copertura reale dei Challenger/ITF/WTA e il costo delle API sul contratto scelto.

## Privacy, dati e responsabilità

Il programma non piazza scommesse e non si collega a conti di gioco. Non è una promessa di vincita né una consulenza per puntate. È uno strumento di raccolta e scrematura dati da convalidare. Le chiavi sono usate solo per richieste HTTPS ai provider configurati; non vengono stampate nei log. Il database SQLite contiene snapshot di probabilità e identificativi partita, non token Telegram.

