#!/usr/bin/env python3
"""Attach a pre-match prediction snapshot to every Premier League fixture in data/live.js."""
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
    model=load_js_assignment(MODEL_PATH,'window.MODEL_DATA = ');live=load_js_assignment(LIVE_PATH,'window.LIVE_DATA = ');trained=load_trained();context=load_context();now=datetime.now(timezone.utc);prior=prior_live or {};old={fixture_key(f):f for f in prior.get('fixtures',[])};generated=preserved=locked=retro=0
    for f in live.get('fixtures',[]):
        prev=old.get(fixture_key(f)) or {};oldp=prev.get('prediction');ko=parse_iso(f.get('kickoff'));started=f.get('status') in ('live','final') or (ko is not None and ko<=now)
        if started and oldp:
            f['prediction']=oldp;f['predictionLocked']=True;f['predictionLockedAt']=prev.get('predictionLockedAt') or f.get('kickoff');preserved+=1;locked+=1;continue
        p=predict_fixture(model,live,f,trained=trained,context=context)
        if started:p['retroGenerated']=True;retro+=1;f['predictionLocked']=True;f['predictionLockedAt']=f.get('kickoff');locked+=1
        else:f['predictionLocked']=False
        f['prediction']=p;generated+=1
    live.setdefault('meta',{})['predictionEngine']={'version':'3.0','generatedAt':now.isoformat().replace('+00:00','Z'),'trainedModelEnabled':bool(trained.get('enabled')),'trainedModelHoldout':trained.get('holdout'),'generated':generated,'preservedLocked':preserved,'locked':locked,'retroGenerated':retro,'policy':'Forecasts freeze at kickoff. Finished matches are never recalculated with future information.'}
    write_js_assignment(LIVE_PATH,'window.LIVE_DATA = ',live);print(f'Predictions: generated={generated}, preserved={preserved}, locked={locked}, retro={retro}, trained={bool(trained.get("enabled"))}');return 0
if __name__=='__main__':raise SystemExit(main())
