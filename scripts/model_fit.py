#!/usr/bin/env python3
"""Shared scikit-learn fitting utilities for the EPL 1X2 softmax ensembles.

Replaces a hand-rolled gradient-descent softmax classifier with scikit-learn's
LogisticRegressionCV (multinomial logistic regression). Two concrete benefits
over the old from-scratch trainer:

1. Regularization strength (C) is chosen by time-respecting cross-validation
   on the training split only, instead of a constant guessed once by hand.
2. Feature standardization uses scikit-learn's StandardScaler, which sets the
   scale of a zero-variance feature to 1.0 instead of the old code's 1e-6
   epsilon fallback -- the old fallback could blow up a live feature that is
   constant in training data (e.g. market availability) but not constant in
   production into an enormous, unstable z-score.

The fitted model is still exported as plain means/scales/coefficients/
intercepts/temperature so prediction_core.py (Python) and noapi-preload.js
(browser fallback) keep working unchanged -- only the fitting engine changed.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

LABELS = ('home', 'draw', 'away')  # class index 0/1/2, matches label() in train_ensemble.py


def _feature_matrix(rows, features):
    return np.array([[float(r['x'].get(name, 0.0)) for name in features] for r in rows], dtype=float)


def fit_softmax_model(train_rows, features, cv_splits=5, max_iter=5000):
    """Fit an L2-regularized multinomial logistic regression on train_rows.

    train_rows must already be in chronological order (as produced by
    build_dataset). Cross-validation for the regularization strength uses
    TimeSeriesSplit, so every validation fold is strictly later in time than
    the fold(s) it is scored against -- consistent with this project's rule
    that no feature may see information from the future.
    """
    X = _feature_matrix(train_rows, features)
    y = np.array([r['y'] for r in train_rows], dtype=int)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    n_splits = max(2, min(cv_splits, len(train_rows) // 150))
    cv = TimeSeriesSplit(n_splits=n_splits)

    model = LogisticRegressionCV(
        Cs=np.logspace(-2, 2, 25),
        cv=cv,
        l1_ratios=(0.0,),  # pure L2, same penalty family as the old trainer
        solver='lbfgs',
        max_iter=max_iter,
        scoring='neg_log_loss',
        use_legacy_attributes=False,
    )
    model.fit(Xs, y)

    means = {name: float(v) for name, v in zip(features, scaler.mean_)}
    scales = {name: float(v) for name, v in zip(features, scaler.scale_)}
    return {
        'means': means,
        'scales': scales,
        'coefficients': model.coef_.tolist(),
        'intercepts': model.intercept_.tolist(),
        'chosenC': float(np.ravel(model.C_)[0]),
        'cvFolds': n_splits,
    }


def softmax_probabilities(row, features, means, scales, coefficients, intercepts, temperature=1.0):
    z = np.array([(float(row['x'].get(n, 0.0)) - means[n]) / (scales[n] or 1.0) for n in features])
    logits = (np.asarray(intercepts, dtype=float) + np.asarray(coefficients, dtype=float) @ z)
    logits = logits / max(float(temperature), 1e-6)
    logits = logits - logits.max()
    exp = np.exp(logits)
    p = exp / exp.sum()
    return {'home': float(p[0]), 'draw': float(p[1]), 'away': float(p[2])}


def fit_temperature(cal_rows, features, means, scales, coefficients, intercepts, metrics_fn, bounds=(0.3, 3.0)):
    """Pick the temperature minimizing log loss on the calibration split via
    bounded scalar optimization (scipy), replacing a hand-rolled grid search."""
    def loss(temp):
        predict = lambda r: softmax_probabilities(r, features, means, scales, coefficients, intercepts, temp)
        return metrics_fn(cal_rows, predict)['logLoss']

    result = minimize_scalar(loss, bounds=bounds, method='bounded', options={'xatol': 1e-3})
    return float(result.x)
