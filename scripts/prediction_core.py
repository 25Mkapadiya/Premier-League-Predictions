#!/usr/bin/env python3
"""Shared prediction utilities. Every feature must exist before fixture kickoff."""
from __future__ import annotations
import json,math
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
def clamp(x,lo,hi):return max(lo,min(hi,x))
def parse_iso(v):
    if not v:return None
    try:return datetime.fromisoformat(v.replace('Z','+00:00'))
    except ValueError:return None
def load_js_assignment(path,prefix):
    text=path.read_text(encoding='utf-8').strip()
    if not text.startswith(prefix):raise ValueError(f'{path} does not start with {prefix!r}')
    body=text[len(prefix):].strip();body=body[:-1] if body.endswith(';') else body
    return json.loads(body)
def write_js_assignment(path,prefix,payload):path.write_text(prefix+json.dumps(payload,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf-8')
def factorial(n):
    out=1
    for i in range(2,n+1):out*=i
    return out
def poisson(k,lam):return math.exp(-lam)*(lam**k)/factorial(k)
def score_grid(hx,ax,rho=-.06,max_goals=8):
    cells=[];total=0
    for x in range(max_goals+1):
        for y in range(max_goals+1):
            p=poisson(x,hx)*poisson(y,ax)
            if x==0 and y==0:p*=1-hx*ax*rho
            elif x==0 and y==1:p*=1+hx*rho
            elif x==1 and y==0:p*=1+ax*rho
            elif x==1 and y==1:p*=1-rho
            p=max(p,0);cells.append((x,y,p));total+=p
    total=max(total,1e-12);home=draw=away=over=btts=0;norm=[]
    for x,y,p in cells:
        p/=total;norm.append((x,y,p))
        if x>y:home+=p
        elif x==y:draw+=p
        else:away+=p
        if x+y>=3:over+=p
        if x>0 and y>0:btts+=p
    top=max(norm,key=lambda c:c[2])
    return {'homeXg':hx,'awayXg':ax,'home':home,'draw':draw,'away':away,'over25':over,'under25':1-over,'btts':btts,'noBtts':1-btts,'score':[int(math.floor(hx+.5)),int(math.floor(ax+.5))],'topScore':[top[0],top[1]],'topScoreProb':top[2]}
def structural_prediction(model,home,away):
    t=model['teams'];p=model['params'];h,a=t[home],t[away];d=(h['elo']+p['eloHomeAdvantage']-a['elo'])/400
    hx=p['homeGoalRate']*h['homeAtt']*a['awayDef'];ax=p['awayGoalRate']*a['awayAtt']*h['homeDef'];hx*=math.exp(p['eloGoalWeight']*d);ax*=math.exp(-p['eloGoalWeight']*d)
    return score_grid(hx,ax,p.get('rho',-.06),p.get('maxGoals',8))
def fair_market(odds):
    if not odds:return None
    fair=odds.get('fair')
    if fair and all(isinstance(fair.get(k),(int,float)) for k in ('home','draw','away')):
        v={k:max(float(fair[k]),1e-8) for k in ('home','draw','away')};s=sum(v.values());return {k:v[k]/s for k in v}
    try:prices={k:float(odds[k]) for k in ('home','draw','away')}
    except (KeyError,TypeError,ValueError):return None
    if not all(v>1 for v in prices.values()):return None
    raw={k:1/v for k,v in prices.items()};s=sum(raw.values());return {k:raw[k]/s for k in raw}
def log_pool(a,b,w):
    w=clamp(w,0,1);v={k:max(a[k],1e-9)**(1-w)*max(b[k],1e-9)**w for k in ('home','draw','away')};s=sum(v.values());return {k:v[k]/s for k in v}
def align_lambdas(hx,ax,target,rho,max_goals):
    best=None
    for si in range(15):
        scale=.86+si*.02
        for ti in range(31):
            tilt=-.45+ti*.03;h=clamp(hx*scale*math.exp(tilt),.18,4.5);a=clamp(ax*scale*math.exp(-tilt),.15,4);g=score_grid(h,a,rho,max_goals)
            err=sum((g[k]-target[k])**2 for k in ('home','draw','away'))+.008*((h+a)-(hx+ax))**2
            if best is None or err<best[0]:best=(err,g)
    return best[1]
def recent_matches(fixtures,team,cutoff,limit=8):
    cut=parse_iso(cutoff) or datetime.now(timezone.utc);rows=[]
    for f in fixtures:
        if f.get('status')!='final' or f.get('homeScore') is None or f.get('awayScore') is None:continue
        dt=parse_iso(f.get('kickoff'))
        if not dt or dt>=cut:continue
        if team in (f.get('home'),f.get('away')):rows.append(f)
    rows.sort(key=lambda f:parse_iso(f.get('kickoff')) or datetime.min.replace(tzinfo=timezone.utc),reverse=True);return rows[:limit]
def team_recent_profile(model,fixtures,team,cutoff):
    rows=recent_matches(fixtures,team,cutoff,8)
    if not rows:return {'matches':0,'ppm':1.35,'gdpg':0,'sotDiff':0,'attackResidual':1,'defenseResidual':1,'xgMatches':0}
    ws=pts=gd=sot=la=ld=0;xgm=0
    for i,f in enumerate(rows):
        w=.78**i;home=f['home']==team;gf=f['homeScore'] if home else f['awayScore'];ga=f['awayScore'] if home else f['homeScore'];p=3 if gf>ga else 1 if gf==ga else 0;stats=f.get('stats') or {};sf=float(stats.get('HST',0) if home else stats.get('AST',0) or 0);sa=float(stats.get('AST',0) if home else stats.get('HST',0) or 0);base=structural_prediction(model,f['home'],f['away']);ef=base['homeXg'] if home else base['awayXg'];ea=base['awayXg'] if home else base['homeXg'];xg=f.get('xg') or {};xgf=xg.get('home') if home else xg.get('away');xga=xg.get('away') if home else xg.get('home')
        if isinstance(xgf,(int,float)) and isinstance(xga,(int,float)):of,oa=float(xgf),float(xga);xgm+=1
        else:of,oa=float(gf),float(ga)
        att=clamp((of+.65)/(ef+.65),.5,1.75);deff=clamp((oa+.65)/(ea+.65),.5,1.75);pts+=p*w;gd+=(gf-ga)*w;sot+=(sf-sa)*w;la+=math.log(att)*w;ld+=math.log(deff)*w;ws+=w
    prior=4.5;return {'matches':len(rows),'ppm':pts/ws,'gdpg':gd/ws,'sotDiff':sot/ws,'attackResidual':math.exp(la/(ws+prior)),'defenseResidual':math.exp(ld/(ws+prior)),'xgMatches':xgm}
def rest_days(fixtures,team,cutoff):
    cut=parse_iso(cutoff);rows=recent_matches(fixtures,team,cutoff,1)
    if not cut or not rows:return None
    prev=parse_iso(rows[0].get('kickoff'));return None if not prev else max(0,(cut-prev).total_seconds()/86400)
def congestion_count(fixtures,team,cutoff,days=14):
    cut=parse_iso(cutoff)
    if not cut:return 0
    n=0
    for f in fixtures:
        if f.get('status')!='final' or team not in (f.get('home'),f.get('away')):continue
        dt=parse_iso(f.get('kickoff'))
        if dt and 0<(cut-dt).total_seconds()<=days*86400:n+=1
    return n
def availability_multiplier(sig):
    if not sig:return 1,1,{'connected':False}
    av=sig.get('availability') or {};att=clamp(float(av.get('attackMultiplier',1)),.96,1.02);deff=clamp(float(av.get('defenseMultiplier',1)),.96,1.02);return att,deff,{'connected':bool(av),**av}
def load_context():
    path=ROOT/'data'/'context.json'
    if not path.exists():return {'fixtures':{}}
    try:return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:return {'fixtures':{}}
def context_multipliers(context,h,a):
    x=(context.get('fixtures') or {}).get(f'{h}__{a}',{});return {'homeAttack':clamp(float(x.get('homeAttackMultiplier',1)),.88,1.12),'homeDefense':clamp(float(x.get('homeDefenseMultiplier',1)),.88,1.12),'awayAttack':clamp(float(x.get('awayAttackMultiplier',1)),.88,1.12),'awayDefense':clamp(float(x.get('awayDefenseMultiplier',1)),.88,1.12),'note':x.get('note',''),'updated':x.get('updated')}
def feature_vector(dynamic,market,hp,ap,rest_diff,avdiff):
    m=market or {'home':dynamic['home'],'draw':dynamic['draw'],'away':dynamic['away']};return {'base_home':dynamic['home'],'base_draw':dynamic['draw'],'base_away':dynamic['away'],'market_home':m['home'],'market_draw':m['draw'],'market_away':m['away'],'market_available':1 if market else 0,'form_ppm_diff':clamp(hp['ppm']-ap['ppm'],-3,3),'gdpg_diff':clamp(hp['gdpg']-ap['gdpg'],-4,4),'sotdiff_diff':clamp(hp['sotDiff']-ap['sotDiff'],-10,10),'rest_diff':clamp(rest_diff,-7,7),'availability_diff':clamp(avdiff,-.08,.08)}
def softmax(v):
    m=max(v);e=[math.exp(x-m) for x in v];s=sum(e);return [x/s for x in e]
def trained_probabilities(model,features):
    if not model or not model.get('enabled'):return None
    names=model.get('features') or [];coef=model.get('coefficients') or [];inter=model.get('intercepts') or []
    if not names or len(coef)!=3 or len(inter)!=3:return None
    z=[]
    for n in names:
        scale=float((model.get('scales') or {}).get(n,1)) or 1;z.append((float(features.get(n,0))-float((model.get('means') or {}).get(n,0)))/scale)
    logits=[float(inter[c])+sum(float(w)*x for w,x in zip(coef[c],z)) for c in range(3)];temp=clamp(float(model.get('temperature',1)),.4,2.5);p=softmax([x/temp for x in logits]);return {'home':p[0],'draw':p[1],'away':p[2]}
def predict_fixture(model,live,fixture,trained=None,context=None):
    h,a,cut=fixture['home'],fixture['away'],fixture.get('kickoff');base=structural_prediction(model,h,a);fixtures=live.get('fixtures') or [];hp=team_recent_profile(model,fixtures,h,cut);ap=team_recent_profile(model,fixtures,a,cut);hx=base['homeXg']*(hp['attackResidual']**.34)*(ap['defenseResidual']**.28);ax=base['awayXg']*(ap['attackResidual']**.34)*(hp['defenseResidual']**.28)
    if hp['xgMatches']>=2:hx*=hp['attackResidual']**.08;ax*=hp['defenseResidual']**.048
    if ap['xgMatches']>=2:ax*=ap['attackResidual']**.08;hx*=ap['defenseResidual']**.048
    hr,ar=rest_days(fixtures,h,cut),rest_days(fixtures,a,cut);rd=0 if hr is None or ar is None else hr-ar;hx*=math.exp(.012*clamp(rd,-4,4));ax*=math.exp(-.012*clamp(rd,-4,4));hc,ac=congestion_count(fixtures,h,cut),congestion_count(fixtures,a,cut);cd=hc-ac;hx*=math.exp(-.008*clamp(cd,-3,3));ax*=math.exp(.008*clamp(cd,-3,3));signals=live.get('teamSignals') or {};ha,hd,hm=availability_multiplier(signals.get(h));aa,ad,am=availability_multiplier(signals.get(a));hx*=ha*ad;ax*=aa*hd;avdiff=(ha-aa)+(ad-hd);ctx=context_multipliers(context or {'fixtures':{}},h,a);hx*=ctx['homeAttack']*ctx['awayDefense'];ax*=ctx['awayAttack']*ctx['homeDefense'];hx,ax=clamp(hx,.2,4.4),clamp(ax,.18,4);params=model['params'];dynamic=score_grid(hx,ax,params.get('rho',-.06),params.get('maxGoals',8));market=fair_market(fixture.get('odds'));features=feature_vector(dynamic,market,hp,ap,rd,avdiff);learned=trained_probabilities(trained,features)
    if learned and int((trained or {}).get('trainingSamples',0))>=500:target=log_pool({k:dynamic[k] for k in ('home','draw','away')},learned,.70);engine='trained ensemble'
    elif market:target=log_pool({k:dynamic[k] for k in ('home','draw','away')},market,.35);engine='dynamic + market'
    else:target={k:dynamic[k] for k in ('home','draw','away')};engine='dynamic score model'
    aligned=align_lambdas(hx,ax,target,params.get('rho',-.06),params.get('maxGoals',8));fp={k:aligned[k] for k in ('home','draw','away')};ordered=sorted(fp.items(),key=lambda kv:kv[1],reverse=True);margin=ordered[0][1]-ordered[1][1];mp=max(market,key=market.get) if market else None;pick=ordered[0][0];agreement='No market snapshot' if not market else 'Model + market agree' if mp==pick else 'Model + market differ';quality=52+min(hp['matches']+ap['matches'],12)*2+(10 if market else 0)+(6 if hp['xgMatches']+ap['xgMatches']>=4 else 0)+(5 if hm.get('connected') or am.get('connected') else 0)+(5 if fixture.get('apiContext',{}).get('lineupsConfirmed') else 0)+(5 if learned else 0);quality=int(clamp(quality,0,100));signal='High signal' if ordered[0][1]>=.62 and margin>=.16 and (not market or mp==pick) else 'Strong lean' if ordered[0][1]>=.52 and margin>=.09 else 'Mixed signals' if market and mp!=pick else 'Moderate lean' if ordered[0][1]>=.44 else 'Tight matchup'
    return {'version':'3.0','engine':engine,'asOf':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'homeWin':round(aligned['home'],6),'draw':round(aligned['draw'],6),'awayWin':round(aligned['away'],6),'homeXg':round(aligned['homeXg'],4),'awayXg':round(aligned['awayXg'],4),'over25':round(aligned['over25'],6),'under25':round(aligned['under25'],6),'btts':round(aligned['btts'],6),'noBtts':round(aligned['noBtts'],6),'score':aligned['score'],'topScore':aligned['topScore'],'topScoreProb':round(aligned['topScoreProb'],6),'signal':signal,'agreement':agreement,'dataQuality':quality,'components':{'structural':{k:round(base[k],6) for k in ('home','draw','away')},'dynamic':{k:round(dynamic[k],6) for k in ('home','draw','away')},'market':{k:round(market[k],6) for k in market} if market else None,'learned':{k:round(learned[k],6) for k in learned} if learned else None,'recent':{'home':hp,'away':ap},'rest':{'homeDays':hr,'awayDays':ar,'difference':rd,'homeMatches14d':hc,'awayMatches14d':ac},'availability':{'home':hm,'away':am},'context':ctx,'apiContext':fixture.get('apiContext')},'features':{k:round(v,6) for k,v in features.items()}}
def brier(prob,actual):
    target={'H':(1,0,0),'D':(0,1,0),'A':(0,0,1)}[actual];vals=(prob['home'],prob['draw'],prob['away']);return sum((p-y)**2 for p,y in zip(vals,target))
def log_loss(prob,actual):return -math.log(max(prob[{'H':'home','D':'draw','A':'away'}[actual]],1e-12))
