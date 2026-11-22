---
name: scadenzario
description: Costruisce lo scadenzario del periodo (settimana o mese) per i clienti dello studio e per gli immobili di famiglia, distinguendo clienti a contabilità mensile e trimestrale ed enti non commerciali. Usala con /scadenzario o quando l'utente chiede "cosa scade questo mese", "scadenze della settimana".
---

# Scadenzario

1. Chiedi il periodo se non è chiaro (default: da oggi a fine mese prossimo).
2. Considera solo le stanze che esistono in questo cervello. Leggi la **Scheda** di ogni `clienti/*/AGENTS.md` (tipo, periodicità, regime, servizi) e
   la sezione "In sospeso" dei rispettivi `MEMORY.md`. Leggi `immobili/*/AGENTS.md` (scadenze contratti, rinnovi, ISTAT).
3. Raggruppa:
   - **Clienti mensili**: liquidazione e versamento IVA del mese, F24.
   - **Clienti trimestrali**: liquidazione IVA del trimestre (solo nei mesi di scadenza).
   - **Enti non commerciali**: adempimenti propri (rendiconti, 398/91, RUNTS) se presenti in scheda.
   - **Adempimenti annuali** del periodo (dichiarativi, LIPE, bilanci, CU…).
   - **Immobili di famiglia**: scadenze e rinnovi contratti, registrazioni annuali, cedolare, IMU.
   - **Cose in sospeso** dai diari.
4. **Date**: non affidarti alla memoria. Verifica ogni data su fonti ufficiali (Agenzia Entrate, scadenzario
   fiscale ufficiale, Eutekne) o con /consulta-pro, considerando proroghe e giorni festivi. Se non puoi
   verificarla, scrivi "da verificare".
5. Output: tabella ordinata per data — data, adempimento, chi (cliente/immobile), stato, fonte.
   Segnala i clienti con scheda incompleta (periodicità mancante).
6. Se richiesto, salva in `scadenzari/AAAA-MM.md`.
