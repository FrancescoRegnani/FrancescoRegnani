---
name: pulisci-dettato
description: Trasforma un testo dettato a voce (Wispr Flow, dettatura Mac, note vocali) in un prompt o appunto pulito e strutturato. Usala con /pulisci-dettato o quando l'utente incolla un dettato disordinato.
---

# Pulisci dettato

1. Prendi il testo dettato così com'è.
2. Togli ripetizioni, intercalari ("ehm", "cioè", "praticamente") e false partenze;
   correggi gli errori di trascrizione evidenti (nomi di clienti: verifica in `clienti/`).
3. Restituisci:
   - **Richiesta**: cosa va fatto, in una frase.
   - **Contesto**: cliente/progetto e informazioni utili.
   - **Vincoli**: scadenze, formato, cose da evitare.
   - **Dubbi**: punti ambigui da chiarire.
4. Chiedi: "Procedo con questa richiesta?" e, se sì, eseguila.
   Se è solo un appunto, proponi dove salvarlo (`inbox/` o l'ala del cliente).
