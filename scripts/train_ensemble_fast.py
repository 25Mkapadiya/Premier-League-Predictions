#!/usr/bin/env python3
"""CI entry point for the market-aware ensemble trainer.

Historically this ran a reduced-epoch variant of the hand-rolled gradient
descent trainer to keep scheduled CI runs quick. Now that fitting uses
scikit-learn's LogisticRegressionCV (which converges in a fraction of a
second on this dataset size), that split is no longer needed -- this just
runs the same trainer as train_ensemble.py.
"""
from __future__ import annotations
import train_ensemble as t

def main():
    return t.main()

if __name__=='__main__':raise SystemExit(main())
