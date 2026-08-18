# Ensemble Framework — No-Key Production Path

The project no longer depends on authenticated football APIs. Production inputs are limited to public downloadable files, public league pages, repository priors, and optional manual context that is timestamped before kickoff.

The current hierarchy is:

1. structural Poisson + Elo + Dixon-Coles prior
2. time-decayed opponent-adjusted form
3. venue-specific recent form
4. current-season Elo movement
5. Understat xG/xGA when publicly available
6. Football-Data shots-on-target signal
7. rest and congestion
8. Football-Data public upcoming odds when EPL rows are published
9. calibrated historical ensemble only when market evidence exists

See [`ACCURACY.md`](ACCURACY.md) for the production methodology and holdout results.
