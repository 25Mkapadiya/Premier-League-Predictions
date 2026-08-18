#!/usr/bin/env python3
"""Remove known club departures from the lightweight FPL availability proxy."""
from __future__ import annotations
DEPARTURE_MARKERS=(
    'has joined ',
    'joined ',
    'permanently',
    'on loan for the rest of the season',
    'loan for the rest of the season',
    'transferred to ',
    'moved to ',
)
def is_departure(news):
    text=(news or '').strip().lower()
    return bool(text) and any(marker in text for marker in DEPARTURE_MARKERS)
def sanitize_team_signals(signals):
    for sig in (signals or {}).values():
        av=(sig or {}).get('availability')
        if not isinstance(av,dict):continue
        flagged=list(av.get('flagged') or [])
        if not flagged:continue
        departed=[p for p in flagged if is_departure(p.get('news'))]
        if not departed:continue
        valid=[p for p in flagged if p not in departed]
        # The original proxy is value-weighted, while the public snapshot only retains
        # compact flagged-player details. Conservatively shrink the aggregate effect
        # toward neutral in proportion to the remaining genuine availability flags.
        ratio=len(valid)/len(flagged)
        for field in ('attackMultiplier','defenseMultiplier'):
            try:old=float(av.get(field,1))
            except (TypeError,ValueError):old=1
            av[field]=round(1+(old-1)*ratio,5)
        av['flagged']=valid
        av['ignoredDepartures']=[{'name':p.get('name'),'news':p.get('news')} for p in departed]
        av['sanitized']=True
    return signals
