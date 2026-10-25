#!/usr/bin/env python3
"""seed_probe.py: ONE-TIME setup run on a GitHub runner (the build sandbox cannot reach ESPN).

1. seed   every regular-season NBA game box score from ESPN for 2025-26 and 2026-27 so far
          -> data/seed/players_<season>.json.gz  (one row per player per game: min, reb, oreb, dreb, starter, dnp)
          -> data/seed/teams_<season>.json.gz    (one row per team per game: reb, oreb, dreb, fga, fgm, fta, tov, pts, ot)
2. probe  raw samples of every free source the engine may use -> probe/<name>.(json|html|txt) + probe/summary.txt

Standard library only. Usage: python scripts/seed_probe.py [seed] [probe]
"""
import gzip
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
ET = timezone(timedelta(hours=-4))


def get(url, timeout=30, tries=3, raw=False):
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
            b = r.read()
            return (r.status, b) if raw else json.loads(b)
        except Exception as e:
            if i == tries - 1:
                return (str(e)[:120], b"") if raw else None
            time.sleep(2 + 3 * i)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def box(summary):
    """ESPN summary -> (player rows, team rows). Regular season final games only."""
    hdr = summary["header"]["competitions"][0]
    comp = {c["homeAway"]: c for c in hdr["competitors"]}
    ab = {ha: comp[ha]["team"]["abbreviation"] for ha in ("home", "away")}
    tid = {ha: comp[ha]["team"]["id"] for ha in ("home", "away")}
    other = {ab["home"]: ab["away"], ab["away"]: ab["home"]}
    ot = max(0, max(len(comp[ha].get("linescores", []) or []) for ha in ab) - 4)
    when = summary["header"].get("competitions", [{}])[0].get("date")
    pr, tr = [], []
    for p in summary.get("boxscore", {}).get("players", []) or []:
        tm = p["team"]["abbreviation"]
        st = (p.get("statistics") or [{}])[0]
        lab = st.get("labels") or st.get("names") or []
        for a in st.get("athletes", []) or []:
            ath = a.get("athlete") or {}
            d = dict(zip(lab, a.get("stats") or []))
            mn = num(d.get("MIN"))
            dnp = bool(a.get("didNotPlay")) or not a.get("stats")
            pr.append({"pid": str(ath.get("id")), "name": ath.get("displayName"), "team": tm, "opp": other.get(tm),
                       "home": int(tm == ab["home"]), "starter": bool(a.get("starter")), "dnp": dnp,
                       "reason": a.get("reason") if dnp else None, "pos": (ath.get("position") or {}).get("abbreviation"),
                       "min": mn, "reb": num(d.get("REB")), "oreb": num(d.get("OREB")), "dreb": num(d.get("DREB"))})
    for t in summary.get("boxscore", {}).get("teams", []) or []:
        tm = t["team"]["abbreviation"]
        s = {x.get("name"): x.get("displayValue") for x in t.get("statistics", []) or []}

        def pair(k, i):
            try:
                return int(str(s.get(k, "")).split("-")[i])
            except (ValueError, IndexError):
                return None
        tr.append({"team": tm, "opp": other.get(tm), "home": int(tm == ab["home"]), "ot": ot,
                   "reb": num(s.get("totalRebounds")), "oreb": num(s.get("offensiveRebounds")),
                   "dreb": num(s.get("defensiveRebounds")), "fgm": pair("fieldGoalsMade-fieldGoalsAttempted", 0),
                   "fga": pair("fieldGoalsMade-fieldGoalsAttempted", 1),
                   "fta": pair("freeThrowsMade-freeThrowsAttempted", 1),
                   "tov": num(s.get("totalTurnovers") or s.get("turnovers")),
                   "pts": num(comp["home" if tm == ab["home"] else "away"].get("score"))})
    return when, pr, tr


def seed_season(label, start, end):
    players, teams, games = [], [], 0
    d = start
    while d <= end:
        sb = get("%s/scoreboard?dates=%s&limit=50" % (ESPN, d.strftime("%Y%m%d")))
        for e in (sb or {}).get("events", []) or []:
            if (e.get("season") or {}).get("type") != 2 or not e["status"]["type"].get("completed"):
                continue
            s = get("%s/summary?event=%s" % (ESPN, e["id"]))
            if not s:
                print("summary failed", e["id"], flush=True)
                continue
            try:
                when, pr, tr = box(s)
            except Exception as ex:
                print("box failed", e["id"], ex, flush=True)
                continue
            for r in pr + tr:
                r["game"], r["date"], r["start"] = e["id"], d.isoformat(), e.get("date")
            players += pr
            teams += tr
            games += 1
        d += timedelta(days=1)
    os.makedirs(os.path.join(ROOT, "data", "seed"), exist_ok=True)
    for nm, rows in (("players", players), ("teams", teams)):
        with gzip.open(os.path.join(ROOT, "data", "seed", "%s_%s.json.gz" % (nm, label)), "wt", encoding="utf-8") as f:
            json.dump(rows, f, separators=(",", ":"))
    print("seed %s: %d games, %d player rows, %d team rows" % (label, games, len(players), len(teams)), flush=True)
    return games


def probe():
    out = os.path.join(ROOT, "probe")
    os.makedirs(out, exist_ok=True)
    lines = []

    def save(name, status, body):
        with open(os.path.join(out, name), "wb") as f:
            f.write(body[:3_000_000])
        lines.append("%-28s %s %d bytes" % (name, status, len(body)))

    today = datetime.now(ET).date()
    st, b = get("%s/scoreboard?dates=%s" % (ESPN, today.strftime("%Y%m%d")), raw=True)
    save("scoreboard_today.json", st, b)
    try:
        evs = json.loads(b)["events"]
    except Exception:
        evs = []
    if evs:
        st, b = get("%s/summary?event=%s" % (ESPN, evs[-1]["id"]), raw=True)
        save("summary_pregame.json", st, b)
    y = today - timedelta(days=1)
    st, b = get("%s/scoreboard?dates=%s" % (ESPN, y.strftime("%Y%m%d")), raw=True)
    try:
        fin = [e for e in json.loads(b)["events"] if e["status"]["type"]["completed"]]
    except Exception:
        fin = []
    if fin:
        st, b = get("%s/summary?event=%s" % (ESPN, fin[0]["id"]), raw=True)
        save("summary_final.json", st, b)
    for nm, url in [
        ("injuries.json", ESPN + "/injuries"),
        ("teams.json", ESPN + "/teams"),
        ("roster_bos.json", ESPN + "/teams/2/roster"),
        ("rotowire_lineups.html", "https://www.rotowire.com/basketball/nba-lineups.php"),
        ("rotowire_injuries.html", "https://www.rotowire.com/basketball/injury-report.php"),
        ("nba_injury_report_page.html", "https://official.nba.com/nba-injury-report-2026-27-season/"),
        ("cbs_injuries.html", "https://www.cbssports.com/nba/injuries/"),
        ("espn_injuries_page.html", "https://www.espn.com/nba/injuries"),
        ("covers_injuries.html", "https://www.covers.com/sport/basketball/nba/injuries"),
    ]:
        st, b = get(url, raw=True)
        save(nm, st, b)
    # the official NBA injury report PDF: try today's most recent half-hour slots
    now = datetime.now(ET)
    for back in range(0, 8):
        t = now - timedelta(minutes=30 * back)
        slot = t.replace(minute=0 if t.minute < 30 else 30)
        hh = slot.hour % 12 or 12
        url = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_%s_%02d_%02d%s.pdf" % (
            slot.date().isoformat(), hh, slot.minute, "AM" if slot.hour < 12 else "PM")
        st, b = get(url, raw=True, tries=1)
        lines.append("injury pdf %s -> %s %d bytes" % (url.rsplit("/", 1)[1], st, len(b)))
        if st == 200:
            save("nba_injury_report.pdf", st, b)
            break
    with open(os.path.join(out, "summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    what = set(sys.argv[1:]) or {"seed", "probe"}
    if "probe" in what:
        probe()
    if "seed" in what:
        seed_season("2025-26", date(2025, 10, 21), date(2026, 4, 12))
        seed_season("2026-27", date(2026, 10, 20), datetime.now(ET).date() - timedelta(days=1))
