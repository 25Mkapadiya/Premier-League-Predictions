#!/usr/bin/env python3
"""Fast activation wrapper for the same leakage-safe ensemble trainer."""
from __future__ import annotations
import json
from datetime import datetime,timezone
import train_ensemble as t

def main():
    data=t.build_dataset(t.load_rows())
    train=[r for r in data if r['season'] in ('2023/24','2024/25')]
    season=[r for r in data if r['season']=='2025/26']
    split=len(season)//2;cal,hold=season[:split],season[split:]
    if len(train)<500 or len(hold)<100:raise RuntimeError(f'Insufficient data train={len(train)} holdout={len(hold)}')
    means,scales=t.standardize(train)
    # Standardized features + regularization converge quickly enough here that 520
    # full-batch passes are ample for activation and much friendlier to scheduled CI.
    W,b=t.fit(train,means,scales,epochs=520,lr=.10,l2=.035)
    temp=t.temperature(cal,W,b,means,scales)
    ensemble=t.metrics(hold,lambda r:t.probs(r,W,b,means,scales,temp))
    structural=t.metrics(hold,lambda r:r['base'])
    market_rows=[r for r in hold if r['x']['market_available']>0]
    market=t.metrics(market_rows,lambda r:{'home':r['x']['market_home'],'draw':r['x']['market_draw'],'away':r['x']['market_away']})
    payload={'enabled':True,'version':'3.0','trainer':'fast-softmax-v1','trainedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'trainingSeasons':['2023/24','2024/25'],'calibrationWindow':'first half 2025/26','holdoutWindow':'second half 2025/26','trainingSamples':len(train),'calibrationSamples':len(cal),'features':t.FEATURES,'means':means,'scales':scales,'coefficients':W,'intercepts':b,'temperature':temp,'holdout':{'ensemble':ensemble,'structural':structural,'market':market},'notes':'Coefficient fitting and temperature selection never use the second-half 2025/26 holdout.'}
    t.OUTPUT.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload['holdout'],indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
