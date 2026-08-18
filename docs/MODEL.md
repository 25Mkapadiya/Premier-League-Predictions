# Prediction Model

## Goal

The app is designed to produce useful **probabilities**, not pretend that football matches can be predicted with certainty. The headline score is the rounded expected-goals forecast, while the home/draw/away percentages are the more important output.

## Data snapshot

Model snapshot date: **August 17, 2026**, before the opening 2026/27 Premier League match.

Primary inputs:

- 2023/24 Premier League results
- 2024/25 Premier League results
- 2025/26 Premier League results
- 2025/26 Championship results for the promoted-club translation
- Official 2026/27 Premier League fixtures for the opening matchweeks shown in the interface

Historical result CSVs come from Football-Data.co.uk. The fixture schedule comes from the Premier League's official fixture release.

## 1. Venue-adjusted attack and defense

For each returning Premier League team, home attack, home defense, away attack, and away defense are estimated separately.

Conceptually:

```text
home_attack = team_home_goals / league_home_goals
home_defense = team_home_goals_conceded / league_away_goals
away_attack = team_away_goals / league_away_goals
away_defense = team_away_goals_conceded / league_home_goals
```

Each factor is shrunk toward `1.0` with prior pseudo-matches so one unusual run does not dominate the forecast. For clubs present in both 2024/25 and 2025/26, the newer season receives most of the weight.

## 2. Expected goals

The initial expected scoring rates are:

```text
home_lambda = league_home_goal_rate × home_team_home_attack × away_team_away_defense
away_lambda = league_away_goal_rate × away_team_away_attack × home_team_home_defense
```

These lambdas are the foundation for the score distribution.

## 3. Elo strength adjustment

A separate Elo process runs through three Premier League seasons. Ratings move after every match based on:

- result
- opponent strength
- home advantage
- margin of victory

The Elo difference applies a modest multiplicative adjustment to the scoring lambdas. It is deliberately a secondary signal rather than a replacement for the scoring model.

## 4. Promoted-team translation

A Championship champion should not be assigned Premier League attack and defense factors as though the divisions are equivalent.

For Coventry City, Ipswich Town, and Hull City, Championship performance is translated around empirically weaker promoted-team Premier League baselines, while preserving a smaller amount of each club's relative Championship strength. This prevents the common modeling error of overrating dominant promoted teams.

## 5. Dixon-Coles low-score correction

Independent Poisson goal models tend to misestimate a few common low-scoring football outcomes. A Dixon-Coles-style correction redistributes probability around:

- 0-0
- 1-0
- 0-1
- 1-1

The full score grid is normalized after the correction, then summed into home-win, draw, and away-win probabilities.

## 6. Displayed score

The large score shown in the app is the **rounded expected-goals score**, not a claim that the exact result is the single most likely event.

For example, if the model estimates `2.51` expected home goals and `1.02` away goals, the UI shows `3:1` while the probability bars remain the primary forecast.

## Backtest

A rolling pre-match simulation over all 380 matches of the 2025/26 Premier League season was used as a sanity check. Before each fixture date, team metrics only included matches already completed at that point.

Results:

| Metric | Result |
| --- | ---: |
| Top home/draw/away accuracy | 48.7% |
| Naive always-home baseline | 42.6% |
| Multiclass Brier score | 0.628 |
| Multiclass log loss | 1.042 |

A 3-way outcome hit rate should not be interpreted like binary accuracy. Draws make football prediction materially harder than a two-outcome classification problem.

## Limitations

The preseason snapshot does not yet include live injury reports, starting-lineup probabilities, summer transfer valuations, or current betting-market odds. Those can materially move a match forecast, especially near kickoff.

The model should therefore be read as a transparent statistical baseline rather than a promise of betting profitability.
