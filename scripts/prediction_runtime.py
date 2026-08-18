#!/usr/bin/env python3
"""Production probability layer that applies only holdout-validated learned models."""
from __future__ import annotations
from datetime import datetime,timezone
from prediction_core import align_lambdas,clamp,fair_market,predict_fixture as dynamic_predict,trained_probabilities


def validated_features(base,market,recent,rest_diff):
    home=recent.get('home') or {};away=recent.get('away') or {};m=market or base
    return {
        'base_home':float(base['home']),'base_draw':float(base['draw']),'base_away':float(base['away']),
        'market_home':float(m['home']),'market_draw':float(m['draw']),'market_away':float(m['away']),'market_available':1 if market else 0,
        'form_ppm_diff':clamp(float(home.get('ppm',1.35))-float(away.get('ppm',1.35)),-3,3),
        'gdpg_diff':clamp(float(home.get('gdpg',0))-float(away.get('gdpg',0)),-4,4),
        'sotdiff_diff':clamp(float(home.get('sotDiff',0))-float(away.get('sotDiff',0)),-10,10),
        'rest_diff':clamp(float(rest_diff or 0),-7,7),'availability_diff':0.0,
    }


def predict_fixture(model,live,fixture,market_model=None,nomarket_model=None,context=None):
    # First build the football-only dynamic score model. Passing no learned model
    # prevents a learned layer from being applied with the wrong feature definition.
    out=dynamic_predict(model,live,fixture,trained=None,context=context)
    components=out.get('components') or {};base=components.get('structural') or {'home':out['homeWin'],'draw':out['draw'],'away':out['awayWin']}
    market=fair_market(fixture.get('odds'));recent=components.get('recent') or {};rest=(components.get('rest') or {}).get('difference',0)
    features=validated_features(base,market,recent,rest)
    chosen=market_model if market else nomarket_model
    learned=trained_probabilities(chosen,features) if chosen and chosen.get('enabled') else None
    if not learned:
        out['validatedFeatures']=features
        out['learnedEligibility']='waiting for validated model' if not chosen else 'model not promoted'
        return out

    params=model['params'];aligned=align_lambdas(float(out['homeXg']),float(out['awayXg']),learned,params.get('rho',-.06),params.get('maxGoals',8))
    out.update({
        'version':'4.1','engine':'trained public-market ensemble' if market else 'trained no-market ensemble',
        'asOf':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'homeWin':round(aligned['home'],6),'draw':round(aligned['draw'],6),'awayWin':round(aligned['away'],6),
        'homeXg':round(aligned['homeXg'],4),'awayXg':round(aligned['awayXg'],4),
        'over25':round(aligned['over25'],6),'under25':round(aligned['under25'],6),
        'btts':round(aligned['btts'],6),'noBtts':round(aligned['noBtts'],6),
        'score':aligned['score'],'topScore':aligned['topScore'],'topScoreProb':round(aligned['topScoreProb'],6),
        'validatedFeatures':features,'learnedEligibility':'validated holdout model active',
    })
    components['learned']={k:round(v,6) for k,v in learned.items()};out['components']=components
    ordered=sorted((('home',out['homeWin']),('draw',out['draw']),('away',out['awayWin'])),key=lambda x:x[1],reverse=True);margin=ordered[0][1]-ordered[1][1]
    market_pick=max(market,key=market.get) if market else None
    out['agreement']='No public market snapshot' if not market else 'Model + market agree' if market_pick==ordered[0][0] else 'Model + market differ'
    out['signal']='High signal' if ordered[0][1]>=.62 and margin>=.16 and (not market or market_pick==ordered[0][0]) else 'Strong lean' if ordered[0][1]>=.52 and margin>=.09 else 'Mixed signals' if market and market_pick!=ordered[0][0] else 'Moderate lean' if ordered[0][1]>=.44 else 'Tight matchup'
    out['dataQuality']=int(clamp(int(out.get('dataQuality',45))+8,0,100))
    return out
