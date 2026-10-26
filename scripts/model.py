"""model.py: our own chance that a player goes over a rebounds / points / assists line. It is the GUARD in Gap + Guard (20% weight,
can only veto, never create).

mean = stat per minute x expected minutes x opponent factor x back-to-back factor        (stat = reb, pts or ast)
  per minute         weighted over his played games, newest heaviest (half-life P.rpm_half games); last season's games count
                     P.prev_season_w as much
  expected minutes   weighted over his last 10 played games (half-life P.min_half)
  opponent factor    what the opponent ALLOWS per game in that stat / league average, shrunk toward 1 (P.opp_shrink games),
                     raised to P.opp_exp
  back-to-back       x P.b2b when his team played the day before
chance over a line L = P(X > L) with X negative binomial, variance = P.disp x mean.
Parameters per stat are fitted by the Data Scientist on 2025-26 box scores, walk-forward (research/calibrate.py; TEAM.md section 7).
Every number comes only from games strictly before the game being priced.
"""
import math
from datetime import date as _date, timedelta

BASE = {"rpm_half": 20.0, "prev_season_w": 0.5, "min_half": 4.0, "min_games": 10, "opp_shrink": 15.0, "opp_exp": 1.0,
        "b2b": 1.0, "disp": 1.15, "min_history": 10}
PARAMS_BY = {
    "reb": dict(BASE),
    "pts": dict(BASE, disp=1.6, rpm_half=10.0),          # DS fit 2026-10-25: log loss 0.6771 vs base 0.6908, bias +0.9 pt
    "ast": dict(BASE, disp=1.0, rpm_half=10.0),          # DS fit 2026-10-25: log loss 0.6660 vs base 0.6844, bias +0.1 pt
}
PARAMS = PARAMS_BY["reb"]


def _wmean(vals, half):
    num = den = 0.0
    for age, (v, w) in enumerate(vals):
        k = w * 0.5 ** (age / half)
        num += k * v
        den += k
    return num / den if den else None


def player_mean(rows, season, opp_factor=1.0, b2b=False, p=PARAMS, stat="reb"):
    """rows: his box rows before the game, oldest first. Returns (mean, info) or (None, why)."""
    played = [r for r in rows if not r.get("dnp") and (r.get("min") or 0) > 0 and r.get(stat) is not None]
    if len(played) < p["min_history"]:
        return None, "fewer than %d games" % p["min_history"]
    new_first = list(reversed(played))
    w = [(1.0 if r["date"] >= season else p["prev_season_w"]) * 0.5 ** (i / p["rpm_half"]) for i, r in enumerate(new_first)]
    tot_min = sum((r["min"] or 0) * k for r, k in zip(new_first, w))
    tot = sum((r[stat] or 0) * k for r, k in zip(new_first, w))
    if tot_min <= 0:
        return None, "no minutes"
    rate = tot / tot_min
    mins = _wmean([(r["min"], 1.0) for r in new_first[:p["min_games"]]], p["min_half"])
    mean = rate * mins * (opp_factor ** p["opp_exp"]) * (p["b2b"] if b2b else 1.0)
    return mean, {"rate": rate, "min": mins, "opp": opp_factor, "b2b": b2b, "games": len(played)}


def opp_factor(allowed, league_avg, season, p=PARAMS):
    """allowed: [(date, amount the opponent allowed that game)], oldest first. league_avg: per team-game."""
    if not league_avg or not allowed:
        return 1.0
    cur = [x for d, x in allowed if d >= season]
    prev = [x for d, x in allowed if d < season]
    n = len(cur) + 0.3 * len(prev)
    if n <= 0:
        return 1.0
    raw = ((sum(cur) + 0.3 * sum(prev)) / n) / league_avg
    return 1.0 + (raw - 1.0) * n / (n + p["opp_shrink"])


def nb_cdf(k, mean, disp):
    """P(X <= k), X negative binomial with E = mean, Var = disp x mean (disp <= 1 falls back to Poisson)."""
    if k < 0:
        return 0.0
    if mean <= 0:
        return 1.0
    if disp <= 1.0001:
        term = math.exp(-mean)
        s = term
        for i in range(1, int(k) + 1):
            term *= mean / i
            s += term
        return min(1.0, s)
    r = mean / (disp - 1.0)
    q = 1.0 / disp
    term = q ** r
    s = term
    for i in range(1, int(k) + 1):
        term *= (r + i - 1) / i * (1 - q)
        s += term
    return min(1.0, s)


def p_over(mean, line, p=PARAMS):
    return 1.0 - nb_cdf(math.floor(line + 1e-9), mean, p["disp"])


def p_push(mean, line, p=PARAMS):
    if abs(line - round(line)) > 1e-9:
        return 0.0
    k = int(round(line))
    return nb_cdf(k, mean, p["disp"]) - nb_cdf(k - 1, mean, p["disp"])


def played_yesterday(team_rows, date):
    if not team_rows:
        return False
    y = (_date.fromisoformat(date) - timedelta(days=1)).isoformat()
    return team_rows[-1]["date"] == y


def league_avg(team_rows_all, season, stat="reb"):
    cur = [r[stat] for r in team_rows_all if r["date"] >= season and r.get(stat) is not None]
    if len(cur) >= 60:
        return sum(cur) / len(cur)
    allr = [r[stat] for r in team_rows_all if r.get(stat) is not None]
    return sum(allr) / len(allr) if allr else None


def chance(store, pid, team, opp, date, line, season_start, stat="reb"):
    """Our chance of OVER `line` for this player on `date` (only games before `date`). (p_over, info) or (None, why)."""
    p = PARAMS_BY[stat]
    rows = store.player_rows(pid, date)
    allowed = []
    for r in store.team_rows(opp, date):
        mate = next((x for x in store.by_team_games.get(r["opp"], []) if x["game"] == r["game"]), None)
        if mate and mate.get(stat) is not None:
            allowed.append((r["date"], mate[stat]))
    lg = league_avg([r for rs in store.by_team_games.values() for r in rs if r["date"] < date], season_start, stat)
    of = opp_factor(allowed, lg, season_start, p)
    mean, info = player_mean(rows, season_start, of, played_yesterday(store.team_rows(team, date), date), p, stat)
    if mean is None:
        return None, info
    info["mean"] = mean
    pu = p_push(mean, line, p)
    po = p_over(mean, line, p)
    if pu:
        po = po / max(1e-9, 1.0 - pu)
    return po, info
