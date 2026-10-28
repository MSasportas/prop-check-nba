import json, sys, gzip, os, collections, statistics
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds
box, NM = {}, {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")): box[(r["game"], r["pid"])] = r; NM[r["pid"]] = r["name"]
STAT = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
def grade(gid, pid, m, line, side):
    b = box.get((gid, pid))
    if not b: return "?"
    if b["dnp"] or not b["min"]: return "V"
    x = b.get(STAT[m])
    if x is None: return "?"
    return "P" if x == line else ("W" if (x > line) == (side == "over") else "L")
def fair_over(q): return odds.fair_two_sided(q["over"], q["under"]) if q and q["over"] and q["under"] and 0 <= odds.hold(q["over"], q["under"]) <= .15 else None
ev = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    d = json.load(open(R + "data/odds/%s.json" % day)); byg = collections.defaultdict(list)
    for f in sorted(d["fetches"], key=lambda f: f["at"]): byg[f["game_id"]].append(f)
    for gid, fs in byg.items():
        for a, b in zip(fs, fs[1:]):
            for m in b["markets"]:
                ha = odds.pairs((a["markets"].get(m) or {}).get("outcomes")); hb = odds.pairs(b["markets"][m]["outcomes"])
                def bk(f, book): return odds.pairs((((f.get("others") or {}).get(book) or {}).get(m) or {}).get("outcomes"))
                pa, pb = bk(a, "pinnacle"), bk(b, "pinnacle")
                for k, h in hb.items():
                    if k not in ha or not (h["over"] and h["under"]): continue
                    fa, fb = fair_over(pa.get(k)), fair_over(pb.get(k))
                    if fa is None or fb is None or abs(fb - fa) < 0.02: continue
                    mv = []
                    for book in (b.get("others") or {}):
                        if book == "pinnacle": continue
                        x, y = fair_over(bk(a, book).get(k)), fair_over(bk(b, book).get(k))
                        if x is not None and y is not None: mv.append(y - x)
                    side = "over" if fb > fa else "under"
                    pin_side = fb if side == "over" else 1 - fb
                    hr_same = ha[k][side] == h[side]
                    ev.append(dict(day=day, who=NM.get(k[0], k[0]), m=m, line=k[1], side=side, pin_move=abs(fb - fa),
                                   others=statistics.median([x if side == "over" else -x for x in mv]) if mv else None, n_oth=len(mv),
                                   hr_same=hr_same, price=h[side], pev=odds.ev(pin_side, h[side]), res=grade(gid, k[0], m, k[1], side)))
print("Pinnacle moved >= 2 pts between two of our reads: %d times" % len(ev))
alone = [e for e in ev if e["others"] is not None and e["others"] < 0.01]
print("  ...and the other books (median) moved < 1 pt the same way: %d" % len(alone))
print("  ...and Hard Rock's price on that side did not change: %d" % sum(e["hr_same"] for e in alone))
print("  ...and Hard Rock's price was +2%% or better vs Pinnacle's new number: %d" % sum(e["hr_same"] and e["pev"] >= .02 for e in alone))
res = collections.Counter(e["res"] for e in alone); print("  results of all 'Pinnacle moved alone' sides (bet the side Pinnacle moved to, at HR):", dict(res))
u = sum(odds.decimal(e["price"]) - 1 if e["res"] == "W" else (-1 if e["res"] == "L" else 0) for e in alone)
print("  units if bet every one at Hard Rock's price: %+.2f on %d bets" % (u, sum(e['res'] in 'WL' for e in alone)))
for e in sorted(alone, key=lambda e: -e["pev"]):
    print("   %s %-22s %-8s %-5s %5s HR %+4d | Pin moved %.1f pts, others %+.1f | HR same %s | EV vs Pin %+.1f%% -> %s" % (e["day"][5:], e["who"][:22], e["m"], e["side"], e["line"], e["price"], 100*e["pin_move"], 100*e["others"], "Y" if e["hr_same"] else "n", 100*e["pev"], e["res"]))
