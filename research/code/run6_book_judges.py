import json, sys, gzip, os, collections
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds
box = {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")): box[(r["game"], r["pid"])] = r
ST = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
days = [d[:-5] for d in sorted(os.listdir(R + "data/odds")) if d < "2026-10-28"]
res = collections.defaultdict(lambda: {2: [], 3: []})
for day in days:
    d = json.load(open(R + "data/odds/%s.json" % day)); flagged = set()
    for f in sorted(d["fetches"], key=lambda f: f["at"]):
        if f["read"] not in "BCD": continue
        for m, hm in f["markets"].items():
            hp = odds.pairs(hm["outcomes"])
            for book, bm in (f.get("others") or {}).items():
                bp = odds.pairs((bm.get(m) or {}).get("outcomes"))
                for k, p in hp.items():
                    q = bp.get(k)
                    if not (p["over"] and p["under"] and q and q["over"] and q["under"]): continue
                    if not 0 <= odds.hold(q["over"], q["under"]) <= .15: continue
                    fo = odds.fair_two_sided(q["over"], q["under"])
                    for side, pr, fr in (("over", p["over"], fo), ("under", p["under"], 1 - fo)):
                        if not -200 <= pr <= 200: continue
                        e = odds.ev(fr, pr)
                        for bar in (2, 3):
                            key = (book, bar, day, f["game_id"], k[0], m)
                            if e >= bar / 100 and key not in flagged:      # first flag per player/market/night, price frozen
                                flagged.add(key)
                                b = box.get((f["game_id"], k[0]))
                                if not b or b["dnp"] or b.get(ST[m]) is None: r = "V"
                                else:
                                    x = b[ST[m]]; r = "P" if x == k[1] else ("W" if (x > k[1]) == (side == "over") else "L")
                                res[book][bar].append((r, pr, side))
print("Each book alone as the price judge, Oct 25-27, B/C/D reads, -200..+200, first flag per player/market/night:")
print("%-12s | %-26s | %-26s" % ("book", "Hard Rock >= +2% vs book", ">= +3%"))
for book in sorted(res, key=lambda b: -len(res[b][2])):
    cells = []
    for bar in (2, 3):
        L = res[book][bar]; w = sum(r == "W" for r, _, _ in L); l = sum(r == "L" for r, _, _ in L)
        u = sum((odds.decimal(p) - 1) if r == "W" else (-1 if r == "L" else 0) for r, p, _ in L)
        cells.append("%3d bets %2d-%-2d %+6.2fu" % (len(L), w, l, u))
    print("%-12s | %s | %s" % (book, cells[0], cells[1]))
