# Jarvis – assistente personale con Siri

Jarvis è un piccolo server su Supabase che risponde alle tue domande con Claude.
Lo chiami con **"Ehi Siri, Jarvis"** da Apple Watch, iPhone o AirPods: detti la domanda, Jarvis risponde a voce.

Cosa sa fare in questa prima versione:
- rispondere a domande di ogni tipo, in modo breve e adatto alla voce;
- **ricordare** cose su di te ("ricorda che lo studio chiude alle 18") e **dimenticarle** se glielo chiedi;
- cercare sul **web** le informazioni aggiornate (notizie, meteo, orari);
- tenere il filo della conversazione per circa 20 minuti, così puoi fare domande di seguito.

## Come è fatto

```
Apple Watch / iPhone  ──Siri──▶  Comando Rapido "Jarvis"
                                      │  POST + token segreto
                                      ▼
                       Supabase Edge Function "jarvis"
                         │                       │
                         ▼                       ▼
                 Claude (API Anthropic)   Database: ricordi e cronologia
```

| File | Contenuto |
|---|---|
| `supabase/migrations/001_jarvis.sql` | Tabelle `jarvis_memories` (ricordi) e `jarvis_messages` (cronologia breve) |
| `supabase/functions/jarvis/index.ts` | Il server: autenticazione, memoria, chiamata a Claude, ricerca web |

## 1. Prepara il server (una volta sola)

1. **Chiave Claude**: su [console.anthropic.com](https://console.anthropic.com) crea una chiave API (*API Keys → Create Key*) e imposta un limite di spesa mensile (*Billing → Limits*).
2. **Token di Jarvis**: crea una password lunga e casuale (per esempio con l'app Password dell'iPhone). Servirà solo al tuo Comando Rapido per farsi riconoscere.
3. **Database**: esegui `supabase/migrations/001_jarvis.sql` nel progetto Supabase (*SQL Editor*).
4. **Funzione**: pubblica `supabase/functions/jarvis/index.ts` con il nome `jarvis` e **verifica JWT disattivata** (l'autenticazione la fa il token di Jarvis).
5. **Segreti**: in Supabase → *Edge Functions → Secrets* aggiungi:
   - `ANTHROPIC_API_KEY` = la chiave del punto 1
   - `JARVIS_TOKEN` = il token del punto 2

   Opzionali: `JARVIS_MODEL` (predefinito `claude-haiku-5-5`, veloce ed economico; `claude-opus-5-5` per risposte più ragionate), `JARVIS_EFFORT` (`low` predefinito, per risposte rapide; `medium` o `high` per risposte più ragionate ma più lente).

L'indirizzo del server sarà: `https://<ID-PROGETTO>.supabase.co/functions/v1/jarvis`

## 2. Crea il Comando Rapido sull'iPhone

Apri l'app **Comandi** → **+** (nuovo comando) e aggiungi queste azioni, in ordine:

1. **Detta testo**
   - Lingua: *Italiano*
   - Interrompi ascolto: *Dopo una pausa*
2. **Ottieni contenuto dell'URL**
   - URL: `https://<ID-PROGETTO>.supabase.co/functions/v1/jarvis`
   - Tocca *Mostra di più*:
     - Metodo: **POST**
     - Intestazioni: aggiungi `x-jarvis-token` = *il tuo token*
     - Corpo richiesta: **JSON** → aggiungi un campo *Testo* con chiave `testo` e come valore la variabile **Testo dettato**
3. **Pronuncia testo** → con la variabile **Contenuti dell'URL**

Poi:
- rinomina il comando in **Jarvis** (il nome è la frase da dire a Siri);
- nei dettagli del comando (icona ⓘ) attiva **Mostra su Apple Watch**.

## 3. Usalo

- Dal Watch: alza il polso, *"Ehi Siri, Jarvis"*, poi fai la domanda.
- Esempi:
  - "Ricorda che il commercialista di riferimento per le paghe è Marco."
  - "Che tempo farà domani a Milano?"
  - "Cosa ti ricordi di me?"
  - "Dimentica l'ultima cosa che ti ho detto."

Se dopo la prova ricevi:
- *"Non autorizzato"* → il token nel Comando Rapido non coincide con `JARVIS_TOKEN`;
- *"La chiave di Claude non è valida"* → controlla `ANTHROPIC_API_KEY`.

## Dove è pubblicato ora

Per non pagare un secondo progetto, Jarvis è pubblicato nel progetto Supabase **ABILITA**:
- indirizzo: `https://ourlmliotsgzrytrsofa.supabase.co/functions/v1/jarvis`
- tabelle: `jarvis_memories`, `jarvis_messages` (separate da quelle dell'app)

**Per toglierlo da ABILITA** (per esempio per spostarlo in un progetto dedicato):
1. Supabase → *Edge Functions* → `jarvis` → *Delete*.
2. *SQL Editor*: `drop table public.jarvis_messages, public.jarvis_memories;`
3. Rimuovi i segreti `ANTHROPIC_API_KEY` e `JARVIS_TOKEN`, a meno che non li usi anche altro.

Per spostarlo, prima esporta i ricordi (`select * from public.jarvis_memories`), poi ripeti i passi del punto 1 nel nuovo progetto.

## Privacy e sicurezza

- Le tabelle hanno RLS attiva e nessuna policy: solo la funzione (con la chiave di servizio) le legge e scrive.
- Jarvis non salva password, codici o dati bancari e sanitari come ricordi.
- Le domande vengono inviate all'API di Claude; secondo i termini commerciali di Anthropic non vengono usate per addestrare i modelli. Evita comunque di dettare dati personali sensibili dei clienti finché non hai valutato l'aspetto GDPR.
- Per cancellare tutto: svuota le tabelle `jarvis_memories` e `jarvis_messages`.

## Prossimi passi

- Collegare Gmail e Google Calendar ("cosa ho domani?", "ci sono email urgenti?").
- Riepilogo del mattino con notifica.
- App per iPhone con notifiche con pulsanti, visibili anche sul Watch.
