# Odds Intelligence 0.1

**Standalone prototype. Nothing in this package accesses or modifies ABILITA.**

## Scope

- FastAPI API with token authentication
- SQLite for local tests; PostgreSQL for production
- Two-way tennis pre-match snapshots, normalized implied probabilities
- Detection of directional movements in a rolling observation window, requiring agreement among independent bookmakers
- Evidence registry and chronology-aware analysis endpoint; **no AI-generated causal explanations yet**
- Optional The Odds API adapter; provider coverage and historical data depend on your plan
- Demo data explicitly labelled and disabled by default

**Not included yet:** exchange traded volumes, live news discovery, tennis fatigue calculations, Telegram alerts, browser dashboard, automatic AI reports. No claim of tracking money staked is made. API `/docs` is a developer interface, not a dashboard.

## 0.2 — Multi-sport dashboard (operational)

- `app/probability.py`: American/decimal conversion, margin-free probabilities for 2-way and 3-way (1X2) markets, consensus across sources, confidence band.
- `app/collector.py`: pulls real pre-match prices, no API key needed:
  - ESPN public scoreboard → DraftKings moneyline (opening and current), totals, 1X2 for NBA, NHL, Serie A, Premier League, LaLiga, Bundesliga, Ligue 1, Champions/Europa/Conference League.
  - Polymarket Gamma API → ATP/WTA tennis (ESPN carries no tennis odds) and a second source for NBA/NHL. Markets with spread > 0.10 or liquidity < $500 are skipped.
  - Writes `web/data.json`; each event has per-outcome probability, fair odds, book odds, the most likely outcome ("pick"), source gap and the open→current move (flagged at `MIN_PROBABILITY_MOVE_PP`).
- `web/index.html`: static dashboard (tabs: Più probabili, Tennis, Basket, Calcio, Hockey NHL, Movimenti). Serve the `web/` folder with any static server.

```bash
python -m app.collector --out web/data.json --days 4
python -m http.server -d web 8080
python -m pytest -q
```

Limits: probabilities are market estimates, not outcome guarantees. One bookmaker (DraftKings) plus one prediction market; the 3-bookmaker consensus rule of 0.1 still applies only to the API pipeline. Data refreshes only when the collector runs.

## 0.3 — Live web app, all markets, match analysis

- `web/index.html` fetches everything in the browser: full scan every 60 s (ESPN scoreboards + Polymarket events), Polymarket mid prices every 3 s (`clob.polymarket.com/midpoints`).
- Markets per match: 1X2/winner, double chance, Asian handicap / spread / puck line, totals (DraftKings and Polymarket lines), tennis first set, set and game handicaps, game totals, number of sets; football Goal/No Goal, Over/Under 1.5/2.5/3.5 and exact scores from a Poisson model fitted to 1X2 + the bookmaker total (labelled "Modello").
- Match analysis on demand: ESPN summary (form, standings, head-to-head, injuries, key players, goalies, ESPN predictor) and 24 h Polymarket price history; optional AI analysis and AI slips on claude.ai (`sample` capability).
- The collector engine lives between `/*ENGINE-START*/` and `/*ENGINE-END*/` in `web/index.html`; `node scripts/snapshot.mjs` runs the same engine to write `web/data.json` (fallback/snapshot). `python scripts/build_site.py DIR` wraps the page for GitHub Pages (`gh-pages` branch).

## Requirements

Python 3.11+; modern supported Linux distribution. CentOS 7 and legacy Plesk/PHP installations are not a safe target for an internet-exposed service. Prefer a supported VM/container on your existing hardware. Python dependencies are version-ranged for initial prototyping; pin a tested lockfile before production.

## Local quick start

```bash
unzip odds-intelligence-0.1.zip
cd odds-intelligence-0.1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set a random API_TOKEN in .env; set ALLOW_DEMO=true for the demo only
set -a; source .env; set +a
python -m app.demo
uvicorn app.main:app --host 127.0.0.1 --port 8088
```

Try:

```bash
curl http://127.0.0.1:8088/health
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8088/anomalies
curl -H "Authorization: Bearer $API_TOKEN" http://127.0.0.1:8088/events/DEMO:MICHELSEN-LEHECKA/analysis
```

Open `http://127.0.0.1:8088/docs` locally for interactive API documentation. The demo uses synthetic quotes and a fictional event timestamp. It is **not** historical market evidence.

## Production on an existing server

1. Use a supported Linux VM/container, dedicated Unix user `odds`, and separate database credentials. Do not reuse ABILITA secrets, database, schema, or network access.
2. Copy project into `/opt/odds-intelligence`, create `.venv`, install dependencies, and place `.env` with permissions `0600`.
3. Provision a **new** PostgreSQL database. Run `sql/postgres.sql` in that database, and set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/odds_intelligence`. Use least-privilege credentials and TLS when remote. SQLite is acceptable for development only.
4. Configure a long random `API_TOKEN` and `ALLOW_DEMO=false`.
5. Obtain a valid ODDS_API_KEY and confirm that the provider covers the required ATP/WTA markets in your region. Data is not automatically live without this key.
6. Copy the `deploy/*.service` and `deploy/*.timer` units to `/etc/systemd/system`, then run `sudo systemctl daemon-reload`, `sudo systemctl enable --now odds-api.service`, and, **only after configuring the provider**, `sudo systemctl enable --now odds-poll.timer`.
7. Put HTTPS reverse proxy with access controls in front of localhost port 8088. Never expose port 8088 or database publicly. Limit API token distribution.
8. Configure log rotation, backups, retention limits, monitoring, and provider quota alerts before sustained collection.

## Data semantics / limitations

- Detection compares earliest and latest **complete two-outcome** snapshots from each bookmaker in the last 60 minutes of that bookmaker's available observations. Minimum three bookmaker movements of the same sign. This is an initial rule, not a statistically validated model.
- Bookmaker snapshots may arrive with stale `last_update` timestamps. Provider polling can create repeated rows when quotes are unchanged. Add an ingestion watermark/unique snapshot constraint before sustained production use.
- No actual exchange traded-volume data is ingested in this release; bookmaker prices do not reveal the amount of money wagered.
- A recorded news item must have been published **before** the first detected movement to be included in `/analysis`. Its presence is not proof of causality.
- No historical backfill, no automatic athlete injury/fatigue inference, no guaranteed coverage, no ROI/prediction claims.
- API has an administrator token rather than multiuser authentication; protect it behind a reverse proxy/VPN.

## Next milestone

Add provider integration tests, historical replay, deduplicated ingestion, automated verified sports-news retrieval, fatigue features and exchange liquidity, followed by Telegram notifications and a proper dashboard.
