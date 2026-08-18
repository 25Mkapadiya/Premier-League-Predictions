#!/usr/bin/env python3
"""No-key public football data helpers.

Sources:
- Football-Data.co.uk downloadable CSV files
- Understat's public league data request used by its own website

No authentication, tokens, secrets, or paid feeds are required.
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

CURRENT_SEASON_CODE = "2627"
FOOTBALL_DATA_CURRENT = f"https://www.football-data.co.uk/mmz4281/{CURRENT_SEASON_CODE}/E0.csv"
FOOTBALL_DATA_FIXTURES = "https://www.football-data.co.uk/fixtures.csv"
UNDERSTAT_CURRENT = "https://understat.com/getLeagueData/EPL/2026"

ALIASES = {
    'Arsenal':'Arsenal','Aston Villa':'Aston Villa','AFC Bournemouth':'Bournemouth','Bournemouth':'Bournemouth',
    'Brentford':'Brentford','Brighton':'Brighton','Brighton & Hove Albion':'Brighton','Brighton and Hove Albion':'Brighton',
    'Chelsea':'Chelsea','Coventry':'Coventry','Coventry City':'Coventry','Crystal Palace':'Crystal Palace','Everton':'Everton',
    'Fulham':'Fulham','Hull':'Hull','Hull City':'Hull','Ipswich':'Ipswich','Ipswich Town':'Ipswich','Leeds':'Leeds','Leeds United':'Leeds',
    'Liverpool':'Liverpool','Man City':'Man City','Manchester City':'Man City','Man Utd':'Man United','Man United':'Man United',
    'Manchester United':'Man United','Newcastle':'Newcastle','Newcastle United':'Newcastle',"Nott'm Forest":"Nott'm Forest",
    'Nottingham Forest':"Nott'm Forest",'Sunderland':'Sunderland','Spurs':'Tottenham','Tottenham':'Tottenham','Tottenham Hotspur':'Tottenham'
}


def team_key(value):
    return ALIASES.get((value or '').strip())


def _plain_text_snippet(body, limit=160):
    """Strip HTML markup from an error response body so a server error page
    reads as prose in the (user-facing) health panel, not a raw HTML dump."""
    text = re.sub(r'<[^>]+>', ' ', body)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit].rstrip()


def request_bytes(url, timeout=30, ajax=False):
    headers={
        'User-Agent':'Mozilla/5.0 (compatible; PL-Forecast-NoKey/4.0)',
        'Accept':'application/json,text/html,text/csv,*/*;q=0.8',
        'Cache-Control':'no-cache',
    }
    if ajax:
        headers['Referer']='https://understat.com/'
        headers['X-Requested-With']='XMLHttpRequest'
    req=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        # Surface the response body (not just the status line) so a stale/ambiguous
        # URL is diagnosable from the recorded message instead of a bare status code.
        # This message is shown as-is in the site's health panel, so it must read as
        # plain text, not raw HTML.
        detail=''
        try:detail=_plain_text_snippet(exc.read(2000).decode('utf-8',errors='replace'))
        except Exception:pass
        message=f'HTTP {exc.code} {exc.reason}'
        if detail:message+=f' :: {detail}'
        raise RuntimeError(message) from exc


def fetch_text(url, timeout=30):
    return request_bytes(url,timeout).decode('utf-8-sig',errors='replace')


def safe_float(value):
    try:return float(value)
    except (TypeError,ValueError):return None


def football_data_rows(url=FOOTBALL_DATA_CURRENT):
    try:
        text=fetch_text(url); rows=list(csv.DictReader(io.StringIO(text)))
        if not rows:return [],{'connected':False,'message':'Football-Data CSV was empty.','url':url}
        return rows,{'connected':True,'rows':len(rows),'url':url}
    except Exception as exc:
        return [],{'connected':False,'message':f'Football-Data CSV unavailable: {exc}','url':url}


def fair_market_from_row(row):
    candidates=[
        ('AvgH','AvgD','AvgA','average bookmaker odds'),
        ('MaxH','MaxD','MaxA','maximum bookmaker odds'),
        ('B365H','B365D','B365A','Bet365 odds'),
        ('PSH','PSD','PSA','Pinnacle odds'),
    ]
    for hcol,dcol,acol,label in candidates:
        vals=[safe_float(row.get(c)) for c in (hcol,dcol,acol)]
        if all(v and v>1 for v in vals):
            raw=[1/v for v in vals];total=sum(raw)
            return {'fair':{'home':raw[0]/total,'draw':raw[1]/total,'away':raw[2]/total},'books':None,
                    'source':f'Football-Data {label}','columns':[hcol,dcol,acol]}
    return None


def upcoming_market_rows():
    rows,meta=football_data_rows(FOOTBALL_DATA_FIXTURES);found={};epl_rows=0
    for row in rows:
        if (row.get('Div') or '').strip()!='E0':continue
        home,away=team_key(row.get('HomeTeam')),team_key(row.get('AwayTeam'))
        if not home or not away:continue
        market=fair_market_from_row(row)
        if not market:continue
        market['updated']=f"{row.get('Date','')} {row.get('Time','')}".strip();market['sourceUrl']=FOOTBALL_DATA_FIXTURES
        found[(home,away)]=market;epl_rows+=1
    return found,{**meta,'eplRows':epl_rows,'attachedCandidates':len(found)}


def understat_matches(url=UNDERSTAT_CURRENT):
    try:
        payload=json.loads(request_bytes(url,ajax=True).decode('utf-8',errors='replace'))
        dates=payload.get('dates') or []
    except Exception as exc:
        return {},{'connected':False,'message':f'Understat public league data unavailable: {exc}','url':url}
    out={}
    for match in dates:
        home=team_key((match.get('h') or {}).get('title'));away=team_key((match.get('a') or {}).get('title'))
        if not home or not away:continue
        xg=match.get('xG') or {};hxg,axg=safe_float(xg.get('h')),safe_float(xg.get('a'))
        item={'home':home,'away':away,'datetime':match.get('datetime'),'isResult':bool(match.get('isResult'))}
        if hxg is not None and axg is not None:item['xg']={'home':hxg,'away':axg,'source':'Understat public EPL data'}
        out[(home,away)]=item
    return out,{'connected':True,'matches':len(out),'url':url}


def parse_fd_kickoff(row):
    date_text=(row.get('Date') or '').strip();time_text=(row.get('Time') or '').strip()
    for fmt in ('%d/%m/%Y %H:%M','%d/%m/%y %H:%M','%d/%m/%Y','%d/%m/%y'):
        try:
            raw=f'{date_text} {time_text}'.strip() if '%H' in fmt else date_text
            return datetime.strptime(raw,fmt).replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z')
        except ValueError:continue
    return None
