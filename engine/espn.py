"""ESPN public endpoints (no key). Fetch + parse into plain rows."""
import json, time, urllib.request, unicodedata, re

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
HDR = {"User-Agent": "Mozilla/5.0 prop-check-nba"}
# ESPN abbreviation -> NBA tricode (baseline uses NBA tricodes)
ABBR = {"GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def tri(a):
    return ABBR.get(a, a)


def get(path, tries=3):
    url = path if path.startswith("http") else f"{BASE}/{path}"
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30)
            return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 + 3 * i)


def name_i(display):
    """'Shai Gilgeous-Alexander' -> 's. gilgeous-alexander' (matches cdn.nba playerNameI, normalized)."""
    parts = display.strip().split(" ", 1)
    s = f"{parts[0][0]}. {parts[1]}" if len(parts) == 2 else display
    return norm(s)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z. -]", "", s).strip()


def scoreboard(date):
    """date YYYYMMDD -> list of games (regular season only)."""
    out = []
    for e in get(f"scoreboard?dates={date}").get("events", []):
        if e.get("season", {}).get("type") != 2:
            continue
        c = e["competitions"][0]
        t = {x["homeAway"]: x for x in c["competitors"]}
        out.append(dict(id=e["id"], date_utc=e["date"], state=e["status"]["type"]["state"],
                        completed=e["status"]["type"]["completed"],
                        home=tri(t["home"]["team"]["abbreviation"]), away=tri(t["away"]["team"]["abbreviation"]),
                        home_id=t["home"]["team"]["id"], away_id=t["away"]["team"]["id"]))
    return out


def spread(summary):
    """Absolute game spread from ESPN pickcenter (DraftKings). None if missing."""
    for src in (summary.get("pickcenter") or []) + (summary.get("odds") or []):
        v = src.get("spread")
        if v is not None:
            try:
                return abs(float(v)), src.get("details", "")
            except (TypeError, ValueError):
                pass
    return None, ""


def roster(team_id):
    """-> list of dict(espn_id, name, status) where status is the ESPN injury status or ''."""
    r = get(f"teams/{team_id}/roster")
    out = []
    for a in r.get("athletes", []):
        inj = a.get("injuries") or []
        st = inj[0].get("status", "") if inj else ""
        out.append(dict(espn_id=str(a["id"]), name=a.get("displayName", ""), status=st))
    return out


def box(summary, game_id, date_et):
    """Completed game summary -> (player rows, team rows) in baseline format."""
    h = summary["header"]["competitions"][0]
    comp = {c["homeAway"]: c for c in h["competitors"]}
    teams = {ha: tri(comp[ha]["team"]["abbreviation"]) for ha in ("home", "away")}
    score = {teams[ha]: int(comp[ha]["score"]) for ha in teams}
    n_ot = max(0, max(len(comp[ha].get("linescores", [])) for ha in teams) - 4)
    other = {teams["home"]: teams["away"], teams["away"]: teams["home"]}
    prow, trow = [], []
    for p in summary["boxscore"]["players"]:
        tm = tri(p["team"]["abbreviation"])
        st = p["statistics"][0]
        lab = st["labels"]
        for a in st["athletes"]:
            if a.get("didNotPlay") or not a.get("stats"):
                continue
            d = dict(zip(lab, a["stats"]))
            try:
                mn = float(d.get("MIN", "0") or 0)
                pts = int(d.get("PTS", "0") or 0)
            except ValueError:
                continue
            if mn <= 0:
                continue
            prow.append(dict(season=2026, gameId=str(game_id), date=date_et, pid=f"espn{a['athlete']['id']}",
                             team=tm, opp=other[tm], home=int(tm == teams["home"]), min=mn, pts=pts,
                             name=a["athlete"]["displayName"]))
    for t in summary["boxscore"]["teams"]:
        tm = tri(t["team"]["abbreviation"])
        s = {x["name"]: x["displayValue"] for x in t["statistics"]}
        fga = int(s["fieldGoalsMade-fieldGoalsAttempted"].split("-")[1])
        fta = int(s["freeThrowsMade-freeThrowsAttempted"].split("-")[1])
        orb = int(s.get("offensiveRebounds", 0))
        tov = int(s.get("totalTurnovers", s.get("turnovers", 0)))
        trow.append(dict(season=2026, gameId=str(game_id), date=date_et, team=tm, opp=other[tm],
                         home=int(tm == teams["home"]), pts=score[tm], poss=fga + 0.44 * fta - orb + tov, n_ot=n_ot))
    return prow, trow
