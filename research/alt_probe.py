#!/usr/bin/env python3
"""research/alt_probe.py: ONE-TIME research read (Matt, 2026-10-26): main + alternate ladders for points, rebounds, assists from Hard Rock
and the 9 other books, for every game that has not started. Research only: never touches picks, the Record or the page.
Cost: 6 markets x 1 region = up to 6 credits a game. Keys from env ODDS_API_KEYS(_2); never printed or written.
Writes research/alt_probe/<date>_<HHMM>.json (feed payloads, keys never included)."""
import json, os, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

API = "https://api.the-odds-api.com/v4/sports/basketball_nba"
BOOKS = "hardrockbet,draftkings,fanduel,betmgm,espnbet,pinnacle,betonlineag,betrivers,novig,prophetx"
MARKETS = ("player_points,player_rebounds,player_assists,"
           "player_points_alternate,player_rebounds_alternate,player_assists_alternate")
keys = [k.strip() for v in ("ODDS_API_KEYS", "ODDS_API_KEYS_2") for k in os.environ.get(v, "").replace("\n", ",").split(",") if k.strip()]


def get(path, params):
    for i, k in enumerate(keys):
        q = urllib.parse.urlencode(dict(params, apiKey=k))
        try:
            with urllib.request.urlopen(API + path + "?" + q, timeout=30) as r:
                left = r.headers.get("x-requests-remaining")
                if left is not None and float(left) < 12:
                    continue
                return json.loads(r.read()), r.headers.get("x-requests-last"), i + 1
        except urllib.error.HTTPError as e:
            print("key %d answered %d" % (i + 1, e.code))
            if e.code in (401, 429):
                continue
            return None, None, i + 1
    return None, None, None


now = datetime.now(timezone.utc)
events, _, _ = get("/events", {"dateFormat": "iso"})
todo = [e for e in events or [] if datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) > now + timedelta(minutes=3)
        and datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) < now + timedelta(hours=8)]
out = {"at": now.isoformat(), "markets": MARKETS, "books": BOOKS, "games": []}
for e in todo:
    js, cost, kn = get("/events/%s/odds" % e["id"], {"regions": "us", "bookmakers": BOOKS, "markets": MARKETS,
                                                      "oddsFormat": "american", "dateFormat": "iso"})
    print("%s @ %s: cost %s (key %s), books %d" % (e["away_team"], e["home_team"], cost, kn, len((js or {}).get("bookmakers", []))))
    out["games"].append({"event": e, "cost": cost, "odds": js})
os.makedirs("research/alt_probe", exist_ok=True)
fn = "research/alt_probe/%s.json" % datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d_%H%M")
json.dump(out, open(fn, "w"), separators=(",", ":"))
print("wrote", fn)
