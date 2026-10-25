"""model.py: our own chance that a player goes over a rebounds line. It is the GUARD in Gap + Guard (20% weight, can only veto).

mean rebounds = rebounds per minute x expected minutes x opponent factor x back-to-back factor
  rebounds per minute  weighted over his played games, newest heaviest (half-life PARAMS.rpm_half games); last season's games
                       count PARAMS.prev_season_w as much
  expected minutes     weighted over his last 10 played games (half-life PARAMS.min_half)
  opponent factor      rebounds the opponent's opponents grab per game / league average, shrunk toward 1 (PARAMS.opp_shrink games),
                       raised to PARAMS.opp_exp
  back-to-back         x PARAMS.b2b when his team played the day before
chance over a line L = P(X > L) with X negative binomial, variance = PARAMS.disp x mean.
Parameters are fitted by the Data Scientist on 2025-26 box scores (research/calibrate.py, TEAM.md section 7 item 3).
Every number comes only from games strictly before the game being priced.
"""
import math
from datetime import date as _date, timedelta

PARAMS = {"rpm_half": 20.0, "prev_season_w": 0.5, "min_half": 4.0, "min_games": 10, "opp_shrink": 15.0, "opp_exp": 1.0,
          "b2b": 1.0, "disp": 1.15, "min_history": 10}


def _wmean(vals, half):
    """Weighted mean of (value, weight) pairs listed newest first, with age decay half-life `half` (in games)."""
    num = den = 0.0
    for age, (v, w) in enumerate(vals):
        k = w * 0.5 ** (age / half)
        num += k * v
        den += k
    return num / den if den else None


def player_mean(rows, season, opp_factor=1.0, b2b=False, p=PARAMS):
    """rows: his box rows before the game, oldest first. Returns (mean, info) or (None, why)."""
    played = [r for r in rows if not r.get("dnp") and (r.get("min") or 0) > 0]
    if len(played) < p["min_history"]:
        return None, "fewer than %d games" % p["min_history"]
    new_first = list(reversed(played))
    tot_min = sum((r["min"] or 0) * (1.0 if r["date"] >= season else p["prev_season_w"]) * 0.5 ** (i / p["rpm_half"])
                  for i, r in enumerate(new_first))
    tot_reb = sum((r["reb"] or 0) * (1.0 if r["date"] >= season else p["prev_season_w"]) * 0.5 ** (i / p["rpm_half"])
                  for i, r in enumerate(new_first))
    if tot_min <= 0:
        return None, "no minutes"
    rpm = tot_reb / tot_min
    mins = _wmean([(r["min"], 1.0) for r in new_first[:p["min_games"]]], p["min_half"])
    mean = rpm * mins * (opp_factor ** p["opp_exp"]) * (p["b2b"] if b2b else 1.0)
    return mean, {"rpm": rpm, "min": mins, "opp": opp_factor, "b2b": b2b, "games": len(played)}


def opp_factor(team_rows_opp, league_avg, season, p=PARAMS):
    """team_rows_opp: the OPPONENT team's rows (each has 'opp' rebounds through the matching row), oldest first, given as
    a list of rebounds its opponents grabbed per game. league_avg: rebounds per team-game."""
    if not league_avg or not team_rows_opp:
        return 1.0
    cur = [x for d, x in team_rows_opp if d >= season]
    prev = [x for d, x in team_rows_opp if d < season]
    n = len(cur) + 0.3 * len(prev)
    raw_num = sum(cur) + 0.3 * sum(prev)
    if n <= 0:
        return 1.0
    raw = (raw_num / n) / league_avg
    return 1.0 + (raw - 1.0) * n / (n + p["opp_shrink"])


def nb_cdf(k, mean, disp):
    """P(X <= k), X negative binomial with E = mean, Var = disp x mean (disp > 1; disp <= 1 falls back to Poisson)."""
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
    r = mean / (disp - 1.0)                     # NB(r, q): mean = r(1-q)/q, var = mean/q -> q = 1/disp
    q = 1.0 / disp
    term = q ** r                               # P(0)
    s = term
    for i in range(1, int(k) + 1):
        term *= (r + i - 1) / i * (1 - q)
        s += term
    return min(1.0, s)


def p_over(mean, line, p=PARAMS):
    """Chance of going OVER a half-point line (a whole-number line: over = more than the line, push not counted)."""
    k = math.floor(line + 1e-9)
    return 1.0 - nb_cdf(k, mean, p["disp"])


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


def league_avg(team_rows_all, season):
    cur = [r["reb"] for r in team_rows_all if r["date"] >= season and r.get("reb") is not None]
    if len(cur) >= 60:
        return sum(cur) / len(cur)
    allr = [r["reb"] for r in team_rows_all if r.get("reb") is not None]
    return sum(allr) / len(allr) if allr else None


def chance(store, pid, team, opp, date, line, season_start):
    """Our chance of OVER `line` for this player on `date` (only games before `date`). (p_over, info) or (None, why)."""
    rows = store.player_rows(pid, date)
    opp_rows = store.team_rows(opp, date)
    # rebounds the opponent ALLOWED: the other team's 'reb' in each of the opponent's games
    allowed = []
    for r in opp_rows:
        mate = next((x for x in store.by_team_games.get(r["opp"], []) if x["game"] == r["game"]), None)
        if mate and mate.get("reb") is not None:
            allowed.append((r["date"], mate["reb"]))
    lg = league_avg([r for rs in store.by_team_games.values() for r in rs if r["date"] < date], season_start)
    of = opp_factor(allowed, lg, season_start)
    mean, info = player_mean(rows, season_start, of, played_yesterday(store.team_rows(team, date), date))
    if mean is None:
        return None, info
    info["mean"] = mean
    pu = p_push(mean, line)
    po = p_over(mean, line)
    if pu:                                     # whole-number line: chance among non-push outcomes
        po = po / max(1e-9, 1.0 - pu)
    return po, info
