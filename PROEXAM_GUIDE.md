# ProExam — Guida Completa per Principianti

Questa è la guida da seguire da zero, assumendo di non sapere programmare. Per la prima versione si evita di costruire contemporaneamente Commercialista, Avvocato e tutti gli altri percorsi: si costruisce il motore universale usando Commercialista come primo corso, poi si duplica la struttura per gli altri esami.

## Obiettivo finale

Creare un'app iOS/Android in stile Duolingo per preparare agli esami professionali italiani:

- Commercialista
- Avvocato
- Consulente finanziario OCF
- Consulente del lavoro
- Revisore legale
- IVASS
- OAM
- Agente immobiliare
- altri percorsi futuri

L'utente sceglie:

1. quale esame deve sostenere;
2. quando sosterrà l'esame;
3. quanto tempo vuole studiare ogni giorno.

L'app costruisce automaticamente il percorso e propone ogni giorno cosa studiare.

## Architettura che utilizzeremo

### App — FlutterFlow

Serve per creare graficamente:

- schermate;
- pulsanti;
- quiz;
- animazioni;
- login;
- navigazione;
- progressi;
- profilo;
- abbonamenti.

Non è necessario conoscere Flutter all'inizio.

### Database — Supabase

Conterrà:

- utenti;
- esami;
- materie;
- lezioni;
- quiz;
- risposte;
- errori;
- progressi;
- mastery;
- simulazioni;
- streak;
- XP.

FlutterFlow dispone di integrazione ufficiale con Supabase.

### Autenticazione — Supabase Auth

Per:

- registrazione;
- login;
- recupero password;
- account utente.

Supabase supporta email/password e diversi provider social; FlutterFlow supporta direttamente Supabase Authentication.

### AI

Un servizio AI richiamato dal backend.

Servirà per:

- spiegazioni;
- correzione risposte;
- tutor;
- simulazioni orali;
- generazione controllata di esercizi;
- analisi delle lacune.

Non metteremo direttamente nell'app una chiave API privata.

### Abbonamenti — RevenueCat

Gestirà:

- Pro mensile;
- Pro annuale;
- eventuali prove gratuite;
- acquisti Apple;
- acquisti Google.

FlutterFlow dispone di integrazione RevenueCat.

### Notifiche — Firebase Cloud Messaging

Per esempio: "Ti aspettano 12 minuti di preparazione."

FlutterFlow usa FCM per le notifiche push.

## Fase 0 — Non costruire subito tutto

Errore da evitare: costruire immediatamente 8 esami, AI, classifiche, abbonamenti, voce, notifiche, simulazioni ecc.

Costruiamo prima un MVP (Minimum Viable Product).

La prima versione deve permettere semplicemente:

```
Registrazione
↓
Scelta esame
↓
Scelta data
↓
Scelta tempo giornaliero
↓
Percorso
↓
Lezione
↓
Quiz
↓
Risultato
↓
XP
↓
Progressione
```

Quando questo funziona bene, aggiungiamo il resto.

## Fase 1 — Crea gli account

Crea account su:

1. **FlutterFlow** — crea un nuovo account.
2. **Supabase** — crea un account.
3. **Firebase** — crea un account/progetto Google Firebase.

Non serve ancora: RevenueCat, Apple Developer, Google Play Console. Li creeremo più avanti.

## Fase 2 — Crea il progetto FlutterFlow

Dentro FlutterFlow: **Create New**

- Nome: `ProExam`
- Tipo: `Blank App`

Non utilizzare subito template complessi.

## Fase 3 — Definisci il design

Prima di creare pagine impostiamo uno stile globale.

**Identità consigliata**: ProExam deve sembrare moderno, semplice, affidabile, giovane, professionale. Non deve sembrare un'app universitaria tradizionale. Non deve nemmeno essere infantile.

### Colori dei percorsi

| Esame | Colori |
|---|---|
| Commercialista | verde/blu |
| Avvocato | rosso/bordeaux |
| Finanza | blu/oro |
| Consulente del lavoro | viola |
| IVASS | azzurro |

La struttura dell'app rimane identica. Cambiano alcuni colori e icone.

## Fase 4 — Crea le prime pagine

Per la V1 creiamo solamente:

1. **Splash** — Logo ProExam.
2. **Welcome** — Titolo: "Preparati. Un giorno alla volta." — Pulsanti: Registrati, Accedi.
3. **Signup** — Nome, Email, Password.
4. **Login** — Email, Password.
5. **Scelta percorso** — Card: Commercialista, Avvocato, Consulente finanziario. Per ora Commercialista sarà funzionante, gli altri "Prossimamente".
6. **Data esame** — "Quando vuoi sostenere l'esame?" — Calendario.
7. **Tempo giornaliero** — "Quanto vuoi dedicare ogni giorno?" — 5 / 10 / 20 / 30 / 45 / 60 min.
8. **Home**
9. **Lezione**
10. **Risultato**
11. **Percorso**
12. **Profilo**

## Fase 5 — Crea Supabase

Da FlutterFlow puoi collegare Supabase tramite OAuth:

`Settings & Integrations → Supabase → Connect with Supabase → scegli il progetto.`

Dopo aver creato o modificato le tabelle bisogna utilizzare **Get Schema** per sincronizzare la struttura con FlutterFlow.

## Fase 6 — Database

Non creare un database gigantesco. Partiamo da queste tabelle.

### Table: users

| Campo | Tipo |
|---|---|
| id | uuid |
| name | text |
| email | text |
| selected_exam | uuid |
| exam_date | date |
| daily_minutes | integer |
| xp | integer |
| current_streak | integer |
| readiness_score | decimal |
| created_at | timestamp |

### Table: exams

| Campo | Tipo |
|---|---|
| id | uuid |
| name | text |
| description | text |
| icon | text |
| active | boolean |

Inseriamo: Commercialista, Avvocato, Consulente finanziario.

### Table: subjects

Esempio:

| id | exam | materia |
|---|---|---|
| 1 | Commercialista | Diritto tributario |
| 2 | Commercialista | Bilancio |
| 3 | Commercialista | Diritto societario |
| 4 | Commercialista | Revisione |

Campi: id, exam_id, name, description, order_number.

### Table: units

Serve per creare i capitoli. Esempio: Commercialista → Diritto societario → Società di capitali.

Campi: id, subject_id, title, description, order_number.

### Table: lessons

Esempio: Società di capitali → La S.r.l.

Campi: id, unit_id, title, explanation, difficulty, xp_reward, order_number.

### Table: questions

Una delle tabelle più importanti.

Campi: id, lesson_id, question, answer_a, answer_b, answer_c, answer_d, correct_answer, explanation, difficulty, source, source_date, verified, question_type.

`question_type` potrebbe essere: multiple_choice, true_false, open, numeric, case.

### Table: user_answers

Ogni volta che una persona risponde salviamo: id, user_id, question_id, answer, correct, response_time, created_at.

Questo database diventerà fondamentale. Permetterà di capire cosa conosce, cosa sbaglia, quanto velocemente risponde, quali argomenti deve ripassare.

### Table: user_progress

Campi: user_id, lesson_id, completed, accuracy, mastery, last_review, next_review, attempts.

### Table: errors

Campi: user_id, question_id, error_type, created_at, resolved.

## Fase 7 — Sicurezza database

Quando l'app diventa reale, non lasciare le tabelle liberamente accessibili.

Supabase dispone di **Row Level Security (RLS)**, che consente di stabilire quali righe ogni utente può leggere o modificare. La documentazione Supabase raccomanda RLS sulle tabelle esposte.

Concetto semplice: Manuel deve poter leggere i progressi di Manuel, ma non quelli di Marco.

Esempio di policy:

- `users` → l'utente può modificare solo il proprio profilo.
- `user_answers` → l'utente può vedere solamente le proprie risposte.
- `user_progress` → solamente i propri progressi.
- `questions` → tutti gli utenti autenticati possono leggere, ma non modificare.

Le modifiche ai contenuti devono essere consentite solo agli amministratori.

Durante le prime prove puoi semplificare temporaneamente le policy, ma prima della pubblicazione RLS deve essere configurato correttamente.

## Fase 8 — Registrazione

Crea la tabella `users`. FlutterFlow richiede una tabella utenti per utilizzare l'autenticazione Supabase nella propria integrazione.

Dentro FlutterFlow: `Settings → Authentication → Enable Authentication → Supabase.`

Imposta:

- Logged Out Page → Welcome
- Logged In Page → Home

### Crea il pulsante Registrati

Seleziona il pulsante → `Actions → Add Action → Supabase Authentication → Create Account.`

Collega: Email → campo email, Password → campo password.

## Fase 9 — Onboarding

Dopo la registrazione mandiamo l'utente a `ChooseExam`. L'utente seleziona Commercialista. Salviamo `selected_exam`.

Poi `ExamDate` (es. 15 novembre 2027). Salviamo `exam_date`.

Poi `DailyGoal` (es. 30 minuti). Salviamo `daily_minutes = 30`.

A quel punto mandiamo l'utente alla Home.

## Fase 10 — Prima Home

Non renderla complessa. Esempio:

```
🔥 7 giorni
Ciao Manuel

Obiettivo di oggi
12 / 30 minuti
██████░░░░

Continua il percorso
Diritto societario
S.r.l. — Lezione 3
[ CONTINUA ]

XP: 1.240
Readiness: 52%
Esame tra: 187 giorni
```

## Fase 11 — Crea il primo percorso

Non creare subito tutto il programma Commercialista. Costruisci:

- **Materia**: Diritto societario
- **Unità**: Società di capitali
- **Lezioni**: 1. Introduzione, 2. S.p.A., 3. S.r.l., 4. Capitale sociale, 5. Amministratori, 6. Assemblea, 7. Responsabilità, 8. Checkpoint

Solo quando questo piccolo percorso funziona passiamo al resto.

## Fase 12 — Prima lezione

Una lezione non deve sembrare un libro.

Esempio: "S.r.l. — Una S.r.l. è una società di capitali…" (testo: massimo poche righe) → Pulsante CONTINUA.

Poi: "Quale affermazione è corretta?" con opzioni A, B, C, D.

Se corretto: "✅ Corretto! +10 XP" + spiegazione breve.

Se sbagliato: "❌ Non proprio. Risposta corretta: B." + spiegazione.

Pulsante: CONTINUA.

## Fase 13 — Risultato lezione

```
Lezione completata
⚡ +60 XP
🎯 Accuratezza: 80%
⏱ Tempo: 7:42
🧠 Mastery: +4%
[ CONTINUA ]
```

## Fase 14 — XP

Algoritmo semplicissimo iniziale:

- Risposta corretta: +10 XP
- Lezione completata: +20 XP
- Perfect lesson: +20 XP bonus

Successivamente potremo complicarlo. Non utilizzare gli XP per stabilire se l'utente è preparato.

## Fase 15 — Mastery

Ogni argomento ha un valore Mastery 0-100 (es. S.r.l. → Mastery: 72%).

Versione iniziale dell'algoritmo:

- Risposta corretta: +4
- Risposta sbagliata: -3
- Corretta dopo 7 giorni: +6
- Corretta dopo 30 giorni: +8
- Errore dopo aver raggiunto mastery alta: -5

Successivamente costruiremo un algoritmo più sofisticato.

## Fase 16 — Spaced repetition

Ogni domanda deve avere `last_review` e `next_review`.

- Risposta sbagliata → ripasso domani
- Risposta difficile → 3 giorni
- Risposta corretta → 7 giorni
- Risposta molto solida → 14 giorni
- Successivamente: 30 giorni, poi 60 giorni

## Fase 17 — Schermata ripasso

Home: "12 concetti da ripassare" → [ RIPASSA ]

FlutterFlow interroga Supabase con `next_review <= oggi` e recupera le domande.

## Fase 18 — Quaderno degli errori

Ogni risposta errata viene salvata nella tabella `errors`.

Pagina "I tuoi errori": Società di capitali — 6, Tributario — 12, Bilancio — 4 → [ RIPARA ERRORI ]

L'app crea automaticamente una sessione utilizzando quegli errori.

## Fase 19 — Streak

Salviamo `last_study_date` e `current_streak`.

- Se ultimo studio = ieri → streak +1
- Se ultimo studio = oggi → non cambia
- Se è passato più di un giorno → streak = 1

Successivamente aggiungeremo: Streak Freeze.

## Fase 20 — Percorso visivo

Trasformiamo il percorso in qualcosa di più simile a Duolingo: lezioni collegate, checkpoint, boss level. Gli elementi futuri sono bloccati; quando completi quello precedente si sblocca il successivo.

## Fase 21 — Assessment iniziale

Una volta funzionanti le lezioni, aggiungiamo un test iniziale di 20-40 domande che copre varie materie. Al termine mostra le percentuali per materia (es. Tributario 42%, Bilancio 71%, Societario 63%, Revisione 31%) e il piano iniziale dà priorità alle aree deboli.

## Fase 22 — Motore "cosa studiare oggi"

Il cuore di ProExam. Ogni giorno deve considerare:

1. Ripassi scaduti — peso molto alto
2. Lacune importanti — peso alto
3. Materie rilevanti — peso alto
4. Nuovi argomenti — peso normale
5. Contenuti già molto solidi — peso basso

Esempio con 30 minuti disponibili: 5 min ripasso IVA, 8 min S.r.l., 7 min bilancio, 5 min errori, 5 min test finale. L'utente NON deve costruire manualmente il programma.

## Fase 23 — Tempo fino all'esame

Calcoliamo `exam_date - oggi` (es. 187 giorni). Con 30 minuti × 187 giorni otteniamo 93,5 ore teoriche. L'app deve confrontare il tempo disponibile con il programma ancora necessario.

## Fase 24 — Traiettoria

Mostriamo messaggi come "Sei in linea" oppure "Devi aumentare leggermente il ritmo", con esempi concreti tipo "Con 15 minuti al giorno il piano non prevede il completamento del programma con sufficiente margine."

## Fase 25 — Readiness Score

Non utilizzare semplicemente la % di lezioni completate. Il Readiness deve combinare Mastery, Retention, Accuracy, Copertura, Simulazioni, Quesiti nuovi.

Pesi per la prima versione:

- 30% Mastery
- 20% Retention
- 15% Coverage
- 20% Simulazioni
- 15% Quiz recenti

Esempio risultato: Readiness 74/100.

## Fase 26 — Exam Ready

Lo stato EXAM READY non deve essere facile da ottenere. Esempio requisiti:

- Coverage > 90%
- Mastery > 85%
- Retention > 80%
- Ultime 3 simulazioni superate
- Nessuna macroarea < 75%

Questo non significa garantire il superamento dell'esame, ma certificare che l'utente soddisfa criteri interni severi.

## Fase 27 — AI Tutor

Solo ora aggiungiamo l'AI, non prima. FlutterFlow può effettuare chiamate REST API attraverso la propria sezione API Calls.

**NON** inserire direttamente nell'app una chiave API segreta. Architettura corretta: App → Backend sicuro → AI provider.

Cosa fa l'AI: pulsanti "Spiegamelo", "Spiegamelo semplice", "Fammi un esempio", "Interrogami", "Fammi un caso", "Perché ho sbagliato?".

## Fase 28 — AI con fonti

Per diritto, fiscalità e finanza l'AI non deve improvvisare. Il database deve contenere: argomento, risposta, normativa, fonte, data, verifica. L'AI riceve queste informazioni e le utilizza per spiegare.

## Fase 29 — Simulazioni

Pagina "Simulazioni": Mini (10 min), Standard (30 min), Esame completo (durata reale).

Al termine: punteggio (es. 78/100), Mastery, Errori, Tempo, Argomenti deboli.

## Fase 30 — Domande mai viste

Non valutare la preparazione solamente attraverso domande già incontrate. Mantieni una parte della banca dati riservata alle **Blind Questions**, usate nelle simulazioni. Questo rende il Readiness Score molto più attendibile.

## Fase 31 — Orale AI

Successivamente: "🎙️ Simulazione orale". L'AI pone una domanda, l'utente risponde parlando, l'app trascrive, analizza, assegna punteggio e fa una domanda successiva.

## Fase 32 — Aggiungi Avvocato

Quando Commercialista funziona, NON ricostruire l'app. Aggiungi `exam = Avvocato`, poi nuove subjects, units, lessons, questions. Il motore rimane uguale.

## Fase 33 — Aggiungi OCF

Stesso principio: `exam = Consulente finanziario`, nuove materie e banca domande. Tutto il resto continua a funzionare.

## Fase 34 — Admin Panel

A questo punto costruisci anche "ProExam Admin" (web), per amministrare il contenuto senza entrare manualmente in Supabase.

Menu: Dashboard, Esami, Materie, Lezioni, Domande, Normative, Utenti, Segnalazioni, Statistiche.

## Fase 35 — Controllo contenuti

Ogni domanda deve avere: Verified (YES/NO), Fonte, Ultima verifica, Professione, Materia, Argomento, Difficoltà. Solo `verified = true` può essere mostrata nell'app.

## Fase 36 — Abbonamenti

Soltanto quando il prodotto funziona aggiungiamo RevenueCat. Possibile modello:

**FREE**: lezioni base, streak, XP, numero limitato di sessioni.

**PRO**: percorso completo, ripasso intelligente, simulazioni, AI Tutor, Readiness, statistiche, orale AI.

## Fase 37 — Paywall

Esempio: "Passa a ProExam PRO — Preparazione completa" con checklist delle funzionalità PRO, opzioni Mensile/Annuale e pulsante [ PROVA PRO ].

## Fase 38 — Regole Apple

Gli abbonamenti digitali devono rispettare le regole dell'App Store: abbonamenti auto-rinnovabili con valore continuativo e condizioni spiegate chiaramente. Verificare nuovamente le regole vigenti prima della pubblicazione.

## Fase 39 — Notifiche

Non servono nella primissima versione. Successivamente: "🔥 Mantieni la tua serie.", "12 minuti per completare l'obiettivo.", "🧠 Hai 7 concetti da ripassare.", "Esame tra 30 giorni: oggi simulazione."

FlutterFlow supporta notifiche push tramite Firebase Cloud Messaging (richiede piano Blaze per il setup basato su Cloud Functions).

## Fase 40 — Test su iPhone

Prima dell'App Store, testa tutto su un vero iPhone: registrazione, login, logout, cambio password, lezioni, quiz, internet lento, chiusura app, ritorno nell'app, acquisti, ripristino acquisti, notifiche, cancellazione account, errori API.

Per le notifiche push iOS il test richiede un dispositivo reale, non il simulatore.

## Fase 41 — Apple Developer

Quando siamo quasi pronti: crea account Apple Developer, poi App Store Connect. FlutterFlow consente di distribuire una build direttamente verso App Store Connect.

## Fase 42 — Identificativo app

Esempio: `com.proexam.app` (Bundle Identifier). Non cambiarlo casualmente successivamente.

## Fase 43 — App Store Connect

Creiamo "ProExam", categoria Education. Inseriamo: nome, descrizione, icona, screenshot, privacy policy, support URL, classificazione età, informazioni privacy.

## Fase 44 — Privacy

ProExam raccoglierà probabilmente: email, progressi, risposte, comportamento di studio, eventualmente audio, dati sugli acquisti.

Bisognerà predisporre: Privacy Policy, Terms of Service, Gestione consenso, Cancellazione account, Gestione dati.

## Fase 45 — Submission

Dentro FlutterFlow: `Settings & Integrations → Mobile Deployment → App Store → Deploy.`

## Fase 46 — Beta test

NON pubblicare subito per tutti. Prima 10 utenti. Misura soprattutto: quante lezioni completano, dove abbandonano, quante domande sbagliano, quanto dura una sessione, quanti giorni consecutivi studiano, quali schermate creano confusione.

## Fase 47 — Metriche importanti

Non guardare soltanto i download. Guarda:

- **Retention D1** — quanti tornano il giorno dopo
- **Retention D7** — quanti tornano dopo una settimana
- **Retention D30** — quanti continuano dopo un mese
- **Daily sessions** — quante sessioni fanno
- **Completion rate** — quante lezioni iniziate vengono finite
- **Learning gain** — quanto migliorano realmente (potrebbe diventare la metrica più importante di ProExam)

## Fase 48 — Versione 2

Solo dopo aver validato l'MVP aggiungiamo: classifiche, league, amici, avatar, achievement avanzati, voce, AI Coach, challenge, community, gruppi studio, streak freeze, widget iPhone, Live Activities, Apple Watch.

## Ordine esatto in cui lavorare

1. Crea FlutterFlow.
2. Crea progetto ProExam.
3. Crea Supabase.
4. Collega Supabase.
5. Crea `users`.
6. Configura login.
7. Crea onboarding.
8. Crea `exams`.
9. Crea `subjects`.
10. Crea `units`.
11. Crea `lessons`.
12. Crea `questions`.
13. Inserisci 20 domande manualmente.
14. Crea schermata Lezione.
15. Crea risposta corretta/sbagliata.
16. Crea questa app.
