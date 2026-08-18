# PL Forecast — Premier League Predictions

A dark 2026/27 Premier League forecasting dashboard built around a **no-API, no-secret prediction pipeline**. The site uses public downloadable football data, public xG pages, a time-ordered trained ensemble, and frozen pre-kickoff forecasts.

## No-key data stack

The production site does not require API keys.

- **Premier League schedule** — retained in the repository from the official 2026/27 fixture release
- **Football-Data.co.uk** — public CSV results, shots, shots on target, historical odds and upcoming fixture odds when EPL rows are published
- **Understat** — public EPL league pages used to enrich completed matches with xG/xGA when the page data is available
- **Repository model priors** — venue attack/defense, Elo and promoted-team translation from prior seasons

If a public source has not updated, the engine keeps the last safe snapshot and falls back to the strongest statistical layer it can support. It never invents missing inputs.

## Prediction engine v4

For each fixture the engine combines:

1. venue-adjusted attack and defense priors
2. Elo strength and home advantage
3. Poisson score probabilities
4. Dixon-Coles low-score correction
5. opponent-adjusted recent performance with time decay
6. separate recent home/away venue form
7. current-season Elo movement
8. xG/xGA residuals when Understat data exists
9. shots-on-target form as a capped fallback signal
10. rest-day difference and 14-day fixture congestion
11. public fair market probabilities when Football-Data publishes upcoming EPL odds
12. the holdout-trained ensemble only when current market evidence exists, matching the regime in which it was validated

The final 1X2 probabilities are converted back into a coherent score distribution, keeping correct score, BTTS and Over/Under consistent with the same forecast.

## Holdout validation

The currently stored trained ensemble used a time-ordered split:

- 2023/24 + 2024/25: coefficient fitting
- first half of 2025/26: probability calibration
- second half of 2025/26: later holdout

On the 190-match holdout:

| Model | Accuracy | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| Trained ensemble | 44.2% | **0.633** | **1.047** |
| Public market benchmark | **45.8%** | 0.635 | 1.050 |
| Structural model | 43.2% | 0.662 | 1.089 |

The ensemble is used for probability quality when market evidence exists. The no-market engine remains a dynamic score model rather than forcing market-trained coefficients onto a different data regime.

## Forecast locking

Predictions may update before kickoff as public results, xG or market information changes. At kickoff the stored forecast becomes immutable.

Finished matches are graded against that frozen prediction, so future information cannot leak backward into historical results.

## Automatic refresh

`.github/workflows/refresh-results.yml` runs every two hours and can also be run manually.

It:

1. keeps the existing 380-match schedule
2. checks the public 2026/27 Football-Data CSV for new results/statistics
3. checks the public Football-Data upcoming-fixtures CSV for EPL odds
4. checks Understat's public 2026/27 EPL page for xG/xGA
5. preserves locked pre-match evidence
6. rebuilds every future prediction
7. commits `data/live.js` only when data changed

No secrets are configured or required.

## Weekly model training

The `Train prediction ensemble` workflow uses historical Football-Data CSV files and produces `data/trained_model.json` plus `data/training_status.json`.

The model is never activated without a valid time-ordered evaluation record.

## Manual context

`data/context.json` can hold a small, timestamped manual adjustment if a major piece of public pre-match information is verified manually, such as a confirmed manager change or extraordinary team news. It is intentionally empty by default.

Normal adjustments should stay close to 1.00 and must have existed before kickoff.

## Run locally

```bash
python3 -m http.server 8000
```

Refresh the data snapshot with:

```bash
python scripts/refresh_snapshot.py
```

## Important

This is an independent forecasting project. Predictions are estimates, not guarantees or betting advice.
