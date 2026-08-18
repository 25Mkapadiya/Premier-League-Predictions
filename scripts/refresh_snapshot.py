#!/usr/bin/env python3
"""Refresh public no-key data, preserve pre-match evidence, and rebuild forecasts."""
from __future__ import annotations
import copy
from datetime import datetime,timezone
import build_predictions,refresh_results
from prediction_core import ROOT,load_js_assignment,write_js_assignment
LIVE=ROOT/'data'/'live.js'

def read_live():
    if not LIVE.exists():return {}
    try:return load_js_assignment(LIVE,'window.LIVE_DATA = ')
    except Exception:return {}
def fixture_key(f):return f"{f.get('home')}__{f.get('away')}__{f.get('matchweek')}"

def main():
    before=read_live();old={fixture_key(f):f for f in before.get('fixtures',[])}
    code=refresh_results.main()
    if code:return code
    after=read_live();preserved_market=preserved_xg=0
    for f in after.get('fixtures',[]):
        prev=old.get(fixture_key(f)) or {}
        if not f.get('odds') and prev.get('odds') and prev.get('predictionLocked'):
            f['odds']=copy.deepcopy(prev['odds']);f['odds']['preserved']=True;preserved_market+=1
        if not f.get('xg') and prev.get('xg'):
            f['xg']=copy.deepcopy(prev['xg']);preserved_xg+=1
    after.setdefault('meta',{})['preservation']={'marketFixtures':preserved_market,'xgFixtures':preserved_xg,'updated':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
    write_js_assignment(LIVE,'window.LIVE_DATA = ',after)
    return build_predictions.main(prior_live=before)

if __name__=='__main__':raise SystemExit(main())
