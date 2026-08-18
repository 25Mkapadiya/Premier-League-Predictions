# Premier League Predictions

A polished, zero-build web app for **2026/27 Premier League match predictions**. It shows predicted scores, home/draw/away probabilities, expected goals, a matchup simulator, preseason power rankings, and the methodology behind every prediction.

## What is in the app

- Matchweek 1 through 5 fixture predictions using the official 2026/27 schedule
- Home / draw / away probabilities for every matchup
- Rounded expected-score forecasts plus expected goals
- Matchup Lab for any pair of 2026/27 clubs
- Preseason power rankings with attack and defense indicators
- Visible model validation and data-source notes
- Responsive desktop and mobile design
- No framework or build step required

## Run locally

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Prediction model

The model combines:

1. Venue-adjusted attack and defense scoring rates
2. Shrinkage toward league averages to reduce small-sample noise
3. Elo team-strength adjustment with home advantage
4. Dixon-Coles low-score correction for 0-0, 1-0, 0-1, and 1-1 outcomes
5. A promotion translation so Championship scoring is not treated as directly equivalent to Premier League scoring

The current snapshot uses Premier League results from **2023/24, 2024/25, and 2025/26**, plus **2025/26 Championship** results to estimate Coventry City, Ipswich Town, and Hull City.

See [`docs/MODEL.md`](docs/MODEL.md) for the full methodology and validation notes.

## Validation

A rolling pre-match backtest on the 2025/26 Premier League season produced:

- **48.7%** top-outcome accuracy across home/draw/away
- **42.6%** accuracy for the naive baseline of always choosing the home team
- **0.628** multiclass Brier score

The backtest only uses information available before each fixture date. It does not leak future results into earlier predictions.

## Sources

- Official Premier League 2026/27 fixture release: `premierleague.com/en/news/4675097/all-380-fixtures-for-202627-premier-league-season`
- Historical match data: `football-data.co.uk/englandm.php`
- Dixon-Coles methodology background: `arxiv.org/abs/2307.02139`

Fixtures are subject to change. This project is independent and is not affiliated with or endorsed by the Premier League or its clubs.

## Files

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   ├── fixtures.js
│   └── model.js
└── docs/
    └── MODEL.md
```

## Next accuracy upgrades

The most useful future improvements would be current player availability, transfer-strength adjustments, expected-goals data, and optional market-odds calibration. Those are intentionally not fabricated in this version.
