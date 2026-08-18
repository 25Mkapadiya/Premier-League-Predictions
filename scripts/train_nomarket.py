#!/usr/bin/env python3
"""Train a no-market EPL ensemble and promote it only if it improves unseen probabilities."""
from __future__ import annotations
import json
from datetime import datetime,timezone
import train_ensemble as t
from prediction_core import ROOT
from model_fit import fit_softmax_model,fit_temperature,softmax_probabilities

OUTPUT=ROOT/'data'/'trained_nomarket.json'
FEATURES=['base_home','base_draw','base_away','form_ppm_diff','gdpg_diff','sotdiff_diff','rest_diff']

def probs(row,W,b,means,scales,temp=1.0):
    return softmax_probabilities(row,FEATURES,means,scales,W,b,temp)

def main():
    data=t.build_dataset(t.load_rows());train=[r for r in data if r['season'] in ('2023/24','2024/25')];season=[r for r in data if r['season']=='2025/26'];split=len(season)//2;cal,hold=season[:split],season[split:]
    if len(train)<500 or len(hold)<100:raise RuntimeError(f'Insufficient data train={len(train)} holdout={len(hold)}')
    fitted=fit_softmax_model(train,FEATURES);means,scales,W,b=fitted['means'],fitted['scales'],fitted['coefficients'],fitted['intercepts']
    temp=fit_temperature(cal,FEATURES,means,scales,W,b,t.metrics)
    ensemble=t.metrics(hold,lambda r:probs(r,W,b,means,scales,temp));structural=t.metrics(hold,lambda r:r['base'])
    improved=(ensemble.get('brier',99)<structural.get('brier',99) and ensemble.get('logLoss',99)<structural.get('logLoss',99))
    payload={'enabled':bool(improved),'version':'4.0-nomarket','trainer':'sklearn-logistic-regression-cv','trainedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'trainingSeasons':['2023/24','2024/25'],'calibrationWindow':'first half 2025/26','holdoutWindow':'second half 2025/26','trainingSamples':len(train),'calibrationSamples':len(cal),
        'features':FEATURES,'means':means,'scales':scales,'coefficients':W,'intercepts':b,'temperature':temp,
        'regularization':{'chosenC':fitted['chosenC'],'cvFolds':fitted['cvFolds'],'method':'LogisticRegressionCV with TimeSeriesSplit, scikit-learn'},
        'holdout':{'ensemble':ensemble,'structural':structural},
        'promotionRule':'Enabled only when both Brier score and log loss beat the structural model on the untouched holdout.',
        'notes':'No bookmaker, injury, lineup, API-key, or future-match information is used.'}
    OUTPUT.write_text(json.dumps(payload,indent=2),encoding='utf-8');print(json.dumps(payload['holdout'],indent=2));print('promoted=',improved);return 0
if __name__=='__main__':raise SystemExit(main())
