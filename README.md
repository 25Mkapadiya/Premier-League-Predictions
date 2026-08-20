# PL Forecast — Premier League Predictions

A dark 2026/27 Premier League forecasting dashboard built around a **no-API, no-secret prediction pipeline**. The site uses public downloadable football data, public xG when available, two holdout-gated learned models, and frozen pre-kickoff forecasts.

## No-key data stack

The production site does not require API keys.

- **Premier League schedule** — retained in the repository from the official 2026/27 fixture release
- **Football-Data.co.uk** — public CSV results, shots, shots on target, historical odds and upcoming fixture odds when EPL rows are published
- **Understat** — optional public EPL xG/xGA enrichment when its public league data is accessible
- **Repository model priors** — venue attack/defense, Elo and promoted-team translation from prior seasons

If a public source has not updated, the engine keeps the last safe snapshot and falls back to the strongest statistically validated layer it can support. It never invents missing inputs.

## Prediction engine v4.1

For each fixture the engine builds a dynamic football forecast from:

1. venue-adjusted attack and defense priors
2. Elo strength and home advantage
3. Poisson score probabilities
4. Dixon-Coles low-score correction
5. opponent-adjusted recent performance with time decay
6. separate recent home/away venue form
7. current-season Elo movement
8. xG/xGA residuals when public Understat data exists
9. shots-on-target form as a capped fallback signal
10. rest-day difference and 14-day fixture congestion

It then chooses the learned probability layer that matches the available evidence:

- **No public odds:** a dedicated no-market model trained only on structural, form, goal-difference, shots-on-target and rest features
- **Public odds available:** the stronger market-aware ensemble, using bookmaker-margin-free probabilities from Football-Data together with the football features

Both learned models are activated only after beating their comparison baseline on a later untouched holdout.

The final 1X2 probabilities are converted back into a coherent score distribution, keeping correct score, BTTS and Over/Under consistent with the same forecast.

## Holdout validation

Both models use the same time-ordered split:

- 2023/24 + 2024/25: coefficient fitting
- first half of 2025/26: probability calibration
- second half of 2025/26: untouched 190-match holdout

### No-market model

| Model | Accuracy | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| **No-market ensemble** | **43.7%** | **0.650** | **1.071** |
| Structural baseline | 43.2% | 0.662 | 1.089 |

### Market-aware model

| Model | Accuracy | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| **Market-aware ensemble** | 44.2% | **0.633** | **1.047** |
| Public market benchmark | **45.8%** | 0.635 | 1.050 |
| Structural baseline | 43.2% | 0.662 | 1.089 |

The market benchmark had the highest raw winner hit rate, while the ensemble produced slightly better probability calibration on this holdout.

## Forecast locking

Predictions may update before kickoff as public results, xG or odds information changes. At kickoff the stored forecast becomes immutable.

Finished matches are graded against that frozen prediction, so future information cannot leak backward into historical results.

## Automatic refresh

`.github/workflows/refresh-results.yml` runs **hourly** and can also be run manually.

It:

1. keeps the existing 380-match schedule
2. checks the public 2026/27 Football-Data CSV for new results/statistics
3. checks the public Football-Data upcoming-fixtures CSV for EPL odds
4. attempts public Understat xG enrichment
5. preserves locked pre-match evidence
6. rebuilds every future prediction
7. commits `data/live.js` only when data changed

No secrets are configured or required.

## Weekly model training

The `Train prediction ensemble` workflow retrains both learned models weekly from public historical Football-Data files:

- `data/trained_nomarket.json`
- `data/trained_model.json`
- `data/training_status.json`

Both are multinomial (softmax) logistic regressions fitted with **scikit-learn's `LogisticRegressionCV`** (`scripts/model_fit.py`), not a hand-rolled optimizer:

- Feature standardization uses scikit-learn's `StandardScaler`, which is robust to zero-variance features (a feature that never varies in training gets scale 1.0, not a divide-by-near-zero blow-up if it varies later in production).
- The L2 regularization strength is chosen by **time-respecting cross-validation** (`TimeSeriesSplit`) on the training split only — never guessed as a fixed constant, and never touching the calibration or holdout windows.
- Post-fit probability calibration (temperature scaling) is solved with `scipy.optimize.minimize_scalar` against the calibration window.

A no-market model is promoted only if it beats the structural baseline on **both Brier score and log loss** on the untouched holdout. Training dependencies (`numpy`, `scipy`, `scikit-learn`, pinned in `scripts/requirements-train.txt`) are only needed by the training workflow — serving predictions at request time uses the plain coefficients/intercepts/temperature exported to JSON and has no extra runtime dependency.

## My draft

The **My Draft** tab tracks players you drafted for a fantasy squad. It's still no-key: player stats come from the official Fantasy Premier League site's own public JSON endpoints (the same ones fantasy.premierleague.com's frontend calls), not a paid provider.

To use it, list your picks in `data/draft.json`:

```json
{
  "picks": [
    {"team": "Arsenal", "player": "Saka"},
    {"team": "Liverpool", "player": "Salah"}
  ]
}
```

`team` should match this project's team names (see `data/model.js`); `player` is matched fuzzily against FPL's player names, so a surname or FPL display name usually works. The `Refresh drafted player stats` workflow (`scripts/refresh_draft.py`) resolves each pick against the FPL API hourly, pulls real points/form/goals/assists/price, and cross-references `data/live.js` for that player's team's next fixture and this project's own win-probability forecast for it, writing the result to `data/draft_stats.js`. A pick that can't be matched (typo, wrong club, player not in the FPL data yet) shows up in the panel with the reason instead of failing silently.

## Manual context

`data/context.json` can hold a small, timestamped manual adjustment if a major piece of public pre-match information is independently verified, such as a confirmed manager change or extraordinary team news. It is intentionally empty by default.

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
