import json, sys, collections, statistics, gzip, os
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds
SB = ["draftkings", "fanduel", "betmgm", "espnbet", "pinnacle", "betonlineag", "betrivers"]
EX = ["novig", "prophetx"]
box = {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")): box[r["pid"], r["date"]] = r
ST = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
def mainline(pairs_):
    best = {}
    for (pid, line), p in pairs_.items():
        if not (p["over"] and p["under"]): continue
        g = abs(odds.fair_two_sided(p["over"], p["under"]) - .5)
        if pid not in best or g < best[pid][0]: best[pid] = (g, line)
    return {k: v[1] for k, v in best.items()}
def P(f, book, m):
    src = (f["markets"].get(m) or {}) if book == "hardrockbet" else ((((f.get("others") or {}).get(book) or {}).get(m)) or {})
    return odds.pairs(src.get("outcomes"))
out = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    d = json.load(open(R + "data/odds/%s.json" % day)); byg = collections.defaultdict(list)
    for f in sorted(d["fetches"], key=lambda f: f["at"]): byg[f["game_id"]].append(f)
    for gid, fs in byg.items():
        for a, b in zip(fs, fs[1:]):
            for m in b["markets"]:
                ha, hb = P(a, "hardrockbet", m), P(b, "hardrockbet", m)
                hma, hmb = mainline(ha), mainline(hb)
                mla = {bk: mainline(P(a, bk, m)) for bk in SB}; mlb = {bk: mainline(P(b, bk, m)) for bk in SB}
                for pid, hl in hmb.items():
                    if hma.get(pid) != hl: continue                   # Hard Rock kept its line
                    ups = downs = n = 0
                    for bk in SB:
                        if pid in mla[bk] and pid in mlb[bk]:
                            n += 1; dl = mlb[bk][pid] - mla[bk][pid]
                            ups += dl > 0; downs += dl < 0
                    if n < 3 or (ups < 2 and downs < 2) or (ups and downs): continue   # >= 2 books moved the line, all one way
                    side = "over" if ups else "under"
                    pa_, pb_ = ha[(pid, hl)][side], hb[(pid, hl)][side]
                    # fair at HR's line after the move: exchanges' two-sided ladder at that exact line
                    fairs = []
                    for bk in EX + SB:
                        q = P(b, bk, m).get((pid, hl))
                        if q and q["over"] and q["under"] and 0 <= odds.hold(q["over"], q["under"]) <= .15:
                            fo = odds.fair_two_sided(q["over"], q["under"]); fairs.append(fo if side == "over" else 1 - fo)
                    bx = box.get((pid, day))
                    if not bx or bx["dnp"] or bx.get(ST[m]) is None: res = "V"
                    else:
                        x = bx[ST[m]]; res = "P" if x == hl else ("W" if (x > hl) == (side == "over") else "L")
                    out.append(dict(day=day, m=m, who=(bx or {}).get("name", pid), hl=hl, side=side, books=ups or downs, n=n,
                                    before=pa_, after=pb_, odds_moved=pa_ != pb_, fair=statistics.median(fairs) if fairs else None,
                                    nf=len(fairs), res=res))
seen = {}
for o in out:                                   # one bet per player/market/day: the first time it happened
    seen.setdefault((o["day"], o["who"], o["m"]), o)
bets = list(seen.values())
def rec(bs):
    w = sum(b["res"] == "W" for b in bs); l = sum(b["res"] == "L" for b in bs)
    u = sum((odds.decimal(b["after"]) - 1) if b["res"] == "W" else (-1 if b["res"] == "L" else 0) for b in bs)
    evs = [odds.ev(b["fair"], b["after"]) for b in bs if b["fair"] is not None]
    return "%d bets, %d-%d, %+.2fu | EV vs fair at HR's line: median %s, >= +3%%: %d of %d" % (
        len(bs), w, l, u, ("%+.1f%%" % (100*statistics.median(evs))) if evs else "-", sum(e >= .03 for e in evs), len(evs))
print("Other books moved the LINE (>= 2 books, same direction), Hard Rock kept its line. Bet the move's direction at HR's line:")
print("  ALL:                  ", rec(bets))
print("  HR odds unchanged:    ", rec([b for b in bets if not b["odds_moved"]]))
print("  HR odds moved (juiced):", rec([b for b in bets if b["odds_moved"]]))
for s in ("over", "under"): print("  %-21s " % (s + ":"), rec([b for b in bets if b["side"] == s]))
for m in ("points", "rebounds", "assists", "threes"): print("  %-21s " % (m + ":"), rec([b for b in bets if b["m"] == m]))
print("examples:")
for b in sorted(bets, key=lambda b: -(odds.ev(b["fair"], b["after"]) if b["fair"] is not None else -9))[:8]:
    print("   %s %-20s %-8s %s %s HR %+d -> %+d | %d of %d books moved | fair %s | %s" % (b["day"][5:], b["who"][:20], b["m"], b["side"], b["hl"], b["before"], b["after"], b["books"], b["n"], ("%.1f%%" % (100*b["fair"])) if b["fair"] else "-", b["res"]))
# the opposite side at Hard Rock (fade the move), same moments
day_odds = {}
fw = fl = 0; fu = 0.0
for b in bets:
    opp = "under" if b["side"] == "over" else "over"
    if b["res"] not in "WL": continue
    d = day_odds.setdefault(b["day"], json.load(open(R + "data/odds/%s.json" % b["day"])))
    price = None
    for f in sorted(d["fetches"], key=lambda f: f["at"]):
        for (p, l), q in odds.pairs((f["markets"].get(b["m"]) or {}).get("outcomes")).items():
            if l == b["hl"] and q["name"] and box.get((p, b["day"]), {}).get("name") == b["who"] and q[opp]: price = q[opp]
    if price is None: continue
    if b["res"] == "L": fw += 1; fu += odds.decimal(price) - 1
    else: fl += 1; fu -= 1
print("FADE the move (opposite side at HR): %d-%d, %+.2fu" % (fw, fl, fu))
