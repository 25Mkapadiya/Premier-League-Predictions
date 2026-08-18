# PL Forecast — Premier League Predictions

A dark, sports-first **2026/27 Premier League prediction dashboard** inspired by the information density of modern score sites while keeping its own visual identity. It combines score forecasts, 1X2 probabilities, prediction markets, result review, standings, a matchup simulator and transparent model documentation.

## What is in the app

- Scores-site style three-column desktop structure: competition navigation, match feed and insights rail
- Dark interface designed specifically around football predictions
- Featured prediction plus compact match rows
- Upcoming / Live / Final match states
- 1X2 probabilities for every matchup
- Over/Under 2.5, BTTS and correct-score probability signals
- Prediction-vs-result review after finished games
- League table calculated from the latest finished fixtures
- Quick standings rail and next-kickoff module
- Team search / filter
- Matchup Lab for any two 2026/27 Premier League clubs
- Responsive mobile navigation
- Versioned results snapshot with a visible last-sync time
- Automatic expansion to all 38 matchweeks when the live fixture snapshot is available

## Daily / on-demand result refresh

The public site is static GitHub Pages, so it does **not** depend on a fragile browser-side sports API call.

Instead, `.github/workflows/refresh-results.yml` runs `scripts/refresh_results.py` and commits a fresh `data/live.js` snapshot.

The workflow supports both:

- **Daily automatic refresh** at 06:20 UTC
- **Manual refresh** through GitHub Actions → `Refresh Premier League results` → `Run workflow`

The refresh script tries the Fantasy Premier League fixture endpoint first and falls back to the current-season Football-Data.co.uk Premier League CSV if needed. The page-level refresh button cache-busts and reloads the newest committed `data/live.js` file.

### Why this architecture

GitHub Pages cannot securely store API secrets, and some football endpoints do not allow normal browser cross-origin requests. A committed snapshot gives the site reliable, auditable data with no client credentials.

## Run locally

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Prediction model

The model combines:

1. Venue-adjusted attack and defense scoring rates
2. Shrinkage toward league averages
3. Elo team-strength adjustment with home advantage
4. Poisson score probabilities
5. Dixon-Coles low-score correction
6. A promoted-team translation for Coventry, Ipswich and Hull

The current preseason model uses Premier League results from **2023/24, 2024/25 and 2025/26**, plus **2025/26 Championship** performance for promoted-team translation.

See [`docs/MODEL.md`](docs/MODEL.md) for methodology and validation.

## Validation

The rolling pre-match 2025/26 backtest produced:

- **48.7%** top 1X2 outcome accuracy
- **42.6%** always-home baseline
- **0.628** multiclass Brier score
- **1.042** log loss

No future match outcomes were included in earlier predictions during the rolling backtest.

## Data sources

- Official 2026/27 schedule: PremierLeague.com fixture release
- Historical match results: Football-Data.co.uk
- Refresh feed: Fantasy Premier League fixtures endpoint on `fantasy.premierleague.com`
- Method reference: Dixon-Coles / Poisson football score modeling research

Fixtures and kick-off times can change. This is an independent fan project and is not affiliated with or endorsed by the Premier League or its clubs. Predictions are estimates, not betting advice.

## Project structure

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   ├── fixtures.js
│   ├── model.js
│   └── live.js
├── scripts/
│   └── refresh_results.py
├── .github/
│   └── workflows/
│       └── refresh-results.yml
└── docs/
    └── MODEL.md
```

## Refresh locally

```bash
python scripts/refresh_results.py
```

That command rewrites `data/live.js` with the latest available fixture/result snapshot.
