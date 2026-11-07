# TrendGuardEA (MetaTrader 4)

Expert Advisor trend-following con gestione del rischio rigida.

> ⚠️ **Nessun EA garantisce profitti.** Il trading su Forex/CFD con leva comporta un
> alto rischio di perdita. Usa sempre prima lo Strategy Tester e un **conto demo**.

## Strategia
- **Ingresso long**: EMA 20 incrocia sopra EMA 50, prezzo sopra EMA 200, RSI tra 50 e 70.
- **Ingresso short**: EMA 20 incrocia sotto EMA 50, prezzo sotto EMA 200, RSI tra 30 e 50.
- **Uscita**: Stop loss = 1,5 × ATR, Take profit = 3 × ATR (rapporto 1:2),
  break-even dopo 1 × ATR, trailing stop a 1,5 × ATR.

## Gestione del rischio
- Rischio fisso per operazione (default **1% del capitale**), lotto calcolato in automatico.
- Stop giornaliero: niente nuovi trade dopo una perdita del **3%** nella giornata.
- Filtro spread, filtro orario, massimo 1 posizione per simbolo.

## Installazione
1. In MT4: **File → Apri cartella dati → MQL4 → Experts**, copia `TrendGuardEA.mq4`.
2. Apri MetaEditor (F4), apri il file e premi **Compila** (F7).
3. In MT4 trascina l'EA su un grafico (es. EURUSD H1) e abilita **AutoTrading**.

## Come verificarlo (fondamentale)
1. **Strategy Tester** (Ctrl+R): modello "Ogni tick", almeno 3–5 anni di dati.
2. Guarda drawdown massimo, profit factor (> 1,3) e numero di trade (> 100).
3. Ottimizza pochi parametri e poi testa su un periodo **diverso** (out-of-sample),
   altrimenti rischi l'overfitting.
4. Almeno 1–3 mesi su **demo** prima di usare soldi veri, iniziando con capitale piccolo.

## Conto piccolo (es. 20 €)
Su un conto **standard** il lotto minimo è 0,01: su EURUSD vale circa 0,09 € per pip.
Con uno stop di 15–20 pip si rischiano 1,5–2 € a trade, cioè **7–10% di 20 €**:
l'EA in quel caso salta il trade (limite `MaxRiskCapPct` = 5%), quindi quasi non opererebbe.

**Soluzione consigliata: conto CENT.** 20 € diventano 2.000 "centesimi" e 0,01 lotti
valgono 1/100 di un lotto standard, quindi l'1% di rischio torna applicabile.
Imposta: `RiskPercent = 1`, `MaxRiskCapPct = 3`, `MaxDailyLossPct = 3`.

Aspettative realistiche: anche un ottimo +3–5% al mese su 20 € sono **0,60–1 €/mese**.
Con 20 € l'obiettivo sensato è imparare e validare la strategia, non guadagnare.
