import json, urllib.request, os
H={"User-Agent":"Mozilla/5.0"}
E="https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
def g(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())
os.makedirs("samples",exist_ok=True)
def save(n,o): json.dump(o,open(f"samples/{n}.json","w"))
sb=g(f"{E}/scoreboard?dates=20261020"); save("scoreboard",sb)
for i,e in enumerate(sb["events"]): save(f"summary_today{i}",g(f"{E}/summary?event={e['id']}"))
save("injuries",g(f"{E}/injuries"))
save("roster_bos",g(f"{E}/teams/bos/roster"))
save("teams",g(f"{E}/teams"))
# a completed game: preseason last week, else last season finals
for d in ["20261017","20261016","20260615"]:
    s=g(f"{E}/scoreboard?dates={d}")
    fin=[e for e in s["events"] if e["status"]["type"]["completed"]]
    if fin:
        save("scoreboard_done",s); save("summary_done",g(f"{E}/summary?event={fin[0]['id']}")); break
