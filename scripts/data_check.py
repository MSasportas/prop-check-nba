"""Probe free data sources from a GitHub Actions runner. Prints a table."""
import json, sys, time, urllib.request, datetime as dt

H = {"User-Agent": "Mozilla/5.0 prop-check-nba"}

def get(url, timeout=25, rng=None):
    h = dict(H)
    if rng: h["Range"] = rng
    t = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
        b = r.read(2_000_000)
        return r.status, b, round(time.time() - t, 1)
    except Exception as e:
        return str(e)[:80], b"", round(time.time() - t, 1)

today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).strftime("%Y%m%d")
rows = []
def rec(name, ok, note): rows.append((name, "WORKS" if ok else "FAILS", note)); print(rows[-1], flush=True)

ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
s, b, t = get(f"{ESPN}/scoreboard?dates={today}")
ev = []
try:
    j = json.loads(b); ev = j.get("events", [])
except Exception: pass
rec("ESPN scoreboard (today)", bool(ev), f"{s}, {len(ev)} games, {t}s")
if ev:
    e = ev[0]; c = e["competitions"][0]
    odds = c.get("odds")
    rec("ESPN spread in scoreboard", bool(odds), json.dumps(odds[0])[:140] if odds else "no odds field")
    rec("ESPN game start times", bool(e.get("date")), f"{[x['date'] for x in ev][:3]}")
    eid = e["id"]
    s, b, t = get(f"{ESPN}/summary?event={eid}")
    try:
        j = json.loads(b)
        rec("ESPN summary (event)", True, f"{s}, keys={list(j)[:8]}")
        rec("ESPN summary odds/pickcenter", bool(j.get("pickcenter") or j.get("odds")), json.dumps(j.get("pickcenter", j.get("odds")))[:140])
        rec("ESPN summary injuries", "injuries" in j, f"{len(j.get('injuries', []))} team blocks")
    except Exception as ex:
        rec("ESPN summary (event)", False, f"{s} {ex}")
s, b, t = get(f"{ESPN}/injuries")
try:
    j = json.loads(b); n = sum(len(x.get("injuries", [])) for x in j.get("injuries", []))
    ex = (j["injuries"][0]["injuries"][0] if n else {})
    rec("ESPN injuries (league)", n > 0, f"{n} entries; sample={json.dumps({k: ex.get(k) for k in ('status','date')})} {ex.get('athlete',{}).get('displayName')}")
except Exception as ex:
    rec("ESPN injuries (league)", False, f"{s} {ex}")
yday = (dt.datetime.now() - dt.timedelta(days=1)).strftime("%Y%m%d")
s, b, t = get(f"{ESPN}/scoreboard?dates={yday}")
try:
    j = json.loads(b); evs = j["events"]
    fin = [x for x in evs if x["status"]["type"]["completed"]]
    rec("ESPN scoreboard (yesterday, final)", bool(fin), f"{len(fin)} final")
    if fin:
        s, b, t = get(f"{ESPN}/summary?event={fin[0]['id']}")
        j = json.loads(b)
        pl = j.get("boxscore", {}).get("players", [])
        a = pl[0]["statistics"][0] if pl else {}
        rec("ESPN box score (pts, min)", bool(pl), f"labels={a.get('labels')}")
except Exception as ex:
    rec("ESPN scoreboard (yesterday, final)", False, f"{s} {ex}")
s, b, t = get(f"{ESPN}/teams")
rec("ESPN teams", s == 200, f"{s}")
s, b, t = get(f"{ESPN}/standings") 
rec("ESPN standings", s == 200, f"{s}")
s, b, t = get("https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings")
rec("ESPN standings (site.web)", s == 200, f"{s}")
# NBA
s, b, t = get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
rec("cdn.nba.com todaysScoreboard", s == 200, f"{s} {t}s")
s, b, t = get("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json")
rec("cdn.nba.com schedule", s == 200, f"{s} {t}s")
s, b, t = get("https://stats.nba.com/stats/scoreboardv2?GameDate=2026-10-20&LeagueID=00&DayOffset=0", timeout=15)
rec("stats.nba.com", s == 200, f"{s}")
# last-season baseline
for nm, url in [("raw.githubusercontent shufinskiy README", "https://raw.githubusercontent.com/shufinskiy/nba_data/main/README.md"),
                ("github shufinskiy cdnnba_2025.tar.xz", "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2025.tar.xz")]:
    s, b, t = get(url, timeout=60, rng="bytes=0-1000000")
    rec(nm, s in (200, 206), f"{s}, {len(b)} bytes in {t}s")
print("\n| Source | Status | Note |\n|---|---|---|")
for r in rows: print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
