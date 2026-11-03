# Odds Intelligence 0.1 — istruzioni per Claude

## Obiettivo
Sviluppare un monitor delle quote sportive ATP/WTA pre-match che individui anomalie e ne analizzi le possibili cause con fonti verificabili.

## Vincoli
- Non modificare, collegare o utilizzare il progetto Supabase ABILITA.
- Non dichiarare quote, volumi o notizie simulate come dati reali.
- Distinguere fatti confermati, ipotesi plausibili e cause non determinate.
- Non attribuire movimenti a 'sharp money' senza dati adeguati.
- Non inserire credenziali nei sorgenti o nei commit.
- Non eseguire modifiche sul server di produzione senza approvazione esplicita.

## Struttura esistente
- `app/main.py`: endpoint FastAPI
- `app/core.py`: logica e database
- `app/provider.py`: connettore quote
- `app/demo.py`: dataset dimostrativo
- `sql/postgres.sql`: schema SQL
- `deploy/`: servizi Linux
- `tests/`: test

## Priorità di sviluppo
1. Eseguire e verificare i test e documentare eventuali problemi.
2. Validare le configurazioni e la compatibilità del server di destinazione.
3. Integrare un provider reale con gestione rate limit, errori e timestamp.
4. Registrare quote e individuare anomalie con probabilità normalizzate e consenso bookmaker.
5. Aggiungere evidenze documentate per calendario, affaticamento e notizie.
6. Costruire dashboard responsive e notifiche Telegram.

## Definizione di completamento
Ogni modifica deve avere test pertinenti, istruzioni di esecuzione aggiornate e chiara distinzione tra funzionalità operative e ancora da implementare.
