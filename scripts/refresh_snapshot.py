#!/usr/bin/env python3
"""Run the normal refresh while preserving the last available pre-match odds snapshot.

The Odds API normally stops returning completed events. Without this wrapper, a finished
fixture would lose the market component that was available before kickoff, making later
prediction review inconsistent with the pre-match forecast.
"""
from __future__ import annotations
import json
from pathlib import Path
import refresh_results

ROOT=Path(__file__).resolve().parents[1]
LIVE=ROOT/'data'/'live.js'
PREFIX='window.LIVE_DATA = '

def read_live():
    if not LIVE.exists():return {}
    text=LIVE.read_text(encoding='utf-8').strip()
    if not text.startswith(PREFIX):return {}
    body=text[len(PREFIX):]
    if body.endswith(';'):body=body[:-1]
    try:return json.loads(body)
    except json.JSONDecodeError:return {}

def fixture_key(f):return f"{f.get('home')}__{f.get('away')}__{f.get('matchweek')}"

def main():
    before=read_live()
    prior_odds={fixture_key(f):f.get('odds') for f in before.get('fixtures',[]) if f.get('odds')}
    code=refresh_results.main()
    if code:return code
    after=read_live()
    preserved=0
    for fixture in after.get('fixtures',[]):
        if fixture.get('odds'):continue
        old=prior_odds.get(fixture_key(fixture))
        if old:
            fixture['odds']=old
            fixture['odds']['preserved']=True
            preserved+=1
    if preserved:
        after.setdefault('meta',{}).setdefault('market',{})['preservedFixtures']=preserved
        LIVE.write_text(PREFIX+json.dumps(after,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf-8')
    print(f'Preserved prior market snapshots for {preserved} fixtures.')
    return 0

if __name__=='__main__':raise SystemExit(main())
