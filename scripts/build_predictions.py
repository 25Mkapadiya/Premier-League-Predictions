#!/usr/bin/env python3
"""Build and freeze no-key pre-match predictions on every EPL fixture."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from prediction_core import ROOT,load_context,load_js_assignment,parse_iso,write_js_assignment
from prediction_runtime import predict_fixture

MODEL_PATH=ROOT/'data'/'model.js'
LIVE_PATH=ROOT/'data'/'live.js'
MARKET_MODEL_PATH=ROOT/'data'/'trained_model.json'
NOMARKET_MODEL_PATH=ROOT/'data'/'trained_nomarket.json'

def load_model(path):
    if not path.exists():return {'enabled':False}
    try:return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:return {'enabled':False}

def fixture_key(f):return f"{f.get('home')}__{f.get('away')}__{f.get('matchweek')}"

def main(prior_live=None):
    model=load_js_assignment(MODEL_PATH,'window.MODEL_DATA = ')
    live=load_js_assignment(LIVE_PATH,'window.LIVE_DATA = ')
    market_model=load_model(MARKET_MODEL_PATH)
    nomarket_model=load_model(NOMARKET_MODEL_PATH)
    context=load_context();now=datetime.now(timezone.utc)
    prior=prior_live or {};old={fixture_key(f):f for f in prior.get('fixtures',[])}
    generated=preserved=locked=retro=market_count=nomarket_count=0
    for f in live.get('fixtures',[]):
        prev=old.get(fixture_key(f)) or {};oldp=prev.get('prediction');ko=parse_iso(f.get('kickoff'))
        started=f.get('status') in ('live','final') or (ko is not None and ko<=now)
        if started and oldp:
            f['prediction']=oldp;f['predictionLocked']=True;f['predictionLockedAt']=prev.get('predictionLockedAt') or f.get('kickoff');preserved+=1;locked+=1;continue
        p=predict_fixture(model,live,f,market_model=market_model,nomarket_model=nomarket_model,context=context)
        if p.get('engine')=='trained public-market ensemble':market_count+=1
        if p.get('engine')=='trained no-market ensemble':nomarket_count+=1
        if started:
            p['retroGenerated']=True;retro+=1;f['predictionLocked']=True;f['predictionLockedAt']=f.get('kickoff');locked+=1
        else:f['predictionLocked']=False
        f['prediction']=p;generated+=1
    live.setdefault('meta',{})['predictionEngine']={
        'version':'4.1','mode':'no API / no secrets','generatedAt':now.isoformat().replace('+00:00','Z'),
        'marketModelEnabled':bool(market_model.get('enabled')),'marketModelHoldout':market_model.get('holdout'),
        'noMarketModelEnabled':bool(nomarket_model.get('enabled')),'noMarketModelHoldout':nomarket_model.get('holdout'),
        'marketModelFixtures':market_count,'noMarketModelFixtures':nomarket_count,'generated':generated,
        'preservedLocked':preserved,'locked':locked,'retroGenerated':retro,
        'policy':'Public files/pages only. Each learned model is used only in the feature regime where it beat the baseline on a later holdout. Forecasts freeze at kickoff.'
    }
    write_js_assignment(LIVE_PATH,'window.LIVE_DATA = ',live)
    print(f'No-key predictions: generated={generated}, preserved={preserved}, locked={locked}, retro={retro}, marketModel={market_count}, noMarketModel={nomarket_count}')
    return 0
if __name__=='__main__':raise SystemExit(main())
