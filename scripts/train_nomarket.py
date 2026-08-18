#!/usr/bin/env python3
"""Train a no-market EPL ensemble and promote it only if it improves unseen probabilities."""
from __future__ import annotations
import json,math
from datetime import datetime,timezone
from pathlib import Path
import train_ensemble as t
from prediction_core import ROOT,softmax

OUTPUT=ROOT/'data'/'trained_nomarket.json'
FEATURES=['base_home','base_draw','base_away','form_ppm_diff','gdpg_diff','sotdiff_diff','rest_diff']

def standardize(rows):
    means={};scales={}
    for name in FEATURES:
        vals=[float(r['x'].get(name,0)) for r in rows];m=sum(vals)/len(vals);v=sum((x-m)**2 for x in vals)/max(len(vals)-1,1)
        means[name]=m;scales[name]=max(math.sqrt(v),1e-6)
    return means,scales

def zrow(row,means,scales):return [(float(row['x'].get(n,0))-means[n])/scales[n] for n in FEATURES]

def fit(rows,means,scales,epochs=650,lr=.10,l2=.04):
    d=len(FEATURES);W=[[0.0]*d for _ in range(3)];b=[0.0]*3;zs=[zrow(r,means,scales) for r in rows];ys=[r['y'] for r in rows];N=len(rows)
    for epoch in range(epochs):
        gW=[[0.0]*d for _ in range(3)];gb=[0.0]*3
        for z,y in zip(zs,ys):
            p=softmax([b[c]+sum(W[c][j]*z[j] for j in range(d)) for c in range(3)])
            for c in range(3):
                e=p[c]-(1 if y==c else 0);gb[c]+=e
                for j in range(d):gW[c][j]+=e*z[j]
        rate=lr/(1+epoch/500)
        for c in range(3):
            b[c]-=rate*gb[c]/N
            for j in range(d):W[c][j]-=rate*(gW[c][j]/N+l2*W[c][j])
    return W,b

def probs(row,W,b,means,scales,temp=1.0):
    z=zrow(row,means,scales);p=softmax([(b[c]+sum(W[c][j]*z[j] for j in range(len(z))))/temp for c in range(3)])
    return {'home':p[0],'draw':p[1],'away':p[2]}

def choose_temperature(rows,W,b,means,scales):
    best=(1e9,1.0)
    for i in range(71):
        temp=.50+i*.02;score=t.metrics(rows,lambda r:probs(r,W,b,means,scales,temp)).get('logLoss',1e9)
        if score<best[0]:best=(score,temp)
    return best[1]

def main():
    data=t.build_dataset(t.load_rows());train=[r for r in data if r['season'] in ('2023/24','2024/25')];season=[r for r in data if r['season']=='2025/26'];split=len(season)//2;cal,hold=season[:split],season[split:]
    if len(train)<500 or len(hold)<100:raise RuntimeError(f'Insufficient data train={len(train)} holdout={len(hold)}')
    means,scales=standardize(train);W,b=fit(train,means,scales);temp=choose_temperature(cal,W,b,means,scales)
    ensemble=t.metrics(hold,lambda r:probs(r,W,b,means,scales,temp));structural=t.metrics(hold,lambda r:r['base'])
    improved=(ensemble.get('brier',99)<structural.get('brier',99) and ensemble.get('logLoss',99)<structural.get('logLoss',99))
    payload={'enabled':bool(improved),'version':'4.0-nomarket','trainer':'no-market-softmax-v1','trainedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'trainingSeasons':['2023/24','2024/25'],'calibrationWindow':'first half 2025/26','holdoutWindow':'second half 2025/26','trainingSamples':len(train),'calibrationSamples':len(cal),
        'features':FEATURES,'means':means,'scales':scales,'coefficients':W,'intercepts':b,'temperature':temp,'holdout':{'ensemble':ensemble,'structural':structural},
        'promotionRule':'Enabled only when both Brier score and log loss beat the structural model on the untouched holdout.',
        'notes':'No bookmaker, injury, lineup, API-key, or future-match information is used.'}
    OUTPUT.write_text(json.dumps(payload,indent=2),encoding='utf-8');print(json.dumps(payload['holdout'],indent=2));print('promoted=',improved);return 0
if __name__=='__main__':raise SystemExit(main())
