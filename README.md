# PL Forecast — Premier League Predictions

A dark, sports-first **2026/27 Premier League prediction dashboard** with a transparent ensemble model, daily result refreshes and prediction-vs-result auditing.

## Prediction framework

The app now combines:

1. **Structural score model** — venue-adjusted Poisson + Elo + Dixon-Coles
2. **Opponent-adjusted recent form** — exponentially weighted residual performance from matches completed before kickoff
3. **Optional bookmaker consensus** — vig-free 1X2 probabilities blended conservatively with the football model
4. **Optional pre-match context** — bounded, sourced lineup/injury/suspension adjustments

Every match card can show the contribution/status of Base, Form, Market and data quality. Missing inputs fall back safely instead of being guessed.

See [`docs/ENSEMBLE.md`](docs/ENSEMBLE.md) for the full framework and accuracy roadmap.

## App features

- Full 38-matchweek schedule when available from the refresh feed
- Home / draw / away probabilities
- Rounded expected-score forecast and most likely exact score
- Over/Under 2.5 and BTTS probabilities
- Model-component breakdown and signal agreement
- Results page retaining the original prediction beside the final score
- Running 1X2 hit rate and Brier score after games finish
- League table and last-five form
- Matchup Lab for any two Premier League clubs
- Responsive dark sports-dashboard interface
- Daily + manual GitHub Actions refresh

## Daily result + market refresh

`.github/workflows/refresh-results.yml` runs `scripts/refresh_results.py` and commits a fresh `data/live.js` snapshot.

The workflow supports:

- automatic daily refresh at 06:20 UTC
- manual refresh from GitHub Actions
- FPL fixture/result feed as the primary schedule/result source
- Football-Data.co.uk result fallback
- optional The Odds API EPL 1X2 consensus

### Enable bookmaker consensus

The project works without a bookmaker API key. To enable the market layer:

1. Create an API key with **The Odds API**.
2. In the GitHub repository open **Settings → Secrets and variables → Actions**.
3. Create a repository secret named exactly `ODDS_API_KEY`.
4. Run **Actions → Refresh Premier League results → Run workflow**.
5. Open the site and verify the right rail says that market consensus is connected.

The secret is only used inside GitHub Actions. It is never placed in browser JavaScript or committed to the repository.

## Pre-match context

`data/context.js` is deliberately empty by default. Add a fixture adjustment only when the information is sourced before kickoff.

Example shape:

```js
"Arsenal__Coventry": {
  "homeAttackMultiplier": 0.98,
  "homeDefenseMultiplier": 1.00,
  "awayAttackMultiplier": 1.00,
  "awayDefenseMultiplier": 1.00,
  "note": "Confirmed starting striker unavailable",
  "updated": "2026-08-21T17:30:00Z"
}
```

Keep normal adjustments close to 1.00. The code contains wider hard safety limits, but those are not target values.

## Data / leakage policy

For a fixture at time `T`:

- recent form only uses matches completed before `T`
- market data must be a snapshot available before `T`
- lineup/injury context must have been known before `T`
- historical predictions should never be rewritten using information learned after the match

This policy is more important than adding a more complicated algorithm.

## Current benchmark

The earlier structural model's rolling 2025/26 check produced:

- 48.7% top 1X2 outcome accuracy
- 42.6% always-home baseline
- 0.628 multiclass Brier score
- 1.042 log loss

These numbers remain the benchmark. **Do not claim the new ensemble is more accurate until it has been walk-forward backtested on the same historical fixtures.**

## Run locally

```bash
python3 -m http.server 8000
```

Open `http://localhost:8000`.

To refresh data locally:

```bash
python scripts/refresh_results.py
```

To include market consensus locally:

```bash
ODDS_API_KEY="your-key" python scripts/refresh_results.py
```

## Project structure

```text
.
├── index.html
├── styles.css
├── ensemble.css
├── app.js
├── data/
│   ├── fixtures.js
│   ├── model.js
│   ├── live.js
│   └── context.js
├── scripts/
│   └── refresh_results.py
├── .github/
│   └── workflows/
│       └── refresh-results.yml
└── docs/
    ├── MODEL.md
    └── ENSEMBLE.md
```

## Important

The listed prediction websites were used as **research references for publicly visible signals and product patterns**, not copied as proprietary models. This project remains independent and its probabilities are estimates, not betting advice.
