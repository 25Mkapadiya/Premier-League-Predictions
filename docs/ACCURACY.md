# Accuracy Architecture — No-API v4

The engine is built around one rule: **only information that existed before kickoff may affect a forecast**.

## Why the project no longer depends on APIs

The production path now uses public files and public web pages only. This removes credential failures, free-tier limits and secret management from the model's critical path.

The tradeoff is that public sources may update less frequently than commercial feeds. The model handles that explicitly by showing data completeness and falling back to its structural/dynamic layer rather than guessing.

## Statistical stack

### 1. Structural score prior

Venue attack/defense factors, Elo, home advantage, Poisson scoring and Dixon-Coles correction create the preseason/long-run score distribution.

### 2. Dynamic recent form

The last ten completed matches receive exponentially declining weight. Performance is measured relative to what the structural model expected against those opponents.

When real xG is present, xG/xGA replaces final goals inside the residual calculation. When xG is unavailable, the residual falls back to goals with stronger shrinkage.

### 3. Venue form

Recent home matches for the home club and recent away matches for the away club create a small additional adjustment after at least two relevant samples. This is deliberately weaker than the main form signal.

### 4. Current-season Elo

Each completed 2026/27 match updates a small Elo delta around the preseason rating. Opponent quality, home advantage and score margin affect the update. The delta is capped before it influences goal intensities.

### 5. Shots on target

Recent shots-on-target differential contributes only a small capped tilt. It is most useful when xG has not yet been attached and is never allowed to dominate team quality.

### 6. Rest and congestion

Rest-day difference and matches played in the prior 14 days apply small capped adjustments.

### 7. Public market information

If the Football-Data upcoming-fixture file contains EPL odds, the overround is removed before those prices are treated as probabilities.

The trained model is market-aware, so it is activated only when current market evidence exists. Without market evidence, production stays on the dynamic no-key model.

## Current trained holdout

The stored model was fit on 2023/24 + 2024/25, calibrated on the first half of 2025/26, and reported on the second half of 2025/26.

| Model | Accuracy | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|
| Trained ensemble | 44.2% | **0.633** | **1.047** |
| Market benchmark | **45.8%** | 0.635 | 1.050 |
| Structural model | 43.2% | 0.662 | 1.089 |

The ensemble improved probability quality versus both comparison layers on this holdout, although the market benchmark had the higher raw 1X2 hit rate.

## What is intentionally not overweighted

- head-to-head history
- possession percentage by itself
- tiny W/D/L streaks
- unverified injury rumors
- social-media sentiment
- arbitrary AI confidence numbers
- long-range current injury information

## Metrics that matter

The Results page reports:

- 1X2 hit rate
- Brier score
- log loss
- exact rounded-score hits
- frozen forecast count

Probability quality matters more than a single headline accuracy percentage because the site publishes probabilities, not only picks.
