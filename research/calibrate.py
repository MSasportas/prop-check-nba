#!/usr/bin/env python3
"""research/calibrate.py (Data Scientist): fit and check the rebounds / points / assists model on 2025-26 box scores, walk-forward.

For every player-game from 2025-12-01 to 2026-04-12 where the player has >= 10 earlier played games this season and played
(a did-not-play is a void, never a loss), the model is built ONLY from games before that date. The test line is the one a book
would most likely post, the player's last-10 average rounded to the nearest half-point line (x.5). We record our chance of
the over and whether he went over. No odds are used (we have no historical Hard Rock rebounds prices).

Outputs: log loss vs the base rate, calibration by chance bucket, mean bias (actual over rate - mean chance) = the offset.
Usage: python research/calibrate.py [reb|pts|ast] [grid]
"""
import gzip
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(gzip.open(os.path.join(ROOT, "data/seed/players_2025-26.json.gz"), "rt"))
T = json.load(gzip.open(os.path.join(ROOT, "data/seed/teams_2025-26.json.gz"), "rt"))
SEASON = "2025-10-01"
STAT = next((a for a in sys.argv[1:] if a in ("reb", "pts", "ast", "fg3m")), "reb")
FROM = "2025-12-01"

T.sort(key=lambda r: (r["date"], r["game"]))
by_game = {}
for r in T:
    by_game.setdefault(r["game"], {})[r["team"]] = r
P.sort(key=lambda r: (r["date"], r["game"]))
dates = sorted({r["date"] for r in T})


def run(params, collect=False):
    hist, allowed, team_last, lg = {}, {}, {}, []
    out = []
    pi = 0
    rows_by_date = {}
    for r in P:
        rows_by_date.setdefault(r["date"], []).append(r)
    for d in dates:
        lgavg = sum(lg) / len(lg) if lg else None
        y = d  # yesterday check
        for r in rows_by_date.get(d, []):
            if d < FROM or r["dnp"] or not r["min"]:
                continue
            rows = hist.get(r["pid"], [])
            played = [x for x in rows if not x["dnp"] and x["min"]]
            if len(played) < 10:
                continue
            last10 = [x[STAT] for x in played[-10:]]
            line = math.floor(sum(last10) / 10.0) + 0.5
            of = model.opp_factor(allowed.get(r["opp"], []), lgavg, SEASON, params)
            prev = team_last.get(r["team"])
            from datetime import date, timedelta
            b2b = prev == (date.fromisoformat(d) - timedelta(days=1)).isoformat()
            mean, info = model.player_mean(rows, SEASON, of, b2b, params, STAT)
            if mean is None:
                continue
            p = model.p_over(mean, line, params)
            out.append((p, 1 if r[STAT] > line else 0, mean, r[STAT], line, b2b))
        for r in rows_by_date.get(d, []):
            hist.setdefault(r["pid"], []).append(r)
        for g in {r["game"] for r in T if r["date"] == d}:
            tt = by_game[g]
            for tm, row in tt.items():
                other = [x for k, x in tt.items() if k != tm]
                if other and other[0].get(STAT) is not None:
                    allowed.setdefault(tm, []).append((d, other[0][STAT]))
                team_last[tm] = d
                if row.get(STAT) is not None:
                    lg.append(row[STAT])
    return out


def score(out):
    n = len(out)
    ll = -sum(y * math.log(max(1e-9, p)) + (1 - y) * math.log(max(1e-9, 1 - p)) for p, y, *_ in out) / n
    base = sum(y for _, y, *_ in out) / n
    llb = -(base * math.log(base) + (1 - base) * math.log(1 - base))
    bias = base - sum(p for p, *_ in out) / n
    return n, ll, llb, base, bias


if __name__ == "__main__":
    if "grid" in sys.argv:
        best = None
        for disp in ((1.0, 1.15, 1.3, 1.45) if STAT != "pts" else (1.6, 2.0, 2.4, 2.8, 3.2)):
            for oe in (0.0, 0.5, 1.0):
                for b2b in (0.95, 1.0):
                    for rh in (10.0, 20.0):
                        prm = dict(model.PARAMS_BY[STAT], disp=disp, opp_exp=oe, b2b=b2b, rpm_half=rh)
                        n, ll, llb, base, bias = score(run(prm))
                        print("disp %.2f opp %.1f b2b %.2f rpm_half %2.0f  n %d  logloss %.4f (base %.4f)  over %.3f bias %+.4f"
                              % (disp, oe, b2b, rh, n, ll, llb, base, bias), flush=True)
                        if best is None or ll < best[0]:
                            best = (ll, prm)
        print("BEST", best)
    else:
        out = run(model.PARAMS_BY[STAT])
        n, ll, llb, base, bias = score(out)
        print("n %d logloss %.4f base %.4f over-rate %.3f bias(offset) %+.4f" % (n, ll, llb, base, bias))
        buckets = {}
        for p, y, *_ in out:
            b = min(9, int(p * 10))
            buckets.setdefault(b, []).append((p, y))
        for b in sorted(buckets):
            xs = buckets[b]
            print("  %.1f-%.1f  n %5d  said %.3f  hit %.3f" % (b / 10, (b + 1) / 10, len(xs), sum(p for p, _ in xs) / len(xs),
                                                             sum(y for _, y in xs) / len(xs)))
