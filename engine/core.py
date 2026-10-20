"""Prop Check NBA v1 engine. Numbers from backtest-v1-results.md ENGINE PARAMETERS, logic from backtest engine.py/analyze.py."""
import math
import numpy as np
import pandas as pd

RUNGS = np.arange(10, 55, 5)
BLEND_K = 15
MAIN_RATE = 0.65
F_DEF, F_PACE, F_OPP_B2B = 1.106, 0.26, 0.018
W_L10, W_L20, W_S = 0.1, 0.2, 0.7
PLATT_A, PLATT_B = 0.125, 0.834
HIGH_RUNG, HIGH_RUNG_CUT, CAP = 25, 0.05, 0.85
MIN_L5, MAX_SPREAD, MIN_TOOL, PARLAY_MIN = 30, 10, 0.60, 0.75
MIN_HIST = 10


def cushion(p):
    return 0.04 if p < .5 else 0.05 if p < .65 else 0.06 if p < .75 else 0.07 if p < .85 else 0.08


def american(p):
    p = min(max(p, 0.01), 0.99)
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def bet_at_prob(p):
    return p - cushion(p)


def logit(p):
    p = min(max(p, 0.02), 0.98)
    return math.log(p / (1 - p))


def calibrate(blend, rung):
    t = 1 / (1 + math.exp(-(PLATT_A + PLATT_B * logit(blend))))
    if rung >= HIGH_RUNG:
        t -= HIGH_RUNG_CUT
    return min(t, CAP)


# ---------------- team context ----------------
def team_games(tm):
    """tm rows: season, gameId, date, team, opp, pts, poss, n_ot -> adds gposs, pace48, opp_pts, margin."""
    g = tm.merge(tm[['gameId', 'team', 'pts', 'poss']].rename(columns={'team': 'opp', 'pts': 'opp_pts', 'poss': 'opp_poss'}),
                 on=['gameId', 'opp'])
    g['gposs'] = (g.poss + g.opp_poss) / 2
    g['pace48'] = g.gposs * 48 / (48 + 5 * g.n_ot)
    g['margin'] = g.pts - g.opp_pts
    return g


def team_ratings(g, season, before):
    """Pregame pace / def per100 / off per100 for every team as of `before` (date str), blended with last season."""
    out = {}
    for team, tg in g.groupby('team'):
        last = tg[tg.season == season - 1]
        cur = tg[(tg.season == season) & (tg.date < before)]
        n = len(cur)
        pr = (last.pace48.mean(), last.opp_pts.sum() / last.gposs.sum() * 100,
              last.pts.sum() / last.gposs.sum() * 100) if len(last) else None
        k = max(0, BLEND_K - n) if pr else 0
        if n + k == 0:
            continue
        cd = cur.opp_pts.sum() / cur.gposs.sum() * 100 if n else 0
        co = cur.pts.sum() / cur.gposs.sum() * 100 if n else 0
        out[team] = dict(
            pace=(cur.pace48.sum() + (pr[0] * k if pr else 0)) / (n + k),
            dfn=(cd * n + (pr[1] * k if pr else 0)) / (n + k),
            off=(co * n + (pr[2] * k if pr else 0)) / (n + k), gp=n)
    lg = dict(pace=np.mean([v['pace'] for v in out.values()]), dfn=np.mean([v['dfn'] for v in out.values()]))
    return out, lg


def factor(team, opp, ratings, lg, opp_b2b):
    r, o = ratings[team], ratings[opp]
    def_ratio = o['dfn'] / lg['dfn']
    pace_ratio = ((r['pace'] + o['pace']) / 2) / lg['pace']
    f = def_ratio ** F_DEF * pace_ratio ** F_PACE * math.exp(F_OPP_B2B * opp_b2b)
    return f, def_ratio, pace_ratio


# ---------------- player ----------------
def clean_history(rows, margins):
    """rows: one player's games (all teams), sorted by date. Flags injury-shortened games
    (min < 60% of median of previous 10, final margin under 20)."""
    rows = rows.merge(margins, on=['gameId', 'team'], how='left').sort_values('date').reset_index(drop=True)
    med10 = rows['min'].shift(1).rolling(10, min_periods=3).median()
    rows['short'] = ((rows['min'] < 0.6 * med10) & (rows.margin.abs() < 20)).astype(int)
    return rows


def evaluate(hist, team, opp, season, fac):
    """hist: cleaned rows for one player before tonight. Returns dict or None (not enough history)."""
    prior = hist[(hist.team == team) & (hist.season >= season - 1) & (hist.short == 0)]
    if len(prior) < MIN_HIST:
        return None
    cur, last = prior[prior.season == season], prior[prior.season == season - 1]
    pa, pc, pl_ = prior.pts.values, cur.pts.values, last.pts.values
    k = max(0, BLEND_K - len(cur)) if len(last) >= 10 else 0
    if len(cur) + k == 0:
        return None

    def season_rate(x):
        rl = (pl_ >= x).mean() if len(pl_) else 0
        return ((pc >= x).sum() + rl * k) / (len(cur) + k)

    rates = np.array([season_rate(x) for x in RUNGS])
    ok = np.where(rates >= MAIN_RATE)[0]
    if len(ok) == 0:
        return None
    main = int(RUNGS[ok.max()])
    rungs = []
    for off in (-5, 0, 5):
        rung = main + off
        if rung <= 0:
            continue
        adj = rung / fac
        L10, L20, S = (pa[-10:] >= adj).mean(), (pa[-20:] >= adj).mean(), season_rate(adj)
        blend = W_L10 * L10 + W_L20 * L20 + W_S * S
        tool = calibrate(blend, rung)
        pb = bet_at_prob(tool)
        rungs.append(dict(off=off, rung=rung, adj=round(float(adj), 1), tool=round(float(tool), 4), blend=round(float(blend), 4),
                          fair=american(tool), bet_at=american(pb), bet_at_p=round(pb, 4),
                          strip=dict(L5=round(float((pa[-5:] >= rung).mean()), 2), L10=round(float((pa[-10:] >= rung).mean()), 2),
                                     L20=round(float((pa[-20:] >= rung).mean()), 2), S=round(float(season_rate(rung)), 2))))
    vs = prior[prior.opp == opp]
    return dict(main=main, rungs=rungs, l5min=round(float(prior['min'].values[-5:].mean()), 1),
                last10=[int(x) for x in pa[-10:]][::-1], n_hist=int(len(prior)), n_cur=int(len(cur)), k=int(k),
                h2h=[int(x) for x in vs.pts.values[-5:]][::-1])
