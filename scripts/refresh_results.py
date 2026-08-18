#!/usr/bin/env python3
"""Refresh fixtures/results, current match statistics, availability proxy and market consensus."""
from __future__ import annotations
import csv,io,json,os,statistics,sys,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUTPUT=ROOT/'data'/'live.js';FPL_BOOTSTRAP='https://fantasy.premierleague.com/api/bootstrap-static/';FPL_FIXTURES='https://fantasy.premierleague.com/api/fixtures/';FOOTBALL_DATA='https://www.football-data.co.uk/mmz4281/2627/E0.csv';ODDS_ENDPOINT='https://api.the-odds-api.com/v4/sports/soccer_epl/odds/'
ALIASES={'Arsenal':'Arsenal','Aston Villa':'Aston Villa','AFC Bournemouth':'Bournemouth','Bournemouth':'Bournemouth','Brentford':'Brentford','Brighton':'Brighton','Brighton & Hove Albion':'Brighton','Brighton and Hove Albion':'Brighton','Chelsea':'Chelsea','Coventry':'Coventry','Coventry City':'Coventry','Crystal Palace':'Crystal Palace','Everton':'Everton','Fulham':'Fulham','Hull':'Hull','Hull City':'Hull','Ipswich':'Ipswich','Ipswich Town':'Ipswich','Leeds':'Leeds','Leeds United':'Leeds','Liverpool':'Liverpool','Man City':'Man City','Manchester City':'Man City','Man Utd':'Man United','Man United':'Man United','Manchester United':'Man United','Newcastle':'Newcastle','Newcastle United':'Newcastle',"Nott'm Forest":"Nott'm Forest",'Nottingham Forest':"Nott'm Forest",'Sunderland':'Sunderland','Spurs':'Tottenham','Tottenham':'Tottenham','Tottenham Hotspur':'Tottenham'}
TEAMS=['Arsenal','Aston Villa','Bournemouth','Brentford','Brighton','Chelsea','Coventry','Crystal Palace','Everton','Fulham','Hull','Ipswich','Leeds','Liverpool','Man City','Man United','Newcastle',"Nott'm Forest",'Sunderland','Tottenham']
def fetch_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'PL-Forecast-GitHub-Action/3.0'})
    with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def fetch_text(url):
    req=urllib.request.Request(url,headers={'User-Agent':'PL-Forecast-GitHub-Action/3.0'})
    with urllib.request.urlopen(req,timeout=35) as r:return r.read().decode('utf-8-sig')
def key(name):return ALIASES.get((name or '').strip())
def base_table():return {t:{'team':t,'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'gd':0,'pts':0,'form':[]} for t in TEAMS}
def apply_result(table,home,away,hs,as_):
    h,a=table[home],table[away];h['played']+=1;a['played']+=1;h['gf']+=hs;h['ga']+=as_;a['gf']+=as_;a['ga']+=hs
    if hs>as_:h['w']+=1;h['pts']+=3;a['l']+=1;h['form'].append('W');a['form'].append('L')
    elif hs<as_:a['w']+=1;a['pts']+=3;h['l']+=1;h['form'].append('L');a['form'].append('W')
    else:h['d']+=1;a['d']+=1;h['pts']+=1;a['pts']+=1;h['form'].append('D');a['form'].append('D')
    h['gd']=h['gf']-h['ga'];a['gd']=a['gf']-a['ga'];h['form']=h['form'][-5:];a['form']=a['form'][-5:]
def sort_table(table):return sorted(table.values(),key=lambda r:(-r['pts'],-r['gd'],-r['gf'],r['team']))
def player_availability(bootstrap,ids):
    by={tid:[] for tid in ids}
    for p in bootstrap.get('elements',[]):
        if p.get('team') in by:by[p['team']].append(p)
    result={}
    for tid,team in ids.items():
        players=sorted(by.get(tid,[]),key=lambda p:float(p.get('now_cost') or 0),reverse=True)[:15];an=ad=dn=dd=0.;flag=[]
        for p in players:
            value=max(float(p.get('now_cost') or 0),1);pos=int(p.get('element_type') or 0);chance=p.get('chance_of_playing_next_round')
            if chance is None:
                s=p.get('status');chance=100 if s=='a' else 75 if s=='d' else 0 if s in ('i','s','u') else 90
            av=max(0,min(100,float(chance)))/100;aw={1:0,2:.2,3:1,4:1}.get(pos,.3);dw={1:1,2:1,3:.22,4:0}.get(pos,.3);an+=value*aw*(1-av);ad+=value*aw;dn+=value*dw*(1-av);dd+=value*dw
            if av<.8:flag.append({'name':f"{p.get('first_name','')} {p.get('second_name','')}".strip(),'availability':av,'news':p.get('news') or ''})
        adef=an/ad if ad else 0;ddef=dn/dd if dd else 0;result[team]={'attackMultiplier':round(1-min(.035,.08*adef),5),'defenseMultiplier':round(1+min(.035,.08*ddef),5),'attackDeficit':round(adef,4),'defenseDeficit':round(ddef,4),'flagged':flag[:8],'source':'FPL availability proxy'}
    return result
def from_fpl():
    bootstrap,raw=fetch_json(FPL_BOOTSTRAP),fetch_json(FPL_FIXTURES);ids={};signals={}
    for t in bootstrap.get('teams',[]):
        mapped=key(t.get('name')) or key(t.get('short_name'))
        if not mapped:continue
        ids[t['id']]=mapped;signals[mapped]={'strength':t.get('strength'),'overallHome':t.get('strength_overall_home'),'overallAway':t.get('strength_overall_away'),'attackHome':t.get('strength_attack_home'),'attackAway':t.get('strength_attack_away'),'defenceHome':t.get('strength_defence_home'),'defenceAway':t.get('strength_defence_away')}
    if len(ids)<18:raise RuntimeError(f'FPL team mapping incomplete ({len(ids)} mapped clubs)')
    for team,av in player_availability(bootstrap,ids).items():signals.setdefault(team,{})['availability']=av
    out=[];table=base_table()
    for f in sorted(raw,key=lambda x:x.get('kickoff_time') or ''):
        home,away=ids.get(f.get('team_h')),ids.get(f.get('team_a'))
        if not home or not away:continue
        finished,started=bool(f.get('finished')),bool(f.get('started'));status='final' if finished else 'live' if started else 'upcoming';hs,as_=f.get('team_h_score'),f.get('team_a_score');out.append({'matchweek':f.get('event'),'kickoff':f.get('kickoff_time'),'home':home,'away':away,'status':status,'homeScore':hs,'awayScore':as_,'minutes':f.get('minutes',0)})
        if finished and isinstance(hs,int) and isinstance(as_,int):apply_result(table,home,away,hs,as_)
    return out,sort_table(table),signals,'Fantasy Premier League fixtures',FPL_FIXTURES
def football_rows():return list(csv.DictReader(io.StringIO(fetch_text(FOOTBALL_DATA))))
def csv_fair(row):
    for cols in (('AvgH','AvgD','AvgA'),('B365H','B365D','B365A'),('PSH','PSD','PSA')):
        try:h,d,a=[float(row.get(c,'') or 0) for c in cols]
        except ValueError:continue
        if h>1 and d>1 and a>1:
            raw=[1/h,1/d,1/a];s=sum(raw);return {'home':raw[0]/s,'draw':raw[1]/s,'away':raw[2]/s}
    return None
def enrich_from_football_data(fixtures):
    try:rows=football_rows()
    except Exception as e:return {'connected':False,'message':f'Football-Data enrichment unavailable: {e}'}
    lookup={(f.get('home'),f.get('away')):f for f in fixtures};applied=0
    for row in rows:
        f=lookup.get((key(row.get('HomeTeam')),key(row.get('AwayTeam'))))
        if not f:continue
        stats={}
        for c in ('HS','AS','HST','AST','HC','AC','HY','AY','HR','AR'):
            try:stats[c]=float(row[c]) if row.get(c) not in ('',None) else 0
            except (KeyError,ValueError):pass
        if stats:f['stats']=stats
        fair=csv_fair(row)
        if fair and not f.get('odds'):f['odds']={'fair':{k:round(v,6) for k,v in fair.items()},'books':1,'source':'Football-Data closing odds','updated':row.get('Date')}
        applied+=1
    return {'connected':True,'rows':len(rows),'fixtures':applied,'message':f'Historical match stats attached to {applied} fixtures.'}
def from_football_data():
    out=[];table=base_table();rows=football_rows()
    for row in rows:
        home,away=key(row.get('HomeTeam')),key(row.get('AwayTeam'))
        if not home or not away:continue
        hraw,araw=row.get('FTHG'),row.get('FTAG');finished=hraw not in (None,'') and araw not in (None,'');hs,as_=(int(float(hraw)),int(float(araw))) if finished else (None,None);kick=row.get('Date','')
        for fmt in ('%d/%m/%Y','%d/%m/%y'):
            try:kick=datetime.strptime(kick,fmt).replace(tzinfo=timezone.utc).isoformat();break
            except ValueError:pass
        f={'matchweek':None,'kickoff':kick,'home':home,'away':away,'status':'final' if finished else 'upcoming','homeScore':hs,'awayScore':as_,'minutes':90 if finished else 0};fair=csv_fair(row)
        if fair:f['odds']={'fair':{k:round(v,6) for k,v in fair.items()},'books':1,'source':'Football-Data odds','updated':row.get('Date')}
        out.append(f)
        if finished:apply_result(table,home,away,hs,as_)
    return out,sort_table(table),{},'Football-Data.co.uk fallback',FOOTBALL_DATA
def fair_for_book(book,home,away):
    market=next((m for m in book.get('markets',[]) if m.get('key')=='h2h'),None)
    if not market:return None
    prices={}
    for o in market.get('outcomes',[]):
        name,price=o.get('name'),o.get('price')
        if not isinstance(price,(int,float)) or price<=1:continue
        mapped=key(name)
        if name=='Draw':prices['draw']=float(price)
        elif mapped==home:prices['home']=float(price)
        elif mapped==away:prices['away']=float(price)
    if not all(k in prices for k in ('home','draw','away')):return None
    raw={k:1/prices[k] for k in prices};s=sum(raw.values());return {k:raw[k]/s for k in raw}
def market_consensus():
    api=os.environ.get('ODDS_API_KEY','').strip()
    if not api:return {},{'connected':False,'message':'ODDS_API_KEY is not configured.'}
    q=urllib.parse.urlencode({'apiKey':api,'regions':'uk,eu','markets':'h2h','oddsFormat':'decimal','dateFormat':'iso'});events=fetch_json(f'{ODDS_ENDPOINT}?{q}');consensus={};samples=0
    for event in events:
        home,away=key(event.get('home_team')),key(event.get('away_team'))
        if not home or not away:continue
        rows=[];updates=[]
        for book in event.get('bookmakers',[]):
            fair=fair_for_book(book,home,away)
            if fair:rows.append(fair);updates.extend([book['last_update']] if book.get('last_update') else [])
        if not rows:continue
        fair={k:statistics.median(r[k] for r in rows) for k in ('home','draw','away')};s=sum(fair.values());fair={k:fair[k]/s for k in fair};consensus[f'{home}__{away}']={'fair':{k:round(v,6) for k,v in fair.items()},'books':len(rows),'source':'The Odds API bookmaker consensus','updated':max(updates) if updates else event.get('commence_time')};samples+=len(rows)
    return consensus,{'connected':True,'fixtures':len(consensus),'bookmakerSamples':samples,'message':f'Consensus available for {len(consensus)} EPL fixtures.'}
def main():
    try:fixtures,table,signals,source,url=from_fpl()
    except Exception as first:
        try:fixtures,table,signals,source,url=from_football_data()
        except Exception as second:print(f'Refresh failed: FPL={first} | Football-Data={second}',file=sys.stderr);return 1
    stats=enrich_from_football_data(fixtures)
    try:
        markets,mm=market_consensus()
        for f in fixtures:
            if m:=markets.get(f"{f['home']}__{f['away']}"):f['odds']=m
    except Exception as e:mm={'connected':False,'message':f'Market refresh skipped: {e}'}
    now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z');finals=sum(f['status']=='final' for f in fixtures);payload={'meta':{'lastUpdated':now,'source':source,'sourceUrl':url,'seasonStarted':finals>0,'message':f'{finals} finished Premier League matches included in this snapshot.','market':mm,'matchStats':stats},'fixtures':fixtures,'table':table,'teamSignals':signals};OUTPUT.write_text('window.LIVE_DATA = '+json.dumps(payload,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf-8');print(f"Wrote {OUTPUT}: {len(fixtures)} fixtures, {finals} final, source={source}, markets={mm.get('fixtures',0)}");return 0
if __name__=='__main__':raise SystemExit(main())
