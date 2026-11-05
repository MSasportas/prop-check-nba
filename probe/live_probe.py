"""One-time source probe (2026-11-04, page redesign): which free live box score and headshot sources the GitHub runner
can reach, and their real field names on games in progress. Writes probe/live/ (uploaded as an artifact, not committed)."""
import json, os, re, urllib.request, urllib.error

OUT = "probe/live"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (prop-check probe)", "Accept": "application/json, text/html, */*",
      "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com"}
log = []


def get(url, binary=False, limit=None):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read()
            log.append({"url": url, "code": r.status, "bytes": len(b), "type": r.headers.get("Content-Type")})
            return b
    except urllib.error.HTTPError as e:
        log.append({"url": url, "code": e.code})
    except Exception as e:  # noqa
        log.append({"url": url, "error": repr(e)[:200]})
    return None


def save(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1)


ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
sb = get(ESPN + "/scoreboard?limit=50")
events = json.loads(sb)["events"] if sb else []
live = [e for e in events if e["status"]["type"]["state"] == "in"] + [e for e in events if e["status"]["type"]["state"] == "post"]
save("espn_scoreboard_status.json", [{"id": e["id"], "name": e.get("shortName"), "status": e["status"]} for e in events])
for e in live[:2]:
    s = get(ESPN + "/summary?event=" + e["id"])
    if not s:
        continue
    js = json.loads(s)
    comp = js["header"]["competitions"][0]
    bp = js.get("boxscore", {}).get("players", [])
    trimmed = {"header_status": comp.get("status"),
               "competitors": [{k: c.get(k) for k in ("homeAway", "score", "id")} | {"abbr": c["team"].get("abbreviation")} for c in comp["competitors"]],
               "players": [{"team": t["team"].get("abbreviation"),
                            "stat_block_keys": list(t["statistics"][0].keys()),
                            "names": t["statistics"][0].get("names"), "keys": t["statistics"][0].get("keys"),
                            "labels": t["statistics"][0].get("labels"),
                            "athletes": t["statistics"][0]["athletes"][:3]} for t in bp]}
    save("espn_summary_%s_%s.json" % (e["status"]["type"]["state"], e["id"]), trimmed)

# NBA official (cdn.nba.com, stats.nba.com, nba.com)
ts = get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
gid = None
if ts:
    g = json.loads(ts)["scoreboard"]["games"]
    save("nba_scoreboard.json", [{k: x.get(k) for k in ("gameId", "gameStatus", "gameStatusText", "period", "gameClock", "gameCode")} for x in g])
    inn = [x for x in g if x.get("gameStatus") == 2] or g
    gid = inn[0]["gameId"] if inn else None
if gid:
    bx = get("https://cdn.nba.com/static/json/liveData/boxscore/boxscore_%s.json" % gid)
    if bx:
        game = json.loads(bx)["game"]
        save("nba_boxscore.json", {"game_keys": list(game.keys()), "gameStatus": game.get("gameStatus"), "period": game.get("period"),
                                    "gameClock": game.get("gameClock"), "home_keys": list(game["homeTeam"].keys()),
                                    "player0": game["homeTeam"]["players"][0]})
get("https://cdn.nba.com/headshots/nba/latest/260x190/1630178.png", binary=True)
get("https://cdn.nba.com/headshots/nba/latest/1040x760/1630178.png", binary=True)
get("https://stats.nba.com/stats/playerindex?LeagueID=00&Season=2026-27&Historical=0")
get("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json")
pl = get("https://www.nba.com/players")
if pl:
    m = re.search(rb'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', pl, re.S)
    if m:
        nd = json.loads(m.group(1))
        props = nd.get("props", {}).get("pageProps", {})
        save("nba_players_page.json", {"pageProps_keys": list(props.keys()),
                                       "sample": (props.get("players") or [None])[:2], "n": len(props.get("players") or [])})
# ESPN headshot CDN (fallback idea) and ESPN athlete record (does it carry an NBA id?)
get("https://a.espncdn.com/i/headshots/nba/players/full/4278104.png", binary=True)
ath = get("https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/4278104")
if ath:
    a = json.loads(ath)
    save("espn_athlete.json", {k: a.get(k) for k in ("id", "uid", "guid", "alternateIds", "externalIds", "displayName", "headshot")})
save("log.json", log)
print(json.dumps(log, indent=1))
