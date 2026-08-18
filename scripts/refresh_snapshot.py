#!/usr/bin/env python3
"""Refresh live data, enrich it, preserve pre-match evidence, then build predictions."""
from __future__ import annotations
import copy
from datetime import datetime,timezone
import build_predictions,external_enrichment,refresh_results
from prediction_core import ROOT,load_js_assignment,write_js_assignment
LIVE=ROOT/'data'/'live.js'
def read_live():
    if not LIVE.exists():return {}
    try:return load_js_assignment(LIVE,'window.LIVE_DATA = ')
    except Exception:return {}
def fixture_key(f):return f"{f.get('home')}__{f.get('away')}__{f.get('matchweek')}"
def main():
    before=read_live();old={fixture_key(f):f for f in before.get('fixtures',[])};code=refresh_results.main()
    if code:return code
    after=read_live();after.setdefault('meta',{})['enrichment']=external_enrichment.enrich(after.get('fixtures',[]));po=pc=0
    for f in after.get('fixtures',[]):
        prev=old.get(fixture_key(f)) or {}
        if not f.get('odds') and prev.get('odds'):f['odds']=copy.deepcopy(prev['odds']);f['odds']['preserved']=True;po+=1
        if not f.get('apiContext') and prev.get('apiContext'):f['apiContext']=copy.deepcopy(prev['apiContext']);f['apiContext']['preserved']=True;pc+=1
        if not f.get('xg') and prev.get('xg'):f['xg']=copy.deepcopy(prev['xg'])
    after['meta']['preservation']={'oddsFixtures':po,'contextFixtures':pc,'updated':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')};write_js_assignment(LIVE,'window.LIVE_DATA = ',after);return build_predictions.main(prior_live=before)
if __name__=='__main__':raise SystemExit(main())
