#!/usr/bin/env bash
# One-time check (2026-11-04): can a phone browser on msasportas.github.io read the live feeds directly (CORS)?
O="Origin: https://msasportas.github.io"
UA="User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
D=$(TZ=America/New_York date +%Y%m%d)
EV=$(curl -s "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=$D" | python3 -c "import json,sys;e=json.load(sys.stdin)['events'];print(next((x['id'] for x in e if x['status']['type']['state']=='in'), e[0]['id']))")
for u in "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=$D" \
         "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=$EV" \
         "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json" \
         "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022600150.json"; do
  echo "=== GET $u"
  curl -s -o /dev/null -D - -m 20 -H "$O" -H "$UA" "$u" | grep -i -E "^HTTP|access-control|cache-control|^age|content-type|server" 
  echo "=== OPTIONS (preflight) $u"
  curl -s -o /dev/null -D - -m 20 -X OPTIONS -H "$O" -H "$UA" -H "Access-Control-Request-Method: GET" "$u" | grep -i -E "^HTTP|access-control"
done
