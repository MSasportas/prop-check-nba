import json, sys, gzip, os, statistics, collections
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds, model, names
d = json.load(open(R + "research/alt_probe/2026-10-26_2013.json"))
DISP = {"points": 1.6, "rebounds": 1.15, "assists": 1.0, "threes": 1.15}
ST = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
box = {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")):
            if r["date"] == "2026-10-26": box[names.norm(r["name"])] = r
def mean_for(p_over, line, disp):
    lo, hi = 0.01, 90.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 1 - model.nb_cdf(int(line), mid, disp) < p_over: lo = mid
        else: hi = mid
    return (lo + hi) / 2
rows = []
for g in d["games"]:
    bks = {b["key"]: b for b in (g["odds"] or {}).get("bookmakers", [])}
    pin, hr = bks.get("pinnacle"), bks.get("hardrockbet")
    if not pin or not hr: continue
    pinmain = {}
    for mk in pin["markets"]:
        stat = mk["key"].replace("player_", "")
        pp = collections.defaultdict(dict)
        for o in mk["outcomes"]: pp[(names.norm(o["description"]), o["point"])][o["name"].lower()] = o["price"]
        for (who, line), q in pp.items():
            if "over" in q and "under" in q: pinmain[(stat, who)] = (line, odds.fair_two_sided(q["over"], q["under"]))
    for mk in hr["markets"]:
        stat = mk["key"].replace("player_", "").replace("_alternate", ""); alt = mk["key"].endswith("_alternate")
        for o in mk["outcomes"]:
            if o["name"] != "Over" or o.get("point") is None: continue
            who = names.norm(o["description"]); k = (stat, who)
            if k not in pinmain: continue
            pl, pf = pinmain[k]
            mu = mean_for(pf, pl, DISP[stat])
            fair = 1 - model.nb_cdf(int(o["point"]), mu, DISP[stat]) if o["point"] != pl else pf
            b = box.get(who); res = None
            if b and not b["dnp"] and b.get(ST[stat]) is not None: res = "W" if b[ST[stat]] > o["point"] else "L"
            elif b: res = "V"
            rows.append(dict(stat=stat, who=who, line=o["point"], price=o["price"], alt=alt, exact=o["point"] == pl,
                             fair=fair, ev=odds.ev(fair, o["price"]), res=res))
def summ(label, rs):
    if not rs: print(label, "none"); return
    e = [r["ev"] for r in rs]; w = sum(r["res"] == "W" for r in rs); l = sum(r["res"] == "L" for r in rs)
    u = sum((odds.decimal(r["price"]) - 1) if r["res"] == "W" else (-1 if r["res"] == "L" else 0) for r in rs)
    print("%-44s n %4d | EV median %+6.1f%% best %+6.1f%% | >= +3%%: %3d | graded %d-%d %+.1fu" % (label, len(rs), 100*statistics.median(e), 100*max(e), sum(x >= .03 for x in e), w, l, u))
band = [r for r in rows if -200 <= r["price"] <= 200]
summ("HR overs on Pinnacle's EXACT main line", [r for r in band if r["exact"]])
summ("HR alt overs, -200..+200 (Pinnacle converted)", [r for r in band if r["alt"] and not r["exact"]])
for s in ("points", "rebounds", "assists", "threes"): summ("   " + s, [r for r in band if r["alt"] and not r["exact"] and r["stat"] == s])
summ("HR alt overs longer than +200", [r for r in rows if r["alt"] and r["price"] > 200])
q = [r for r in rows if r["alt"] and r["ev"] >= .03]
summ("ANY HR alt over with EV >= +3% vs Pinnacle", q)
for r in sorted(q, key=lambda r: -r["ev"])[:10]: print("   %-20s %-8s over %4s %+5d  Pin-implied %.1f%%  EV %+.1f%% -> %s" % (r["who"][:20], r["stat"], r["line"], r["price"], 100*r["fair"], 100*r["ev"], r["res"]))
