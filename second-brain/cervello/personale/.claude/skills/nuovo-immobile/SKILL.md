---
name: nuovo-immobile
description: Crea la scheda di un immobile di famiglia in immobili/ dal modello. Usala quando l'utente dice "nuovo immobile", "aggiungi la casa di…" o parla di un immobile di famiglia che non ha ancora una cartella. Non per gli immobili dei clienti (quelli vanno nell'ala del cliente).
---

# Nuovo immobile di famiglia

1. Chiedi (se mancano): nome breve (es. `via-roma-12`), indirizzo, uso (affitto breve, lungo, famiglia, sfitto).
2. Crea `immobili/<nome>/` copiando `immobili/_modello-immobile/`.
3. Compila la scheda con ciò che l'utente sa; lascia `{{…}}` dove manca e elenca i dati mancanti.
4. Se l'utente fornisce un contratto o una visura (PDF in `inbox/`), estrai i dati e sposta il file in `contratti/`.
5. Aggiungi la voce di apertura in `MEMORY.md` dell'immobile.
