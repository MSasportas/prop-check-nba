"""espn.py: ESPN's public NBA JSON (no key). Schedule, rosters, injuries and box scores.

Only the GitHub runner can reach ESPN (the build sandbox cannot). With PC_ESPN_FIXTURE_DIR set every call reads a saved file:
scoreboard_<YYYYMMDD>.json, summary_<event>.json, injuries.json, roster_<CODE>.json.
"""
import json
import os
import re

import common
import teams

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SOURCE = {"ok": 0, "failed": 0}
HEADSHOT_RE = re.compile(r"^https://a\.espncdn\.com/i/headshots/nba/players/full/\d+\.png$")


def _fixture_dir():
    return os.environ.get("PC_ESPN_FIXTURE_DIR")


def _get(path, fixture_name):
    fx = _fixture_dir()
    if fx:
        try:
            with open(os.path.join(fx, fixture_name), "r", encoding="utf-8") as f:
                SOURCE["ok"] += 1
                return json.load(f)
        except (OSError, ValueError):
            SOURCE["failed"] += 1
            return None
    r = common.http_get("%s/%s" % (BASE, path), timeout=20)
    js = r.json() if r.ok else None
    SOURCE["ok" if js is not None else "failed"] += 1
    return js


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _made(x):
    """'3-7' -> 3.0 (made of made-attempted), None when unreadable."""
    try:
        return float(str(x).split("-")[0])
    except (TypeError, ValueError):
        return None


def scoreboard(date):
    """date 'YYYY-MM-DD' -> list of games, regular season only, or None when ESPN did not answer.
    game: id, start (ISO, Eastern), away, home (ESPN codes), state (pre / in / post), completed, detail."""
    ymd = date.replace("-", "")
    js = _get("scoreboard?dates=%s&limit=50" % ymd, "scoreboard_%s.json" % ymd)
    if js is None:
        return None
    out = []
    for e in js.get("events", []) or []:
        if (e.get("season") or {}).get("type") != 2:
            continue
        try:
            c = e["competitions"][0]
            side = {x["homeAway"]: x for x in c["competitors"]}
            st = e["status"]["type"]
            out.append({"id": str(e["id"]), "date": date, "start": common.iso(common.parse_iso(e["date"])),
                        "away": teams.code(side["away"]["team"]["abbreviation"]),
                        "home": teams.code(side["home"]["team"]["abbreviation"]),
                        "state": st.get("state"), "completed": bool(st.get("completed")), "status_name": st.get("name"),
                        "detail": st.get("shortDetail") or st.get("detail"),
                        "score": {teams.code(side[h]["team"]["abbreviation"]): side[h].get("score") for h in ("away", "home")}})
        except (KeyError, IndexError, TypeError):
            continue
    return out


def roster(code):
    """Team code -> [{"pid", "name", "team", "pos", "injury", "headshot"}] or None. headshot = ESPN's own photo link
    (a.espncdn.com, keyed by the same ESPN id as our picks) or None; display only (data/headshots.json)."""
    tid = TEAM_IDS.get(code)
    if not tid:
        return None
    js = _get("teams/%s/roster" % tid, "roster_%s.json" % code)
    if js is None:
        return None
    out = []
    for a in js.get("athletes", []) or []:
        inj = (a.get("injuries") or [{}])[0].get("status") if a.get("injuries") else None
        hs = (a.get("headshot") or {}).get("href") if isinstance(a.get("headshot"), dict) else None
        out.append({"pid": str(a.get("id")), "name": a.get("displayName") or a.get("fullName"), "team": code,
                    "pos": (a.get("position") or {}).get("abbreviation"), "injury": inj,
                    "headshot": hs if isinstance(hs, str) and HEADSHOT_RE.match(hs) else None})
    return out


def injuries():
    """League injury list -> {pid: {"status" (lower case), "name", "team", "date", "note"}} or None."""
    js = _get("injuries", "injuries.json")
    if js is None:
        return None
    out = {}
    for blk in js.get("injuries", []) or []:
        code = teams.code(blk.get("displayName"))
        for i in blk.get("injuries", []) or []:
            ath = i.get("athlete") or {}
            pid = None
            for l in ath.get("links", []) or []:
                h = l.get("href") or ""
                if "/id/" in h:
                    pid = h.split("/id/")[1].split("/")[0]
                    break
            if not pid:
                continue
            out[pid] = {"status": (i.get("status") or "").lower(), "name": ath.get("displayName"), "team": code,
                        "date": i.get("date"), "note": (i.get("shortComment") or "")[:200]}
    return out


def box(summary):
    """Final game summary -> (player rows, team rows) in the stats-store format, or (None, None) if not final."""
    try:
        hdr = summary["header"]["competitions"][0]
        if not hdr["status"]["type"].get("completed"):
            return None, None
        comp = {c["homeAway"]: c for c in hdr["competitors"]}
    except (KeyError, IndexError, TypeError):
        return None, None
    ab = {ha: teams.code(comp[ha]["team"]["abbreviation"]) for ha in ("home", "away")}
    other = {ab["home"]: ab["away"], ab["away"]: ab["home"]}
    ot = max(0, max(len(comp[ha].get("linescores", []) or []) for ha in ab) - 4)
    gid = str(summary["header"]["id"])
    date = common.slate_date(common.parse_iso(hdr.get("date")))
    pr, tr = [], []
    for p in summary.get("boxscore", {}).get("players", []) or []:
        tm = teams.code(p["team"]["abbreviation"])
        st = (p.get("statistics") or [{}])[0]
        lab = st.get("labels") or []
        for a in st.get("athletes", []) or []:
            ath = a.get("athlete") or {}
            d = dict(zip(lab, a.get("stats") or []))
            dnp = bool(a.get("didNotPlay")) or not a.get("stats")
            pr.append({"pid": str(ath.get("id")), "name": ath.get("displayName"), "team": tm, "opp": other.get(tm),
                       "home": int(tm == ab["home"]), "starter": bool(a.get("starter")), "dnp": dnp,
                       "reason": a.get("reason") if dnp else None, "pos": (ath.get("position") or {}).get("abbreviation"),
                       "min": _num(d.get("MIN")), "reb": _num(d.get("REB")), "oreb": _num(d.get("OREB")),
                       "dreb": _num(d.get("DREB")), "pts": _num(d.get("PTS")), "ast": _num(d.get("AST")),
                       "fg3m": _made(d.get("3PT")),
                       "game": gid, "date": date})
    for t in summary.get("boxscore", {}).get("teams", []) or []:
        tm = teams.code(t["team"]["abbreviation"])
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics", []) or []}

        def pair(k, i):
            try:
                return int(str(s.get(k, "")).split("-")[i])
            except (ValueError, IndexError):
                return None
        tr.append({"team": tm, "opp": other.get(tm), "home": int(tm == ab["home"]), "ot": ot,
                   "reb": _num(s.get("totalRebounds")), "oreb": _num(s.get("offensiveRebounds")),
                   "dreb": _num(s.get("defensiveRebounds")), "ast": _num(s.get("assists")),
                   "fg3m": pair("threePointFieldGoalsMade-threePointFieldGoalsAttempted", 0), "fgm": pair("fieldGoalsMade-fieldGoalsAttempted", 0),
                   "fga": pair("fieldGoalsMade-fieldGoalsAttempted", 1), "fta": pair("freeThrowsMade-freeThrowsAttempted", 1),
                   "tov": _num(s.get("totalTurnovers") or s.get("turnovers")),
                   "pts": _num(comp["home" if tm == ab["home"] else "away"].get("score")), "game": gid, "date": date})
    if len(tr) != 2 or not pr:
        return None, None
    return pr, tr


_SUMMARY = {}                                              # in-run memo: grade's reads are reused by live (no extra calls)


def summary(event_id):
    k = str(event_id)
    if k in _SUMMARY:
        return _SUMMARY[k]
    js = _get("summary?event=%s" % k, "summary_%s.json" % k)
    if js is not None:
        _SUMMARY[k] = js
    return js


def summary_cached(event_id):
    """This run's summary read of a game, or None when it was not read this run. Never calls ESPN."""
    return _SUMMARY.get(str(event_id))


def clear_cache():
    _SUMMARY.clear()


# ---------------------------------------------------------------- live (display only: the page's Live tab)
LIVE_KEYS = {"points": "points", "rebounds": "rebounds", "assists": "assists",
             "threes": "threePointFieldGoalsMade-threePointFieldGoalsAttempted"}
LIVE_LABELS = {"points": "PTS", "rebounds": "REB", "assists": "AST", "threes": "3PT"}


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def game_state(summary):
    """An in-progress (or final) summary -> {state, period, clock, detail, in_break, away {abbrev, score}, home {...}},
    or None when the header is unreadable. Field names checked on real in-progress games (event 401909922, 2026-11-04)."""
    try:
        hdr = summary["header"]["competitions"][0]
        st = hdr.get("status") or {}
        tp = st.get("type") or {}
        side = {c["homeAway"]: c for c in hdr["competitors"]}
        team = lambda ha: {"abbrev": teams.show(teams.code(side[ha]["team"]["abbreviation"]) or side[ha]["team"]["abbreviation"]),
                           "score": _int(side[ha].get("score"))}
        detail = tp.get("detail") or tp.get("shortDetail") or ""
        state = tp.get("state")
        brk = state == "in" and (tp.get("name") in ("STATUS_HALFTIME", "STATUS_END_PERIOD") or
                                 bool(re.search(r"halftime|^end of", detail, re.I)))
        return {"state": state, "completed": bool(tp.get("completed")), "period": _int(st.get("period")),
                "clock": st.get("displayClock") if isinstance(st.get("displayClock"), str) else None,
                "detail": detail or None, "in_break": bool(brk), "away": team("away"), "home": team("home")}
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def player_stats(summary):
    """Any summary (in progress or final) -> {ESPN player id: {"dnp", "points", "rebounds", "assists", "threes"}}. Stats are
    mapped by the index of each block's `keys` (labels as a fallback); threes = the made part of the 3PT key."""
    out = {}
    for p in (summary.get("boxscore") or {}).get("players", []) or []:
        if not isinstance(p, dict):
            continue                                       # one malformed team block never blanks the rest
        st = (p.get("statistics") or [{}])[0] or {}
        if not isinstance(st, dict):
            continue
        keys, labels = st.get("keys") or [], st.get("labels") or []
        idx = {}
        for m, k in LIVE_KEYS.items():
            if k in keys:
                idx[m] = keys.index(k)
            elif LIVE_LABELS[m] in labels:
                idx[m] = labels.index(LIVE_LABELS[m])
        for a in st.get("athletes", []) or []:
            if not isinstance(a, dict):
                continue
            pid = str((a.get("athlete") or {}).get("id"))
            vals = a.get("stats") or []
            dnp = bool(a.get("didNotPlay")) or not vals
            row = {"dnp": dnp}
            for m in LIVE_KEYS:
                i = idx.get(m)
                v = vals[i] if (i is not None and i < len(vals) and not dnp) else None
                row[m] = (_made(v) if m == "threes" else _num(v)) if v is not None else None
                row[m] = int(row[m]) if row[m] is not None else None
            out[pid] = row
    return out


TEAM_IDS = {"ATL": "1", "BOS": "2", "BKN": "17", "CHA": "30", "CHI": "4", "CLE": "5", "DAL": "6", "DEN": "7", "DET": "8",
            "GS": "9", "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29", "MIA": "14", "MIL": "15", "MIN": "16",
            "NO": "3", "NY": "18", "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22", "SAC": "23", "SA": "24",
            "TOR": "28", "UTAH": "26", "WSH": "27"}
