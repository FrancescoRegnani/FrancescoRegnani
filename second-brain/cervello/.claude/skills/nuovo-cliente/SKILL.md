---
name: nuovo-cliente
description: Apre una nuova ala cliente nel second brain copiando clienti/_modello-cliente. Usala quando l'utente dice "nuovo cliente", "apri cartella per…" o nomina un cliente che non ha ancora un'ala.
---

# Nuova ala cliente

1. Chiedi (se mancano): nome cliente, tipo (società, ditta, professionista, ente non commerciale, privato),
   **periodicità contabilità/IVA (mensile, trimestrale, nessuna)**, regime, referente, servizi.
   Per i recapiti cerca prima con /rubrica-clienti.
2. Crea `clienti/<nome-in-minuscolo-con-trattini>/` copiando `clienti/_modello-cliente/`.
3. Sostituisci i segnaposto `{{…}}` in `AGENTS.md` e `MEMORY.md`; lascia vuoto ciò che non sai.
4. Aggiungi in `MEMORY.md` del cliente la voce di apertura con la data di oggi.
5. Proponi di eseguire `brief-cliente` se Gmail/Drive sono collegati.
Non copiare mai dati di un altro cliente.
