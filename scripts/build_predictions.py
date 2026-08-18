#!/usr/bin/env python3
"""Build and freeze no-key pre-match predictions on every EPL fixture."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from prediction_core import ROOT,load_context,load_js_assignment,parse_iso,predict_fixture,write_js_assignment
MODEL_PATH=ROOT/'data'/'model.js';LIVE_PATH=ROOT/'data'/'live.js';TRAINED_PATH=ROOT/'data'/'trained_model.json'

def load_trained():
    if not TRAINED_PATH.exists():return {'enabled':False}
    try:return json.loads(TRAINED_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError:return {'enabled':False}

def fixture_key(f):return f"{f.get('home')}__{f.get('away')}__{f.get('matchweek')}"

def main(prior_live=None):
    model=load_js_assignment(MODEL_PATH,'window.MODEL_DATA = ');live=load_js_assignment(LIVE_PATH,'window.LIVE_DATA = ');trained=load_trained();context=load_context();now=datetime.now(timezone.utc)
    prior=prior_live or {};old={fixture_key(f):f for f in prior.get('fixtures',[])};generated=preserved=locked=retro=trained_count=0
    for f in live.get('fixtures',[]):
        prev=old.get(fixture_key(f)) or {};oldp=prev.get('prediction');ko=parse_iso(f.get('kickoff'));started=f.get('status') in ('live','final') or (ko is not None and ko<=now)
        if started and oldp:
            f['prediction']=oldp;f['predictionLocked']=True;f['predictionLockedAt']=prev.get('predictionLockedAt') or f.get('kickoff');preserved+=1;locked+=1;continue
        p=predict_fixture(model,live,f,trained=trained,context=context)
        if p.get('engine')=='no-key trained ensemble':trained_count+=1
        if started:p['retroGenerated']=True;retro+=1;f['predictionLocked']=True;f['predictionLockedAt']=f.get('kickoff');locked+=1
        else:f['predictionLocked']=False
        f['prediction']=p;generated+=1
    live.setdefault('meta',{})['predictionEngine']={'version':'4.0','mode':'no API / no secrets','generatedAt':now.isoformat().replace('+00:00','Z'),
        'trainedModelEnabled':bool(trained.get('enabled')),'trainedModelHoldout':trained.get('holdout'),'trainedFixtures':trained_count,'generated':generated,
        'preservedLocked':preserved,'locked':locked,'retroGenerated':retro,
        'policy':'Public files/pages only. Forecasts freeze at kickoff and finished matches are never recalculated with future evidence.'}
    write_js_assignment(LIVE_PATH,'window.LIVE_DATA = ',live)
    print(f'No-key predictions: generated={generated}, preserved={preserved}, locked={locked}, retro={retro}, trained={trained_count}')
    return 0
if __name__=='__main__':raise SystemExit(main())
