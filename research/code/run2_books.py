import json, sys, gzip, os, statistics, collections
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds, names
box = {}
NM = {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")): box[(r["game"], r["pid"])] = r; NM[r["pid"]] = r["name"]
STAT = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
def grade(r):
    b = box.get((r["game_id"], r["pid"]))
    if not b: return None
    if b["dnp"] or not b["min"]: return "V"
    x = b.get(STAT[r["market"]])
    if x is None: return None
    if x == r["line"]: return "P"
    return "W" if (x > r["line"]) == (r["side"] == "over") else "L"
rows = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    for rd in json.load(open(R + "data/shadow/%s.json" % day))["reads"]:
        for r in rd["rows"]:
            r.update(day=day, rd=rd["read"], rat=rd["at"]); rows.append(r)
# best (latest B/C/D read) per side
last = {}
for r in rows:
    if r["rd"] in "BCD":
        k = (r["day"], r["game_id"], r["pid"], r["market"], r["line"], r["side"])
        if k not in last or r["rat"] > last[k]["rat"]: last[k] = r
print("graded box rows available:", len(box))
pin = [dict(r, pev=odds.ev(r["pin_fair"], r["price"])) for r in rows if r.get("pin_fair") is not None]
top = sorted(pin, key=lambda r: -r["pev"])
seen = set(); print("Pinnacle-only sides >= +2% (any read):")
for r in top:
    if r["pev"] < 0.02: break
    k = (r["day"], r["pid"], r["market"], r["side"])
    if k in seen: continue
    seen.add(k)
    print("  %s %-5s %+.1f%% vs Pin | median of %d books %+.1f%% | %s %s %s %s %+d -> %s" % (r["day"][5:], r["rd"], 100*r["pev"], r["n_books"], 100*(r["gap_ev"] or 0), NM.get(r["pid"], r["pid"]), r["market"], r["side"], r["line"], r["price"], grade(r)))
# single-book judges, latest B/C/D read per side
D = "/home/claude/prop-check-nba/data/odds/"
judge = collections.defaultdict(list)
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    lastf = {}
    for f in json.load(open(D + day + ".json"))["fetches"]:
        if f["read"] in "BCD": lastf[f["game_id"]] = f
    for f in lastf.values():
        for m, hm in f["markets"].items():
            hp = odds.pairs(hm["outcomes"])
            for book, bm in (f.get("others") or {}).items():
                bp = odds.pairs((bm.get(m) or {}).get("outcomes"))
                for k, p in hp.items():
                    q = bp.get(k)
                    if not (p["over"] and p["under"] and q and q["over"] and q["under"]): continue
                    if not (0 <= odds.hold(q["over"], q["under"]) <= .15): continue
                    fo = odds.fair_two_sided(q["over"], q["under"])
                    for side, pr, fr in (("over", p["over"], fo), ("under", p["under"], 1 - fo)):
                        if -200 <= pr <= 200: judge[book].append(odds.ev(fr, pr))
print("\nHR vs EACH book alone as judge (latest read, same line, -200..+200):")
for b, v in sorted(judge.items(), key=lambda kv: -statistics.median(kv[1])):
    print("  %-11s n %4d  median %+5.1f%%  >= +3%%: %3d  (%.1f%%)" % (b, len(v), 100*statistics.median(v), sum(x >= .03 for x in v), 100*sum(x >= .03 for x in v)/len(v)))
seq = collections.defaultdict(list)
for r in rows:
    if r.get("pin_fair") is not None: seq[(r["day"], r["game_id"], r["pid"], r["market"], r["line"], r["side"])].append(r)
ev = []; pairs_n = 0
for v in seq.values():
    v.sort(key=lambda r: r["rat"])
    for a, b in zip(v, v[1:]):
        pairs_n += 1
        if b["price"] == a["price"] and b["pin_fair"] - a["pin_fair"] >= 0.02:
            ev.append((odds.ev(b["pin_fair"], b["price"]), b))
print("\nPinnacle moved >= 2 pts toward a side, Hard Rock price unchanged: %d of %d pairs" % (len(ev), pairs_n))
for e, b in sorted(ev, key=lambda t: -t[0])[:6]:
    print("  EV vs new Pinnacle %+.1f%%  %s %s %s %s %+d -> %s" % (100*e, NM.get(b["pid"], b["pid"]), b["market"], b["side"], b["line"], b["price"], grade(b)))
