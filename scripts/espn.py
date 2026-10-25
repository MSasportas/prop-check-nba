"""espn.py: ESPN's public NBA JSON (no key). Schedule, rosters, injuries and box scores.

Only the GitHub runner can reach ESPN (the build sandbox cannot). With PC_ESPN_FIXTURE_DIR set every call reads a saved file:
scoreboard_<YYYYMMDD>.json, summary_<event>.json, injuries.json, roster_<CODE>.json.
"""
import json
import os

import common
import teams

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SOURCE = {"ok": 0, "failed": 0}


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
    """Team code -> [{"pid", "name", "team", "pos", "injury"}] or None."""
    tid = TEAM_IDS.get(code)
    if not tid:
        return None
    js = _get("teams/%s/roster" % tid, "roster_%s.json" % code)
    if js is None:
        return None
    out = []
    for a in js.get("athletes", []) or []:
        inj = (a.get("injuries") or [{}])[0].get("status") if a.get("injuries") else None
        out.append({"pid": str(a.get("id")), "name": a.get("displayName") or a.get("fullName"), "team": code,
                    "pos": (a.get("position") or {}).get("abbreviation"), "injury": inj})
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
                       "dreb": _num(d.get("DREB")), "game": gid, "date": date})
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
                   "dreb": _num(s.get("defensiveRebounds")), "fgm": pair("fieldGoalsMade-fieldGoalsAttempted", 0),
                   "fga": pair("fieldGoalsMade-fieldGoalsAttempted", 1), "fta": pair("freeThrowsMade-freeThrowsAttempted", 1),
                   "tov": _num(s.get("totalTurnovers") or s.get("turnovers")),
                   "pts": _num(comp["home" if tm == ab["home"] else "away"].get("score")), "game": gid, "date": date})
    if len(tr) != 2 or not pr:
        return None, None
    return pr, tr


def summary(event_id):
    return _get("summary?event=%s" % event_id, "summary_%s.json" % event_id)


TEAM_IDS = {"ATL": "1", "BOS": "2", "BKN": "17", "CHA": "30", "CHI": "4", "CLE": "5", "DAL": "6", "DEN": "7", "DET": "8",
            "GS": "9", "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29", "MIA": "14", "MIL": "15", "MIN": "16",
            "NO": "3", "NY": "18", "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22", "SAC": "23", "SA": "24",
            "TOR": "28", "UTAH": "26", "WSH": "27"}
