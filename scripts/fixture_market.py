#!/usr/bin/env python3
"""Attach Football-Data's free upcoming EPL fixture odds when no richer market snapshot exists."""
from __future__ import annotations
import csv,io,urllib.request
URL='https://www.football-data.co.uk/fixtures.csv'
ALIASES={'Arsenal':'Arsenal','Aston Villa':'Aston Villa','AFC Bournemouth':'Bournemouth','Bournemouth':'Bournemouth','Brentford':'Brentford','Brighton':'Brighton','Brighton & Hove Albion':'Brighton','Chelsea':'Chelsea','Coventry':'Coventry','Coventry City':'Coventry','Crystal Palace':'Crystal Palace','Everton':'Everton','Fulham':'Fulham','Hull':'Hull','Hull City':'Hull','Ipswich':'Ipswich','Ipswich Town':'Ipswich','Leeds':'Leeds','Leeds United':'Leeds','Liverpool':'Liverpool','Man City':'Man City','Manchester City':'Man City','Man Utd':'Man United','Man United':'Man United','Manchester United':'Man United','Newcastle':'Newcastle','Newcastle United':'Newcastle',"Nott'm Forest":"Nott'm Forest",'Nottingham Forest':"Nott'm Forest",'Sunderland':'Sunderland','Spurs':'Tottenham','Tottenham':'Tottenham','Tottenham Hotspur':'Tottenham'}
def key(v):return ALIASES.get((v or '').strip())
def download():
    req=urllib.request.Request(URL,headers={'User-Agent':'PL-Forecast-Fixtures/3.1','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8-sig')
def fair(row):
    candidates=(('AvgH','AvgD','AvgA'),('B365H','B365D','B365A'),('PSH','PSD','PSA'),('MaxH','MaxD','MaxA'))
    for cols in candidates:
        try:h,d,a=[float(row.get(c,'') or 0) for c in cols]
        except (TypeError,ValueError):continue
        if h>1 and d>1 and a>1:
            raw=[1/h,1/d,1/a];s=sum(raw);return {'home':raw[0]/s,'draw':raw[1]/s,'away':raw[2]/s},cols
    return None,None
def division_is_epl(row):
    raw=str(row.get('Div') or row.get('League') or row.get('Competition') or '').strip().upper()
    return raw in ('E0','ENG PR','EPL','PREMIER LEAGUE','ENGLAND PREMIER LEAGUE') or ('PREMIER' in raw and 'ENGL' in raw)
def attach(fixtures):
    try:text=download();reader=csv.DictReader(io.StringIO(text));rows=list(reader);headers=list(reader.fieldnames or [])
    except Exception as e:return {'connected':False,'message':f'Free fixture odds unavailable: {e}','sourceUrl':URL}
    found={};epl=0
    for row in rows:
        h,a=key(row.get('HomeTeam') or row.get('Home')),key(row.get('AwayTeam') or row.get('Away'))
        if not h or not a:continue
        # If the source omitted a division column, the known EPL team mapping itself
        # safely identifies the EPL rows. Otherwise require an EPL division label.
        has_div=any(x in row for x in ('Div','League','Competition'))
        if has_div and not division_is_epl(row):continue
        fp,cols=fair(row)
        if not fp:continue
        found[(h,a)]={'fair':{k:round(v,6) for k,v in fp.items()},'books':1,'source':'Football-Data upcoming fixture odds','sourceUrl':URL,'updated':f"{row.get('Date','')} {row.get('Time','')}".strip(),'columns':list(cols)};epl+=1
    applied=0
    for f in fixtures:
        if f.get('odds'):continue
        odds=found.get((f.get('home'),f.get('away')))
        if odds:f['odds']=odds;applied+=1
    diagnostic={}
    if not found:
        diagnostic={'headers':headers[:30],'sampleDivisions':list(dict.fromkeys(str(r.get('Div') or r.get('League') or r.get('Competition') or '') for r in rows[:40]))[:12],'sampleTeams':[[(r.get('HomeTeam') or r.get('Home')), (r.get('AwayTeam') or r.get('Away'))] for r in rows[:6]]}
    return {'connected':bool(found),'availableFixtures':epl,'attached':applied,'message':f'Free market probabilities attached to {applied} EPL fixtures.','sourceUrl':URL,**diagnostic}
