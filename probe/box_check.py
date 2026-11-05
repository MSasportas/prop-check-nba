"""Throwaway (2026-11-04): ESPN box score points/reb/ast/3PM for finished games, plus tries at the official NBA box."""
import json, urllib.request
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
            return r.status, r.read()
    except Exception as e:
        return repr(e)[:120], None
c, b = get(ESPN + "/scoreboard?dates=20261104")
ev = json.loads(b)["events"]
for e in ev:
    if e["status"]["type"]["state"] != "post":
        continue
    c, s = get(ESPN + "/summary?event=" + e["id"])
    js = json.loads(s)
    print("GAME", e["id"], e["shortName"], e["status"]["type"]["detail"])
    for t in js["boxscore"]["players"]:
        st = t["statistics"][0]; k = st["keys"]
        for a in st["athletes"]:
            v = a.get("stats") or []
            if not v:
                print("  %s|%s|DNP" % (t["team"]["abbreviation"], a["athlete"]["displayName"])); continue
            g = lambda key: v[k.index(key)]
            print("  %s|%s|PTS %s|REB %s|AST %s|3PT %s" % (t["team"]["abbreviation"], a["athlete"]["displayName"], g("points"),
                  g("rebounds"), g("assists"), g("threePointFieldGoalsMade-threePointFieldGoalsAttempted")))
for u in ["https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
          "https://www.basketball-reference.com/boxscores/202611040DET.html"]:
    print("TRY", u, get(u)[0])
