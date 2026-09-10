# ProExam (MVP)

App di preparazione agli esami professionali, in stile Duolingo. Percorso
funzionante per ora: **Commercialista → Diritto societario → Società di
capitali** (8 lezioni). Segue `PROEXAM_GUIDE.md` nella root del repository,
Fasi 0-20 (MVP core).

Stack: **Expo / React Native** + **TypeScript** + **expo-router** +
**Supabase** (database, auth, RLS).

## Cosa è già pronto

- Registrazione/login/logout con Supabase Auth (email+password).
- Onboarding: scelta esame, data esame, tempo di studio giornaliero.
- Home con streak, obiettivo del giorno, XP, readiness (approssimata),
  giorni all'esame, scorciatoie a ripasso ed errori.
- Percorso visivo con lezioni sbloccate progressivamente.
- Lezione con spiegazione + quiz a risposta multipla, feedback immediato.
- Schermata risultato (XP, accuratezza, tempo, mastery).
- XP, mastery, spaced repetition e streak (algoritmi semplici, Fase 14-19
  della guida — pensati per essere sostituiti da versioni più sofisticate
  in seguito).
- Quaderno degli errori e ripassi in scadenza.
- Schema SQL completo con Row Level Security (`supabase/schema.sql`) e
  contenuto di esempio (`supabase/seed.sql`).

## Cosa NON è ancora incluso (fasi successive della guida)

AI Tutor, simulazioni, Readiness Score completo, abbonamenti/RevenueCat,
notifiche push, admin panel, Avvocato/OCF e gli altri esami. Vanno
aggiunti quando l'MVP core è validato, come raccomandato dalla guida
stessa (Fase 0).

## 1. Configura Supabase

1. Crea un progetto su [supabase.com](https://supabase.com).
2. Apri **SQL Editor** e incolla il contenuto di `supabase/schema.sql`,
   poi eseguilo.
3. Fai lo stesso con `supabase/seed.sql` per popolare il percorso
   Commercialista di esempio (⚠️ i contenuti legali sono di esempio: prima
   di usarli con utenti reali fai revisionare ogni domanda da un
   professionista, come richiesto dalla Fase 35 della guida).
4. In **Authentication → Providers**, verifica che Email sia abilitato.
   Se vuoi saltare la conferma via email durante lo sviluppo, disattiva
   "Confirm email" in **Authentication → Settings**.
5. Copia `Project URL` e `anon public key` da **Settings → API**.

## 2. Configura l'app

```bash
cd app
cp .env.example .env
# incolla EXPO_PUBLIC_SUPABASE_URL e EXPO_PUBLIC_SUPABASE_ANON_KEY
npm install
```

## 3. Avvia in sviluppo

```bash
npm run ios       # richiede macOS + Xcode, oppure usa Expo Go
npm run android
npm start          # poi scansiona il QR code con Expo Go
```

Testa il flusso completo: registrazione → onboarding → home → lezione →
quiz → risultato → progressione. Il trigger SQL crea automaticamente la
riga in `public.users` alla registrazione.

## 4. Prepara la build nativa (EAS)

Serve un account Expo (gratuito) e la CLI EAS:

```bash
npm install -g eas-cli
eas login
eas build:configure
```

Questo genera `eas.json`. Per una build iOS di sviluppo/interna:

```bash
eas build --platform ios --profile preview
```

## 5. Requisiti da completare tu prima della pubblicazione

Questi passaggi richiedono le tue credenziali/decisioni reali e non
possono essere completati da un agente:

1. **Apple Developer Program** (99$/anno) — crea l'account su
   [developer.apple.com](https://developer.apple.com).
2. **App Store Connect** — crea l'app con bundle id `com.proexam.app`
   (già impostato in `app.json`), categoria Education.
3. **Branding reale** — sostituisci le icone placeholder in `assets/`
   (icon, splash, adaptive icon Android) con la vera identità ProExam
   (Fase 3 della guida: verde/blu per Commercialista).
4. **Privacy Policy e Terms of Service** — pagine pubbliche reali (Fase
   44): l'app raccoglie email, progressi, risposte alle domande.
   Serve anche la cancellazione account (obbligatoria per l'App Store se
   c'è login).
5. **Screenshot e metadata** dello Store (descrizione, parole chiave,
   classificazione età).
6. **Build e submit**:
   ```bash
   eas build --platform ios --profile production
   eas submit --platform ios
   ```
7. **Contenuto verificato**: prima di far studiare utenti reali, fai
   rivedere ogni domanda `verified = true` da un professionista (Fase 35).
8. **RLS in produzione**: le policy in `supabase/schema.sql` sono già
   pensate per la produzione (ogni utente vede solo i propri dati); non
   disattivarle.
9. Testa tutto su un iPhone fisico prima della submission (Fase 40):
   notifiche push e alcuni flussi non funzionano nel simulatore.

## Struttura del progetto

```
app/
  _layout.tsx          Root layout (Auth provider, Stack)
  index.tsx            Redirect gate (auth/onboarding/home)
  welcome.tsx, signup.tsx, login.tsx
  onboarding/           choose-exam, exam-date, daily-goal
  (tabs)/               home, path, profile (bottom tabs)
  lesson/[id].tsx        spiegazione + quiz
  lesson-result.tsx
  errors.tsx             quaderno degli errori (Fase 18)
  review.tsx             ripassi in scadenza (Fase 17)
lib/
  supabase.ts            client Supabase
  database.types.ts       tipi TS dello schema
  queries.ts              accesso ai dati (letture/scritture)
  learning.ts             XP, mastery, spaced repetition, streak (pure functions)
  auth-context.tsx        sessione utente + profilo
constants/theme.ts        colori, spaziatura, tipografia
components/ui.tsx         componenti UI condivisi
supabase/schema.sql        (nella root del repo) schema + RLS
supabase/seed.sql          (nella root del repo) contenuto di esempio
```
