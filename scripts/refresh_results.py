#!/usr/bin/env python3
"""Refresh the 2026/27 EPL snapshot using only public no-key sources."""
from __future__ import annotations

from datetime import datetime, timezone
from prediction_core import ROOT, load_js_assignment, write_js_assignment
from public_sources import football_data_rows, upcoming_market_rows, understat_matches, team_key, fair_market_from_row, parse_fd_kickoff

LIVE_PATH = ROOT/'data'/'live.js'
PUBLIC_SOURCE_PAGE='https://www.football-data.co.uk/englandm.php'
TEAMS=['Arsenal','Aston Villa','Bournemouth','Brentford','Brighton','Chelsea','Coventry','Crystal Palace','Everton','Fulham','Hull','Ipswich','Leeds','Liverpool','Man City','Man United','Newcastle',"Nott'm Forest",'Sunderland','Tottenham']


def base_table():
    return {t:{'team':t,'played':0,'w':0,'d':0,'l':0,'gf':0,'ga':0,'gd':0,'pts':0,'form':[]} for t in TEAMS}

def apply_result(table,home,away,hs,as_):
    h,a=table[home],table[away]; h['played']+=1; a['played']+=1; h['gf']+=hs; h['ga']+=as_; a['gf']+=as_; a['ga']+=hs
    if hs>as_: h['w']+=1;h['pts']+=3;a['l']+=1;h['form'].append('W');a['form'].append('L')
    elif hs<as_: a['w']+=1;a['pts']+=3;h['l']+=1;h['form'].append('L');a['form'].append('W')
    else: h['d']+=1;a['d']+=1;h['pts']+=1;a['pts']+=1;h['form'].append('D');a['form'].append('D')
    h['gd']=h['gf']-h['ga'];a['gd']=a['gf']-a['ga'];h['form']=h['form'][-5:];a['form']=a['form'][-5:]

def sort_table(table): return sorted(table.values(), key=lambda r:(-r['pts'],-r['gd'],-r['gf'],r['team']))

def num(row,key):
    try:return int(float(row.get(key,'')))
    except (TypeError,ValueError):return None


def main():
    live=load_js_assignment(LIVE_PATH,'window.LIVE_DATA = '); fixtures=live.get('fixtures') or []
    rows,fd_meta=football_data_rows();results={}
    for row in rows:
        home,away=team_key(row.get('HomeTeam')),team_key(row.get('AwayTeam'));hs,as_=num(row,'FTHG'),num(row,'FTAG')
        if not home or not away or hs is None or as_ is None:continue
        results[(home,away)]={'homeScore':hs,'awayScore':as_,'kickoff':parse_fd_kickoff(row),
            'stats':{k:num(row,k) for k in ('HS','AS','HST','AST') if num(row,k) is not None},'closingOdds':fair_market_from_row(row)}
    markets,market_meta=upcoming_market_rows();understat,xg_meta=understat_matches();table=base_table();finals=0;now=datetime.now(timezone.utc)
    for f in fixtures:
        key=(f.get('home'),f.get('away'));result=results.get(key)
        if result:
            f['status']='final';f['homeScore']=result['homeScore'];f['awayScore']=result['awayScore'];f['minutes']=90;f['stats']=result['stats'];finals+=1
            if result.get('kickoff') and not f.get('kickoff'):f['kickoff']=result['kickoff']
            apply_result(table,f['home'],f['away'],result['homeScore'],result['awayScore'])
            if result.get('closingOdds'):f['closingOdds']=result['closingOdds']
        elif fd_meta.get('connected'):
            ko=f.get('kickoff');dt=None
            try:dt=datetime.fromisoformat(ko.replace('Z','+00:00')) if ko else None
            except ValueError:pass
            # Football-Data is result-oriented. Without a final row, keep the fixture upcoming.
            if f.get('status')!='final':f['status']='upcoming';f['homeScore']=None;f['awayScore']=None;f['minutes']=0
        elif f.get('status')=='final' and f.get('homeScore') is not None and f.get('awayScore') is not None:
            # Public result feed is temporarily unavailable: retain the last known-good result/table state.
            apply_result(table,f['home'],f['away'],int(f['homeScore']),int(f['awayScore']));finals+=1
        if key in markets and f.get('status')=='upcoming':f['odds']=markets[key]
        us=understat.get(key)
        if us and us.get('xg') and f.get('status')=='final':f['xg']=us['xg']
        f.pop('apiContext',None)
    if fd_meta.get('connected') or finals:
        live['table']=sort_table(table)
    live['teamSignals']={}
    live.setdefault('meta',{}).update({'lastUpdated':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'source':'Public no-key sources','sourceUrl':PUBLIC_SOURCE_PAGE,
        'seasonStarted':finals>0,'message':f'{finals} finished Premier League matches in the current snapshot.','noApi':True,
        'publicSources':{'footballData':fd_meta,'upcomingMarket':market_meta,'understat':xg_meta}})
    for key in ('market','matchStats','enrichment','freeMarket'):
        live['meta'].pop(key,None)
    write_js_assignment(LIVE_PATH,'window.LIVE_DATA = ',live)
    print(f'No-key refresh: fixtures={len(fixtures)} finals={finals} FD={fd_meta.get("connected")} Understat={xg_meta.get("connected")} market={market_meta.get("eplRows",0)}')
    return 0

if __name__=='__main__':raise SystemExit(main())
