# Accuracy Architecture

PL Forecast v3 follows one rule: **a forecast is only valid if every input existed before kickoff**.

## Active with no paid API key

The site works with the repository alone and uses:

- venue-adjusted Poisson scoring
- Elo team strength
- Dixon-Coles low-score correction
- recent opponent-adjusted performance once 2026/27 matches are completed
- FPL fixtures/results and team-strength signals
- a deliberately small player-availability proxy for fixtures no more than eight days away
- automatic filtering of players whose availability news shows they have already left the club
- home/away rest difference and 14-day fixture congestion
- Football-Data shots / shots-on-target once the current-season results CSV is published
- Football-Data's free weekly upcoming-fixture odds when EPL rows are present

Long-range matches do **not** inherit today's injury list. They are re-enriched as kickoff approaches.

## Optional production enrichments

### `ODDS_API_KEY`
Adds multi-bookmaker EPL 1X2 consensus from The Odds API. Every bookmaker's margin is removed before taking a median fair probability. The final pre-kickoff market snapshot is preserved after the event leaves the live odds feed.

### `SPORTMONKS_API_TOKEN`
Adds team xG to recent completed fixtures. The recent-performance layer prefers real xG over final goals when xG exists, while retaining shrinkage and caps.

### `API_FOOTBALL_KEY`
Adds sourced near-kickoff injury lists and confirmed starting lineups. Raw injury counts are not converted into arbitrary penalties. The context is stored for auditing and future player-impact modeling.

## Trained market-aware ensemble

`Train prediction ensemble` builds a chronological historical dataset:

- 2022/23: state warm-up only
- 2023/24 + 2024/25: coefficient fitting (760 matches)
- first half 2025/26: temperature calibration (190 matches)
- second half 2025/26: untouched holdout (190 matches)

The first successful v3 holdout produced:

| Model | 1X2 accuracy | Brier | Log loss |
| --- | ---: | ---: | ---: |
| v3 ensemble | 44.2% | **0.633** | **1.047** |
| historical market benchmark | **45.8%** | 0.635 | 1.050 |
| rolling structural benchmark | 43.2% | 0.662 | 1.089 |

The ensemble's raw winner hit rate did not beat the historical market on this holdout, so the project does not claim that it did. It did slightly improve the two probability-quality metrics used for calibration.

Every historical training row had market probabilities available. For that reason, production only uses the learned ensemble when the live fixture also has a fair market snapshot. Without market evidence the site stays on the dynamic football model rather than extrapolating the learned coefficients outside their tested regime.

`data/training_status.json` records every training run's success/failure and latest holdout.

## Coherent score markets

After a final 1X2 probability is chosen, the engine searches for home/away scoring lambdas that closely reproduce that target while penalizing unnecessary movement in total expected goals. Correct score, expected score, BTTS, totals and 1X2 therefore remain tied to one score distribution.

## Forecast locking

`build_predictions.py` stores a prediction directly on every fixture in `data/live.js`.

Before kickoff the prediction may change as valid new evidence arrives. At kickoff it becomes immutable. Later result refreshes grade the frozen forecast instead of recalculating with future information. If the first snapshot is created only after kickoff, it is marked `retroGenerated` and is distinguishable from a genuine pre-match forecast.

## Metrics

The Results page reports 1X2 hit rate, Brier score, log loss, rounded score hits and the number of frozen forecasts. Brier score and log loss are the primary probability-quality measures.

## Deliberately low-weight or excluded

- head-to-head history
- raw possession percentage by itself
- tiny W/D/L streaks
- raw injury counts without player impact
- social-media sentiment
- arbitrary AI confidence labels

A new feature should enter the production model only after it improves unseen-match probability quality.
