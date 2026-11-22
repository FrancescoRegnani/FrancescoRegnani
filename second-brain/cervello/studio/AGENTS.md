# AGENTS.md — Second brain dello STUDIO

> **Mappa del palazzo.** Ogni agente la legge per prima. Resta **snella**: dice *dove* sono le cose,
> non le contiene. Apri gli altri file **solo quando servono**.
> Questo è il cervello di **lavoro** (PC dello studio). Le cose personali stanno nel cervello di casa, non qui.

## Chi sono
<!-- Compilato da /intervista. Max 5 righe. -->
- Francesco, commercialista in uno studio professionale.
- Risposte: italiano, dirette, prima la conclusione poi i dettagli, passaggi numerati.

## Il palazzo
| Stanza | Cosa contiene | Quando aprirla |
|---|---|---|
| `MEMORY.md` | Diario di bordo dello studio: decisioni, cose in sospeso | A inizio lavoro (solo le ultime voci) |
| `clienti/<nome>/` | **Ali** dei clienti: scheda (tipo, periodicità mensile/trimestrale, regime), diario, chiamate, consulenza, documenti | Quando il compito riguarda quel cliente |
| `reference/` | **Biblioteca**: modelli di offerte, pareri, lettere, email | Quando produci un documento con un modello |
| `scadenzari/` | Scadenzari salvati | Quando chiedo le scadenze |
| `inbox/` | Appunti e file da smistare | Quando chiedo di smistare l'inbox |
| `archivio/` | Clienti chiusi, memoria vecchia | Solo su richiesta |
| `.claude/skills/` | **Procedure** ripetibili | Vedi sotto |

## Le strade (collegamenti)
- Gmail e Google Drive dello studio via connettori: **solo lettura**, salvo mia richiesta esplicita.
- Recapiti: skill `/rubrica-clienti`. Quesiti professionali: `/consulta-pro` (solo fonti ufficiali).
- TeamSystem: istruzioni in `/teamsystem-contabile` (se disponibile). Mai operare nel gestionale senza conferma.

## Procedure
Per altri agenti: file di istruzioni in `.claude/skills/<nome>/SKILL.md`.
- `intervista` — crea o aggiorna questa mappa
- `nuovo-cliente` — apre l'ala di un cliente (tipo, periodicità, regime)
- `brief-cliente` — punto della situazione di un cliente da email e Drive
- `offerta` — preventivo dal modello in `reference/`
- `scadenzario` — scadenze del periodo (clienti mensili, trimestrali, enti non commerciali)
- `pulisci-dettato` — dettato vocale → richiesta pulita
- `chiudi-sessione` — a fine lavoro aggiorna memoria, mappa e biblioteca

## Regole
1. Non leggere tutto: parti dalla mappa, apri solo ciò che serve.
2. Ogni cliente nella sua ala; mai mescolare dati di clienti diversi.
3. Mai inventare norme, importi, scadenze o dati: se manca la fonte, dillo. Cita la fonte ufficiale.
4. Prima di inviare, cancellare, condividere o modificare qualcosa all'esterno (email, PEC, Drive, TeamSystem): chiedi conferma.
5. Nessun dato dei clienti va salvato in memorie esterne (es. Honcho): restano in questa cartella.
6. A fine sessione proponi `chiudi-sessione`.
