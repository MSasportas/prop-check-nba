import json, sys, statistics, collections
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))), "scripts"))
import odds
import os
D = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "shadow") + "/"
rows = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    for rd in json.load(open(D + day + ".json"))["reads"]:
        for r in rd["rows"]:
            r["day"], r["rd"], r["rat"] = day, rd["read"], rd["at"]
            rows.append(r)
ok = [r for r in rows if r.get("gap_ev") is not None and r["n_books"] >= 4]
print("sides with >=4 books on HR's line:", len(ok), "of", len(rows))
def summ(label, rs, key="gap_ev"):
    if not rs: return
    g = [r[key] for r in rs if r.get(key) is not None]
    if not g: return
    print("  %-28s n %5d  median %+5.1f%%  p90 %+5.1f%%  best %+5.1f%%  >=0 %3d  >=+2 %3d  >=+3 %3d" % (
        label, len(g), 100*statistics.median(g), 100*sorted(g)[int(.9*len(g))], 100*max(g), sum(x>=0 for x in g), sum(x>=.02 for x in g), sum(x>=.03 for x in g)))
print("R1 gap vs median of books:")
for m in ("rebounds", "points", "assists", "threes"): summ(m, [r for r in ok if r["market"] == m])
for k in "ABCD": summ("read " + k, [r for r in ok if r["rd"] == k])
for lab, f in (("price <= -150", lambda p: p <= -150), ("-149..-101", lambda p: -150 < p < -100), ("-100..+120", lambda p: -100 <= p <= 120), ("> +120", lambda p: p > 120)):
    summ("price " + lab, [r for r in ok if f(r["price"])])
for s in ("over", "under"): summ(s, [r for r in ok if r["side"] == s])
print("R2 vs Pinnacle alone (Pinnacle on HR's line):")
pr = [dict(r, pev=odds.ev(r["pin_fair"], r["price"])) for r in rows if r.get("pin_fair") is not None]
summ("all", pr, "pev")
for m in ("rebounds", "points", "assists", "threes"): summ(m, [r for r in pr if r["market"] == m], "pev")
# R3 stale: same game/player/market/line/side, consecutive reads; consensus moved >= 3 pts, HR price unchanged
seq = collections.defaultdict(list)
for r in ok: seq[(r["day"], r["game_id"], r["pid"], r["market"], r["line"], r["side"])].append(r)
st = []
for k, v in seq.items():
    v.sort(key=lambda r: r["rat"])
    for a, b in zip(v, v[1:]):
        if b["price"] == a["price"] and abs(b["market_fair"] - a["market_fair"]) >= 0.03:
            st.append((b["market_fair"] - a["market_fair"], b["gap_ev"], k))
print("R3 stale HR prices (market moved >= 3 pts, HR same price, next read):", len(st), "events of", sum(len(v)-1 for v in seq.values()) , "pairs")
for x in sorted(st, key=lambda t: -t[1])[:6]: print("   move %+.1f pts  gap now %+.1f%%  %s" % (100*x[0], 100*x[1], x[2]))
print("HR price changes between consecutive reads: %.1f%% of pairs" % (100*sum(b["price"] != a["price"] for v in seq.values() for a, b in zip(sorted(v, key=lambda r: r["rat"]), sorted(v, key=lambda r: r["rat"])[1:])) / max(1, sum(len(v)-1 for v in seq.values()))))
