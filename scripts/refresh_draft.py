#!/usr/bin/env python3
"""Resolve data/draft.json against the public Fantasy Premier League API.

data/draft.json is a small, hand-edited list of {"team","player"} picks --
whoever you drafted for the season. This script looks each one up against
the FPL site's own public JSON (no API key), pulls real stats/points, and
cross-references data/live.js for that player's team's next fixture and this
project's own win-probability prediction for it. Output goes to
data/draft_stats.js, in the same window.X_DATA = {...}; format as the rest of
the site's data files.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timezone

from prediction_core import ROOT, load_js_assignment, write_js_assignment
from public_sources import FPL_POSITIONS, fpl_bootstrap, team_key

DRAFT_PATH = ROOT / 'data' / 'draft.json'
STATS_PATH = ROOT / 'data' / 'draft_stats.js'
LIVE_PATH = ROOT / 'data' / 'live.js'


def normalize(text):
    text = unicodedata.normalize('NFKD', text or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return ''.join(ch for ch in text.lower() if ch.isalnum())


def fpl_team_key(team_row):
    # FPL's own club names match this project's team names closely enough to
    # reuse the same alias table the other public sources already use.
    if not team_row:
        return None
    return team_key(team_row.get('name')) or team_key(team_row.get('short_name'))


def match_player(pick, elements, teams_by_id):
    wanted_team = team_key(pick.get('team')) or (pick.get('team') or '').strip() or None
    wanted_name = normalize(pick.get('player'))
    if not wanted_name:
        return None, 'no player name given'
    candidates = []
    for el in elements:
        el_team = fpl_team_key(teams_by_id.get(el.get('team')))
        full_name = f"{el.get('first_name', '')} {el.get('second_name', '')}"
        norm_names = [normalize(n) for n in (el.get('web_name'), el.get('second_name'), full_name) if n]
        exact = wanted_name in norm_names
        contains = exact or any(wanted_name in n or n in wanted_name for n in norm_names if n)
        if not contains:
            continue
        team_match = (wanted_team is None) or (el_team == wanted_team)
        candidates.append((exact and team_match, exact, team_match, el, el_team))
    if not candidates:
        return None, f'no FPL player matched "{pick.get("player")}"'
    candidates.sort(key=lambda c: c[:3], reverse=True)
    best_both, exact, team_match, el, el_team = candidates[0]
    if wanted_team and not team_match:
        return None, f'found "{el.get("web_name")}" but at {el_team or "an unrecognized club"}, not {wanted_team}'
    return (el, el_team), None


def next_fixture_for_team(team_key_value, live_fixtures):
    upcoming = [f for f in live_fixtures if f.get('status') == 'upcoming' and team_key_value in (f.get('home'), f.get('away'))]
    upcoming.sort(key=lambda f: f.get('kickoff') or '')
    if not upcoming:
        return None
    f = upcoming[0]
    is_home = f.get('home') == team_key_value
    opponent = f.get('away') if is_home else f.get('home')
    prediction = f.get('prediction') or {}
    win_prob = prediction.get('homeWin') if is_home else prediction.get('awayWin')
    return {
        'opponent': opponent, 'venue': 'home' if is_home else 'away', 'kickoff': f.get('kickoff'),
        'ourWinProbability': round(win_prob, 4) if isinstance(win_prob, (int, float)) else None,
    }


def player_payload(el, team_key_value, live_fixtures):
    def num(key, cast=float, default=0):
        v = el.get(key)
        try:
            return cast(v) if v is not None else default
        except (TypeError, ValueError):
            return default
    return {
        'fplId': el.get('id'), 'name': el.get('web_name'),
        'fullName': f"{el.get('first_name', '')} {el.get('second_name', '')}".strip(),
        'team': team_key_value, 'position': FPL_POSITIONS.get(el.get('element_type')),
        'price': round(num('now_cost') / 10, 1), 'totalPoints': num('total_points', int),
        'eventPoints': num('event_points', int), 'form': num('form'), 'pointsPerGame': num('points_per_game'),
        'selectedByPercent': num('selected_by_percent'), 'minutes': num('minutes', int),
        'goals': num('goals_scored', int), 'assists': num('assists', int), 'cleanSheets': num('clean_sheets', int),
        'bonus': num('bonus', int), 'status': el.get('status'), 'news': el.get('news') or '',
        'chanceOfPlayingNextRound': el.get('chance_of_playing_next_round'),
        'nextFixture': next_fixture_for_team(team_key_value, live_fixtures) if team_key_value else None,
    }


def main():
    draft = json.loads(DRAFT_PATH.read_text(encoding='utf-8')) if DRAFT_PATH.exists() else {'picks': []}
    picks = draft.get('picks') or []
    bootstrap, meta = fpl_bootstrap()
    live = load_js_assignment(LIVE_PATH, 'window.LIVE_DATA = ') if LIVE_PATH.exists() else {'fixtures': []}
    live_fixtures = live.get('fixtures') or []

    matched, unmatched = [], []
    if bootstrap:
        elements, teams_by_id = bootstrap['elements'], bootstrap['teams_by_id']
        for pick in picks:
            result, reason = match_player(pick, elements, teams_by_id)
            if result:
                el, team_key_value = result
                payload = player_payload(el, team_key_value, live_fixtures)
                payload['input'] = pick
                matched.append(payload)
            else:
                unmatched.append({'input': pick, 'reason': reason})
    else:
        unmatched = [{'input': p, 'reason': 'FPL data unavailable'} for p in picks]

    payload = {
        'updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source': meta, 'picks': matched, 'unmatched': unmatched,
    }
    write_js_assignment(STATS_PATH, 'window.DRAFT_DATA = ', payload)
    print(f'Draft refresh: picks={len(picks)} matched={len(matched)} unmatched={len(unmatched)} fplConnected={meta.get("connected")}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
