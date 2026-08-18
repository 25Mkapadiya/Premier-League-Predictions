#!/usr/bin/env python3
"""Optional provider-backed enrichments. Tokens stay in GitHub Actions secrets."""
from __future__ import annotations
import json,os,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
ALIASES={'Arsenal':'Arsenal','Aston Villa':'Aston Villa','AFC Bournemouth':'Bournemouth','Bournemouth':'Bournemouth','Brentford':'Brentford','Brighton':'Brighton','Brighton & Hove Albion':'Brighton','Brighton and Hove Albion':'Brighton','Chelsea':'Chelsea','Coventry':'Coventry','Coventry City':'Coventry','Crystal Palace':'Crystal Palace','Everton':'Everton','Fulham':'Fulham','Hull':'Hull','Hull City':'Hull','Ipswich':'Ipswich','Ipswich Town':'Ipswich','Leeds':'Leeds','Leeds United':'Leeds','Liverpool':'Liverpool','Man City':'Man City','Manchester City':'Man City','Man Utd':'Man United','Man United':'Man United','Manchester United':'Man United','Newcastle':'Newcastle','Newcastle United':'Newcastle',"Nott'm Forest":"Nott'm Forest",'Nottingham Forest':"Nott'm Forest",'Sunderland':'Sunderland','Spurs':'Tottenham','Tottenham':'Tottenham','Tottenham Hotspur':'Tottenham'}
def key(name):return ALIASES.get((name or '').strip())
def get_json(url,headers=None):
    req=urllib.request.Request(url,headers={'User-Agent':'PL-Forecast-Enrichment/3.0',**(headers or {})})
    with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def parse_time(v):
    if not v:return None
    try:return datetime.fromisoformat(v.replace('Z','+00:00'))
    except ValueError:return None
def sportmonks_xg(fixtures):
    token=os.environ.get('SPORTMONKS_API_TOKEN','').strip()
    if not token:return {'connected':False,'message':'SPORTMONKS_API_TOKEN not configured.'}
    now=datetime.now(timezone.utc);dates=sorted({dt.date().isoformat() for f in fixtures if f.get('status')=='final' and not f.get('xg') and (dt:=parse_time(f.get('kickoff'))) and (now-dt).days<=28});matches={};calls=0
    for date in dates:
        q=urllib.parse.urlencode({'api_token':token,'include':'participants;xGFixture','per_page':50});payload=get_json(f'https://api.sportmonks.com/v3/football/fixtures/date/{date}?{q}');calls+=1
        for item in payload.get('data',[]) if isinstance(payload,dict) else []:
            parts=item.get('participants') or [];hp=next((p for p in parts if (p.get('meta') or {}).get('location')=='home'),None);ap=next((p for p in parts if (p.get('meta') or {}).get('location')=='away'),None);home,away=key((hp or {}).get('name')),key((ap or {}).get('name'))
            if (not home or not away) and ' vs ' in item.get('name',''):
                h,a=item['name'].split(' vs ',1);home,away=key(h),key(a)
            if not home or not away:continue
            expected=item.get('xGFixture') or item.get('expected') or item.get('x_g_fixture') or [];vals={}
            for row in expected:
                loc=row.get('location');data=row.get('data') or {};value=data.get('value') if isinstance(data,dict) else None
                if loc in ('home','away') and isinstance(value,(int,float)):vals[loc]=float(value)
            if 'home' in vals and 'away' in vals:matches[(date,home,away)]=vals
    applied=0
    for f in fixtures:
        dt=parse_time(f.get('kickoff'));vals=matches.get((dt.date().isoformat(),f.get('home'),f.get('away'))) if dt else None
        if vals:f['xg']={'home':round(vals['home'],4),'away':round(vals['away'],4),'source':'Sportmonks xG'};applied+=1
    return {'connected':True,'calls':calls,'fixtures':applied,'message':f'xG attached to {applied} recent finished fixtures.'}
def api_football_context(fixtures):
    token=os.environ.get('API_FOOTBALL_KEY','').strip()
    if not token:return {'connected':False,'message':'API_FOOTBALL_KEY not configured.'}
    headers={'x-apisports-key':token};now=datetime.now(timezone.utc);start=(now-timedelta(hours=3)).date().isoformat();end=(now+timedelta(days=3)).date().isoformat();q=urllib.parse.urlencode({'league':39,'season':2026,'from':start,'to':end});payload=get_json(f'https://v3.football.api-sports.io/fixtures?{q}',headers);lookup={};calls=1
    for row in payload.get('response',[]) if isinstance(payload,dict) else []:
        teams=row.get('teams') or {};home=key((teams.get('home') or {}).get('name'));away=key((teams.get('away') or {}).get('name'));fix=row.get('fixture') or {}
        if home and away and fix.get('id'):lookup[(home,away)]={'id':fix['id'],'date':fix.get('date')}
    enriched=0
    for f in fixtures:
        dt=parse_time(f.get('kickoff'));api=lookup.get((f.get('home'),f.get('away')))
        if not dt or not api or not(-3<=(dt-now).total_seconds()/3600<=48):continue
        fid=api['id'];inj=get_json(f'https://v3.football.api-sports.io/injuries?fixture={fid}',headers);calls+=1;lin=get_json(f'https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}',headers);calls+=1;hi=[];ai=[]
        for item in inj.get('response',[]) if isinstance(inj,dict) else []:
            t=key(((item.get('team') or {}).get('name')));name=((item.get('player') or {}).get('name'))
            if name and t==f.get('home'):hi.append(name)
            elif name and t==f.get('away'):ai.append(name)
        rows=lin.get('response',[]) if isinstance(lin,dict) else [];formations={};starters={'home':[],'away':[]}
        for row in rows:
            t=key(((row.get('team') or {}).get('name')));side='home' if t==f.get('home') else 'away' if t==f.get('away') else None
            if not side:continue
            formations[side]=row.get('formation')
            for p in row.get('startXI',[]) or []:
                name=(((p or {}).get('player') or {}).get('name'))
                if name:starters[side].append(name)
        f['apiContext']={'source':'API-Football','fixtureId':fid,'homeInjuries':hi[:12],'awayInjuries':ai[:12],'homeInjuryCount':len(hi),'awayInjuryCount':len(ai),'lineupsConfirmed':bool(starters['home'] and starters['away']),'formations':formations,'starters':starters if starters['home'] or starters['away'] else None,'updated':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')};enriched+=1
    return {'connected':True,'calls':calls,'fixtures':enriched,'message':f'Context checked for {enriched} near-term fixtures.'}
def enrich(fixtures):
    meta={}
    try:meta['xg']=sportmonks_xg(fixtures)
    except Exception as e:meta['xg']={'connected':False,'message':f'Sportmonks enrichment failed: {e}'}
    try:meta['lineups']=api_football_context(fixtures)
    except Exception as e:meta['lineups']={'connected':False,'message':f'API-Football enrichment failed: {e}'}
    return meta
