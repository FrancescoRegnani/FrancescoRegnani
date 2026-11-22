# AGENTS.md — Second brain PERSONALE (casa)

> **Mappa del palazzo.** Ogni agente la legge per prima. Resta **snella**: dice *dove* sono le cose.
> Questo è il cervello **personale** (Mac di casa). Il lavoro dello studio e i dati dei clienti
> stanno nel cervello dello studio, sul PC dell'ufficio: **non qui**.

## Chi sono
<!-- Compilato da /intervista. Max 5 righe. -->
- Francesco, commercialista; qui gestisco immobili di famiglia e progetti personali.
- Risposte: italiano, dirette, prima la conclusione poi i dettagli, passaggi numerati.

## Il palazzo
| Stanza | Cosa contiene | Quando aprirla |
|---|---|---|
| `MEMORY.md` | Diario di bordo personale | A inizio lavoro (solo le ultime voci) |
| `immobili/<nome>/` | Immobili di **famiglia**: scheda, contratti, inquilini, spese | Quando il compito riguarda un immobile |
| `progetti/<nome>/` | Progetti personali (Abilita, Jarvis, strumenti AI…) | Quando il compito riguarda quel progetto |
| `reference/` | Modelli ed esempi riusabili | Quando produci un documento con un modello |
| `scadenzari/` | Scadenzari salvati (immobili, scadenze personali) | Quando chiedo le scadenze |
| `inbox/` | Appunti e file da smistare | Quando chiedo di smistare l'inbox |
| `archivio/` | Cose chiuse, memoria vecchia | Solo su richiesta |
| `.claude/skills/` | **Procedure** ripetibili | Vedi sotto |

## Le strade (collegamenti)
- Gmail e Google Drive personali via connettori: **solo lettura**, salvo mia richiesta esplicita.
- Memoria Honcho: ricorda chi sono e come lavoro.

## Procedure
Per altri agenti: file di istruzioni in `.claude/skills/<nome>/SKILL.md`.
- `intervista` — crea o aggiorna questa mappa
- `nuovo-immobile` — crea la scheda di un immobile di famiglia
- `scadenzario` — scadenze del periodo (contratti, rinnovi, ISTAT, cedolare, IMU)
- `pulisci-dettato` — dettato vocale → richiesta pulita
- `chiudi-sessione` — a fine lavoro aggiorna memoria, mappa e biblioteca

## Regole
1. Non leggere tutto: parti dalla mappa, apri solo ciò che serve.
2. Mai inventare norme, importi o scadenze: se manca la fonte, dillo.
3. Prima di inviare, cancellare o condividere qualcosa all'esterno: chiedi conferma.
4. Niente dati di clienti dello studio qui: se ne compaiono, segnalalo.
5. A fine sessione proponi `chiudi-sessione`.
