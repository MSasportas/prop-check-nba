"""Run 7 (2026-10-29): calculated ways to cut the pick count (S1-S7 in research/HYPOTHESES.md). Discovery only, Oct 25-28.
Read-only on data/ and scripts/. Usage: python3 research/code/run7_reduce.py"""
import collections, copy, json, math, random, statistics, sys, os
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/"
sys.path.insert(0, R + "scripts")
import common, engine, odds, stats, model, teams, run  # noqa: E402

cfg = copy.deepcopy(common.load_config())
cfg["pin_solo"]["min_gap_vs_pin"] = -1.0          # population is taken BEFORE the v2.2 gap gate
live_gap = 0.02
store = stats.load()
STAT = {m: cfg["markets"][m]["stat"] for m in cfg["markets"]}

class Ctx:
    def __init__(self, games): self.cfg, self.games, self.people = cfg, games, {}
    def eligible(self, *a): return None

pop = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28"):
    doc = common.read_json(odds.odds_path(day))
    byg = collections.defaultdict(list)
    for f in doc.get("fetches", []): byg[f["game_id"]].append(f)
    games = {g: {"id": g, "away": fs[0]["away"], "home": fs[0]["home"]} for g, fs in byg.items()}
    ctx, taken, rows = Ctx(games), set(), []
    for gid, fs in byg.items():
        for a, b in engine.solo_pairs(fs):
            if b["read"] in cfg["pin_solo"]["flag_reads"]:
                rows += [r for r in engine.solo_moves(a, b, ctx) if r["why"] is None]
    for r in sorted(rows, key=lambda r: (r["at"], -abs(r["pin_after"] - r["pin_before"]), r["pid"], r["market"])):
        if (r["pid"], r["market"]) in taken: continue
        taken.add((r["pid"], r["market"]))
        box = [x for x in store.player_rows(r["pid"]) if x["game"] == r["game_id"]]
        if not box: continue
        it = {"shown": {"pid": r["pid"], "line": r["line"], "side": r["side"], "price": r["price"], "market": r["market"]}}
        res, actual, units = engine.grade_one(it, box, cfg)
        if res not in ("W", "L"): continue
        t, opp = box[0]["team"], (games[r["game_id"]]["home"] if box[0]["team"] == games[r["game_id"]]["away"] else games[r["game_id"]]["away"])
        mp, _ = model.chance(store, r["pid"], t, opp, day, r["line"], run.SEASON_START, STAT[r["market"]])
        ms = None
        if mp is not None:
            off = cfg["gap_guard"]["offsets"].get(r["market"], 0.0)
            ms = (mp + off) if r["side"] == "over" else (1 - mp - off)
        pop.append(dict(day=day, game=r["game_id"], team=t, who=r["name"], m=r["market"], side=r["side"], line=r["line"], price=r["price"],
                        move=abs(r["pin_after"] - r["pin_before"]), others=r["others_move"], pin=r["pin_after"], pev=r["ev_vs_pin"],
                        gap=r["gap_vs_pin"], model=ms, res=res, u=units, live=(r["gap_vs_pin"] is not None and r["gap_vs_pin"] >= live_gap - 1e-9)))
days = sorted({p["day"] for p in pop})

def S(rs):
    w = sum(r["res"] == "W" for r in rs); l = sum(r["res"] == "L" for r in rs); u = sum(r["u"] for r in rs)
    return "%2d bets %2d-%2d %+6.2fu ROI %+5.1f%%" % (len(rs), w, l, u, 100 * u / len(rs) if rs else 0)
def roi(rs): return sum(r["u"] for r in rs) / len(rs) if rs else 0

print("POPULATION (before v2.2 gap): %d bets; %s" % (len(pop), S(pop)))
print("  live-rule subset (gap >= 2 pts): %s" % S([p for p in pop if p["live"]]))
for d in days: print("   ", d, S([p for p in pop if p["day"] == d]), "| live subset:", S([p for p in pop if p["day"] == d and p["live"]]))

# ---- scores ----
for p in pop:
    p["be"] = odds.break_even(p["price"])
    p["S1"] = p["pev"]
    p["S2"] = p["pin"] - p["be"] - 0.015
    oth = max(p["others"] if p["others"] is not None else 0.0, 0.005)
    p["S3"] = p["move"] / oth
    p["S6"] = (p["model"] is not None and p["model"] - p["pin"] >= -0.05)
def band(p): return "plus" if p["price"] > 0 else ("light" if p["price"] >= -130 else "heavy")
def cell_edge(train, p, key, k=20):
    t = [x for x in train if key(x) == key(p)]
    if not t: return 0.0
    hit = sum(x["res"] == "W" for x in t) / len(t); be = sum(x["be"] for x in t) / len(t)
    return (hit - be) * len(t) / (len(t) + k)
for p in pop:
    tr = [x for x in pop if x["day"] != p["day"]]
    p["S4"] = cell_edge(tr, p, lambda x: (x["m"], x["side"]))
    p["S4b"] = cell_edge(tr, p, band)
    # overlap: group key
    key = (lambda x: (x["day"], x["game"], x["team"], "over")) if p["side"] == "over" else (lambda x: (x["day"], x["game"], "under"))
    k = sum(1 for x in pop if x["side"] == p["side"] and key(x) == key(p))
    p["S5"] = p["S1"] / math.sqrt(k)
def z(vals, x):
    sd = statistics.pstdev(vals) or 1.0
    return (x - statistics.mean(vals)) / sd
for p in pop:
    tr = [x for x in pop if x["day"] != p["day"]]
    p["S7"] = z([x["S1"] for x in tr], p["S1"]) + z([x["S3"] for x in tr], p["S3"]) + z([x["S4"] for x in tr], p["S4"])

rules = [("S1 EV vs Pinnacle >= 0%", lambda p: p["S1"] >= 0), ("S1 EV vs Pinnacle >= +2%", lambda p: p["S1"] >= .02),
         ("S2 net Pinnacle edge > 0", lambda p: p["S2"] > 0), ("S3 move/others >= 2", lambda p: p["S3"] >= 2),
         ("S3 move/others >= 4", lambda p: p["S3"] >= 4), ("S4 cell track record > 0", lambda p: p["S4"] > 0),
         ("S4b price band track > 0", lambda p: p["S4b"] > 0), ("S5 overlap-discounted EV >= -3%", lambda p: p["S5"] >= -.03),
         ("S5 overlap-discounted EV >= -1%", lambda p: p["S5"] >= -.01),
         ("S6 model not 5+ pts below Pinnacle", lambda p: p["S6"]), ("S7 composite > 0", lambda p: p["S7"] > 0)]
random.seed(7)
def placebo(rs, n, trials=2000):
    if n == 0 or n == len(rs): return float("nan")
    base = roi(rs); hit = 0; us = [r["u"] for r in rs]
    k = roi([r for r in rs])  # unused
    keep_roi = None
    return None
for label, subset in (("ALL population (before gap)", pop), ("LIVE subset (gap >= 2 pts)", [p for p in pop if p["live"]])):
    print("\n=== %s: %s ===" % (label, S(subset)))
    print("%-36s | %-34s | %-34s | cut%% | placebo p" % ("rule", "KEPT", "CUT"))
    for name, f in rules:
        kept = [p for p in subset if f(p)]; cut = [p for p in subset if not f(p)]
        if not kept: print("%-36s | none kept" % name); continue
        kr = roi(kept); ge = 0
        for _ in range(2000):
            samp = random.sample(subset, len(kept))
            if roi(samp) >= kr: ge += 1
        print("%-36s | %-34s | %-34s | %3.0f%% | %.2f" % (name, S(kept), S(cut), 100 * len(cut) / len(subset), ge / 2000))
    # score terciles (diagnosis only: does a higher score mean better results?)
    print("  score thirds (diagnosis, highest first):")
    for sc in ("S1", "S2", "S3", "S4", "S5", "S7"):
        srt = sorted(subset, key=lambda p: -p[sc]); n = len(srt); a, b = n // 3, 2 * n // 3
        print("   %s: top %s | mid %s | low %s" % (sc, S(srt[:a]), S(srt[a:b]), S(srt[b:])))
json.dump(pop, open(R + "research/run7_population.json", "w"), indent=0)
