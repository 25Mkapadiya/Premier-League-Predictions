# Accuracy Architecture

PL Forecast v3 is designed around one rule: **a forecast is only valid if every input existed before kickoff**.

## Active with no paid API key

The site works with the current repository alone and uses:

- venue-adjusted Poisson scoring
- Elo team strength
- Dixon-Coles low-score correction
- recent opponent-adjusted goals/form
- current Premier League match results
- shots / shots on target when Football-Data has them
- home/away rest difference and fixture congestion
- a small FPL availability proxy capped so it cannot dominate team strength
- historical/promoted-team priors already embedded in `data/model.js`

The availability proxy is intentionally weak. Fantasy price and player status are not treated as a complete player-impact model.

## Optional production enrichments

### `ODDS_API_KEY`

Adds multi-bookmaker EPL 1X2 consensus from The Odds API. Each bookmaker's overround is removed before the median fair probability is calculated. The last pre-kickoff market snapshot is preserved after the event disappears from the live odds feed.

### `SPORTMONKS_API_TOKEN`

Adds team xG to recent completed fixtures. The dynamic form layer prefers real xG over final goals when xG exists, but the influence is shrunk and capped.

### `API_FOOTBALL_KEY`

Adds near-kickoff injury lists and confirmed starting lineups. Raw injury counts are **not** converted into arbitrary probability penalties. The context is stored for auditing and for a future learned player-impact layer.

## Trained ensemble

`Train prediction ensemble` downloads four historical Premier League seasons from Football-Data and builds a time-ordered dataset.

- 2022/23: state warm-up only
- 2023/24 + 2024/25: coefficient fitting
- first half 2025/26: probability temperature calibration
- second half 2025/26: untouched holdout

Features include structural probabilities, fair market probabilities, recent points/form, goal difference, shots-on-target difference and rest difference.

The trainer outputs `data/trained_model.json`. Production only activates the learned layer when the file is valid and contains enough training samples.

## Coherent markets

A learned or market-calibrated 1X2 forecast can otherwise conflict with an old Poisson score grid. The production engine therefore realigns the home/away goal lambdas to the final 1X2 target while penalizing unnecessary changes to total expected goals.

That keeps expected score, correct score, BTTS, totals and 1X2 tied to one final score distribution.

## Forecast locking

`build_predictions.py` stores a prediction directly on each fixture in `data/live.js`.

Before kickoff, that prediction may change as fresh form, market or lineup evidence arrives. At kickoff it becomes immutable. Later result refreshes grade the frozen forecast instead of recalculating with future information.

If the site is first run only after a match has already started, the generated forecast is marked `retroGenerated` so it is not confused with a true pre-match snapshot.

## Metrics

The Results page reports 1X2 hit rate, Brier score, log loss, rounded score hits and the number of genuinely frozen forecasts.

Brier score and log loss matter more than raw hit rate when judging probability quality.

## What is deliberately not over-weighted

- head-to-head history
- raw possession percentage
- tiny winning/losing streaks
- injury counts without player-impact estimates
- social-media sentiment
- arbitrary AI confidence labels

A feature should enter the production model only after it improves unseen-match probability quality.
