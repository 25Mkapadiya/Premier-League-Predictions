#!/usr/bin/env python3
"""Attach Football-Data's free upcoming EPL fixture odds when no richer market snapshot exists."""
from __future__ import annotations
import csv,io,urllib.request
URL='https://www.football-data.co.uk/fixtures.csv'
ALIASES={'Arsenal':'Arsenal','Aston Villa':'Aston Villa','AFC Bournemouth':'Bournemouth','Bournemouth':'Bournemouth','Brentford':'Brentford','Brighton':'Brighton','Brighton & Hove Albion':'Brighton','Chelsea':'Chelsea','Coventry':'Coventry','Coventry City':'Coventry','Crystal Palace':'Crystal Palace','Everton':'Everton','Fulham':'Fulham','Hull':'Hull','Hull City':'Hull','Ipswich':'Ipswich','Ipswich Town':'Ipswich','Leeds':'Leeds','Leeds United':'Leeds','Liverpool':'Liverpool','Man City':'Man City','Manchester City':'Man City','Man Utd':'Man United','Man United':'Man United','Manchester United':'Man United','Newcastle':'Newcastle','Newcastle United':'Newcastle',"Nott'm Forest":"Nott'm Forest",'Nottingham Forest':"Nott'm Forest",'Sunderland':'Sunderland','Spurs':'Tottenham','Tottenham':'Tottenham','Tottenham Hotspur':'Tottenham'}
def key(v):return ALIASES.get((v or '').strip())
def download():
    req=urllib.request.Request(URL,headers={'User-Agent':'PL-Forecast-Fixtures/3.0','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8-sig')
def fair(row):
    for cols in (('AvgH','AvgD','AvgA'),('B365H','B365D','B365A'),('PSH','PSD','PSA')):
        try:h,d,a=[float(row.get(c,'') or 0) for c in cols]
        except (TypeError,ValueError):continue
        if h>1 and d>1 and a>1:
            raw=[1/h,1/d,1/a];s=sum(raw);return {'home':raw[0]/s,'draw':raw[1]/s,'away':raw[2]/s},cols
    return None,None
def attach(fixtures):
    try:rows=list(csv.DictReader(io.StringIO(download())))
    except Exception as e:return {'connected':False,'message':f'Free fixture odds unavailable: {e}','sourceUrl':URL}
    found={};epl=0
    for row in rows:
        if row.get('Div') not in ('E0','ENG PR','EPL',None,''):continue
        h,a=key(row.get('HomeTeam')),key(row.get('AwayTeam'))
        if not h or not a:continue
        fp,cols=fair(row)
        if not fp:continue
        found[(h,a)]={'fair':{k:round(v,6) for k,v in fp.items()},'books':1,'source':'Football-Data upcoming fixture odds','sourceUrl':URL,'updated':f"{row.get('Date','')} {row.get('Time','')}".strip(),'columns':list(cols)};epl+=1
    applied=0
    for f in fixtures:
        if f.get('odds'):continue
        odds=found.get((f.get('home'),f.get('away')))
        if odds:f['odds']=odds;applied+=1
    return {'connected':bool(found),'availableFixtures':epl,'attached':applied,'message':f'Free market probabilities attached to {applied} EPL fixtures.','sourceUrl':URL}
