import json, sys, collections
R = "/home/claude/prop-check-nba/"
sys.path.insert(0, R + "scripts"); import odds
def mainlines(rows):
    best = {}
    for (pid, line), p in odds.pairs(rows).items():
        if not (p["over"] and p["under"]): continue
        g = abs(odds.fair_two_sided(p["over"], p["under"]) - .5)
        if pid not in best or g < best[pid][0]: best[pid] = (g, line)
    return {k: v[1] for k, v in best.items()}
moves = collections.Counter(); pairs = collections.Counter(); pin_solo = 0; pin_lm = 0; hr_follow = 0; ex = []
for day in ("2026-10-25", "2026-10-26", "2026-10-27"):
    d = json.load(open(R + "data/odds/%s.json" % day)); byg = collections.defaultdict(list)
    for f in sorted(d["fetches"], key=lambda f: f["at"]): byg[f["game_id"]].append(f)
    for gid, fs in byg.items():
        for a, b in zip(fs, fs[1:]):
            for m in b["markets"]:
                def ml(f, book):
                    src = (f["markets"].get(m) or {}) if book == "hardrockbet" else ((((f.get("others") or {}).get(book) or {}).get(m)) or {})
                    return mainlines(src.get("outcomes"))
                books = ["hardrockbet"] + [x for x in (b.get("others") or {}) if x not in ("novig", "prophetx")]
                A = {bk: ml(a, bk) for bk in books}; B = {bk: ml(b, bk) for bk in books}
                for bk in books:
                    for pid, l in B[bk].items():
                        if pid in A[bk]:
                            pairs[bk] += 1; moves[bk] += (A[bk][pid] != l)
                for pid, l in B.get("pinnacle", {}).items():
                    if pid in A.get("pinnacle", {}) and A["pinnacle"][pid] != l:
                        pin_lm += 1
                        oth = [bk for bk in books if bk not in ("pinnacle", "hardrockbet") and pid in A[bk] and pid in B[bk]]
                        moved = sum(A[bk][pid] != B[bk][pid] for bk in oth)
                        hr = pid in A["hardrockbet"] and pid in B["hardrockbet"] and A["hardrockbet"][pid] != B["hardrockbet"][pid]
                        if oth and moved <= len(oth) // 3:
                            pin_solo += 1; ex.append((day, m, pid, A["pinnacle"][pid], l, moved, len(oth), hr))
                        hr_follow += hr
print("Main LINE changed between two consecutive checks (share of player-checks):")
for bk in sorted(pairs, key=lambda b: -moves[b] / pairs[b]): print("  %-12s %5.1f%%  (%d of %d)" % (bk, 100 * moves[bk] / pairs[bk], moves[bk], pairs[bk]))
print("Pinnacle moved its LINE: %d times; Hard Rock moved its line in the same window %d of those; Pinnacle alone (<= 1/3 of others moved): %d" % (pin_lm, hr_follow, pin_solo))
for e in ex[:8]: print("  ", e)
import gzip, os
box = {}
for f in ("data/seed/players_2026-27.json.gz", "data/state/box/players_2026-27.json.gz"):
    if os.path.exists(R + f):
        for r in json.load(gzip.open(R + f, "rt")): box[r["pid"], r["date"]] = r
ST = {"rebounds": "reb", "points": "pts", "assists": "ast", "threes": "fg3m"}
W = L = 0; u = 0.0
for day, m, pid, l0, l1, mv, n, hr in ex:
    side = "over" if l1 > l0 else "under"
    b = box.get((pid, day))
    # Hard Rock's line + price for that side at the later read (find in the day's fetches)
    d = json.load(open(R + "data/odds/%s.json" % day)); hl = hp = None
    for f in sorted(d["fetches"], key=lambda f: f["at"]):
        for (p, l), q in odds.pairs((f["markets"].get(m) or {}).get("outcomes")).items():
            if p == pid and q[side]: hl, hp = l, q[side]
    if not b or b["dnp"] or hl is None: print("  ", m, pid, "ungraded"); continue
    x = b[ST[m]]; res = "P" if x == hl else ("W" if (x > hl) == (side == "over") else "L")
    W += res == "W"; L += res == "L"; u += (odds.decimal(hp) - 1) if res == "W" else (-1 if res == "L" else 0)
    print("   %s %-8s %s Pinnacle %s -> %s, bet %s at HR %s %+d -> %s (%s)" % (day[5:], m, b["name"], l0, l1, side, hl, hp, res, x))
print("Pinnacle solo LINE moves, follow at Hard Rock: %d-%d, %+.2fu" % (W, L, u))
