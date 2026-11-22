---
name: offerta
description: Prepara un'offerta/preventivo per un cliente seguendo il modello in reference/struttura-offerta.md, in Markdown e, se richiesto, in PDF. Usala con /offerta o quando l'utente chiede un preventivo o una proposta.
---

# Offerta

1. Leggi `reference/struttura-offerta.md` e, se esiste, `clienti/<cliente>/brief.md` e `AGENTS.md`.
2. Chiedi solo gli elementi variabili mancanti (oggetto, attività, compenso, tempi, validità).
3. Scrivi `clienti/<cliente>/documenti/AAAA-MM-GG-offerta.md` seguendo sezioni, ordine e tono del modello.
4. Se l'utente vuole il PDF, convertilo (es. con la skill PDF o `pandoc`) nella stessa cartella.
5. Mostra un riepilogo (importo, tempi, esclusioni) e aggiorna `MEMORY.md` del cliente.
Non inventare importi o condizioni: se non li hai, chiedili.
