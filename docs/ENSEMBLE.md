# Ensemble Prediction Framework

This project does **not** attempt to reproduce proprietary algorithms from Forebet, SoccerVital, PredictZ or WinDrawWin. Their private model weights and training code are not public. The framework below is based on the signals those sites publicly expose or describe, combined with established football-modeling practices.

## What the reference sites suggest

### Forebet
Public pages emphasize mathematical probability, score forecasts, 1X2 percentages, trends, average goals and bookmaker coefficients. Forebet also describes Poisson/probability ideas and value-selection concepts.

**Useful idea for this project:** keep a full score-probability model as the structural core and show probabilities rather than only a tip.

### PredictZ
PredictZ presents correct-score predictions as a central output and derives related markets such as BTTS and Over/Under. It prominently surfaces recent records, home/away statistics, H2H and bookmaker odds.

**Useful idea:** one coherent score distribution should power 1X2, totals, BTTS and correct-score outputs so the markets do not contradict one another.

### WinDrawWin
WinDrawWin also anchors picks around exact scores, presents form and statistics, and communicates confidence tiers. It emphasizes updating predictions close to the latest completed matches.

**Useful idea:** make current form time-sensitive and expose signal strength, but do not present an arbitrary confidence number.

### SoccerVital
SoccerVital publicly lists league position, points situation, remaining fixtures, recent form, H2H, venue form, injuries, suspensions, rotation, tactics, congestion and motivation as relevant factors.

**Useful idea:** create an explicit pre-match context layer for player availability and fixture congestion, but keep it sourced, bounded and timestamped.

## Production ensemble

The browser model now has four layers.

### 1. Structural score model

The existing venue-adjusted Poisson + Elo + Dixon-Coles model remains the anchor. It is slow-moving and prevents a handful of recent matches from completely changing team quality.

### 2. Opponent-adjusted recent form

For each fixture, only matches completed **before kickoff** are eligible.

For the last eight team matches, the model compares actual goals scored/conceded with what the structural model expected in those fixtures:

```text
attack residual = (actual GF + smoothing) / (expected GF + smoothing)
defense residual = (actual GA + smoothing) / (expected GA + smoothing)
```

More recent matches receive exponentially greater weight. The aggregate residual is shrunk strongly toward `1.00`, so small samples cannot dominate.

This is better than a raw W-D-L streak because a 1-0 win over an elite opponent and a 1-0 win over a weak opponent should not carry identical information.

### 3. Optional bookmaker consensus

When `ODDS_API_KEY` is configured, the refresh job downloads EPL h2h/1X2 odds from multiple bookmakers.

For each bookmaker:

```text
raw implied p = 1 / decimal odds
fair p = raw implied p / sum(raw implied probabilities)
```

This removes that bookmaker's overround. The project then takes the median fair home/draw/away probability across available books.

The market does **not** replace the model. The current implementation uses a log-opinion pool with a conservative market weight of `0.35`.

That weight should be tuned by walk-forward validation, not by intuition.

### 4. Pre-match context

`data/context.js` provides bounded multipliers for confirmed, sourced information such as a major striker absence, goalkeeper absence, suspension or heavily rotated lineup.

Default values are exactly `1.00`. A missing injury feed does not silently become a guessed adjustment.

Recommended bounds are intentionally small:

- normal notable absence: roughly 0.97–1.03
- multiple important absences: roughly 0.94–1.06
- only exceptional, well-supported cases should go beyond that

The application hard-clamps the values to 0.70–1.30 as a safety guard, but production adjustments should normally be much tighter.

## Confidence / signal strength

Do not label the largest probability as “90% confidence.” The current signal label uses:

- magnitude of the top 1X2 probability
- separation from the second-highest outcome
- whether the structural/form forecast and bookmaker consensus agree
- data quality / availability

This creates labels such as `High signal`, `Strong lean`, `Moderate lean`, `Mixed signals`, and `Tight matchup`.

## Accuracy roadmap

### Priority 1 — calibrate the ensemble weights

Run walk-forward validation over multiple seasons. For every historical fixture, construct every feature using only data available before that kickoff.

Optimize for **log loss and Brier score first**, not raw accuracy. A model that says 55% and is well calibrated is more useful than an overconfident model that happens to pick a few more winners.

Suggested split:

- train/tune: 2023/24 and 2024/25
- untouched holdout: 2025/26
- then freeze weights before using 2026/27 results

Never tune on the same season used to report performance.

### Priority 2 — add expected-goals data

Goals are noisy. Replace or supplement raw goals in the recent-form residual with non-penalty xG for and against. Ideally use event-level xG from a provider with a stable API/license.

Useful features:

- rolling npxG for / against
- home/away npxG split
- shot quality conceded
- big-chance or post-shot xG if licensed
- opponent-adjusted xG residuals

### Priority 3 — player availability and projected lineups

Add a server-side provider such as API-Football or Sportmonks to the GitHub Action. Store only the prediction-relevant snapshot in `data/live.js` or `data/context.js`.

Potential features:

- starting XI availability
- goalkeeper change
- missing minutes/importance score by position
- suspended players
- likely rotation after European/cup fixtures

Do **not** use the confirmed lineup in a historical backtest if that lineup would not have been available at the prediction timestamp you are simulating.

### Priority 4 — fixture congestion and rest

Derive this directly from fixture dates, so no extra API is required:

- days since previous match
- matches in previous 7 / 14 days
- travel / European midweek flag
- rest-day difference between teams

Treat it as a small adjustment and validate whether it improves holdout calibration.

### Priority 5 — better market data

The current market consensus uses the median fair probability across books. Later upgrades can include:

- opening vs latest price movement
- sharper-book subset
- closing-line benchmark
- separate market blend weights by time-to-kickoff

For fair model evaluation, store the odds snapshot that existed **when the prediction was published**.

### Priority 6 — model diversity

Only after the data pipeline is leakage-safe, consider adding a second genuinely different model, for example:

- gradient-boosted trees on tabular pre-match features
- Bayesian dynamic Poisson
- score-driven bivariate count model

Then stack/calibrate the models on a validation period. Two versions of the same Poisson formula do not create much ensemble diversity.

## Monitoring during 2026/27

Store a prediction snapshot before kickoff. Track:

- 1X2 accuracy
- multiclass Brier score
- log loss
- calibration by probability bucket
- correct-score hit rate (secondary only)
- BTTS and O/U Brier scores
- performance by confidence tier
- structural-only vs ensemble delta
- market-only vs ensemble delta

If the ensemble does not outperform the structural-only baseline on proper scoring rules over a meaningful sample, reduce or remove the new layer.
