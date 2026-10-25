"""stats.py: the box-score store the model reads.

Sources: data/seed/players_<season>.json.gz and teams_<season>.json.gz (one-time `setup` workflow: ESPN box scores of 2025-26 and of
2026-27 up to 2026-10-24), plus data/state/box/players_<season>.json.gz / teams_<season>.json.gz, which run.py extends with every final
game it grades (one row per player per game, same fields as the seed). A game is never stored twice (keyed by game id).

Row fields (player): pid (ESPN athlete id), name, team, opp (ESPN abbreviations), home, starter, dnp, min, reb, oreb, dreb, game, date.
Row fields (team):   team, opp, home, ot, reb, oreb, dreb, fgm, fga, fta, tov, pts, game, date.
"""
import os

import common

SEASONS = ("2025-26", "2026-27")
CURRENT = "2026-27"


def season_of(date):
    """'2026-10-25' -> '2026-27' (a season runs from August to July)."""
    y, m = int(date[:4]), int(date[5:7])
    start = y if m >= 8 else y - 1
    return "%d-%02d" % (start, (start + 1) % 100)


def _seed_path(kind, season):
    return os.path.join(common.ROOT, "data", "seed", "%s_%s.json.gz" % (kind, season))


def _live_path(kind, season):
    return common.dpath("state", "box", "%s_%s.json.gz" % (kind, season))


class Store:
    def __init__(self, players, teams):
        self.players, self.teams = players, teams
        self.by_pid, self.by_team_games = {}, {}
        for r in sorted(players, key=lambda r: (r["date"], r["game"])):
            self.by_pid.setdefault(r["pid"], []).append(r)
        for r in sorted(teams, key=lambda r: (r["date"], r["game"])):
            self.by_team_games.setdefault(r["team"], []).append(r)
        self.games = {r["game"] for r in teams}
        self.names = {}
        for r in players:
            self.names[r["pid"]] = r["name"]

    def player_rows(self, pid, before=None):
        rows = self.by_pid.get(pid, [])
        return [r for r in rows if before is None or r["date"] < before]

    def team_rows(self, team, before=None):
        rows = self.by_team_games.get(team, [])
        return [r for r in rows if before is None or r["date"] < before]

    def last_team_game(self, team, before):
        rows = self.team_rows(team, before)
        return rows[-1] if rows else None

    def latest_date(self):
        return max((r["date"] for r in self.teams), default=None)


def load():
    players, teams, seen = [], [], set()
    for season in SEASONS:
        for path_of in (_live_path, _seed_path):            # live rows first: a regraded game wins over the seed
            ps = common.read_gz_json(path_of("players", season), []) or []
            ts = common.read_gz_json(path_of("teams", season), []) or []
            new = {r["game"] for r in ts} - seen
            players += [r for r in ps if r["game"] in new]
            teams += [r for r in ts if r["game"] in new]
            seen |= new
    return Store(players, teams)


def add_game(season, prow, trow):
    """Store one final game's rows (from espn.box). Returns True if it was new."""
    tp, pp = _live_path("teams", season), _live_path("players", season)
    teams = common.read_gz_json(tp, []) or []
    gid = trow[0]["game"] if trow else None
    if gid is None or any(r["game"] == gid for r in teams):
        return False
    seed = common.read_gz_json(_seed_path("teams", season), []) or []
    if any(r["game"] == gid for r in seed):
        return False
    players = common.read_gz_json(pp, []) or []
    common.write_gz_json(pp, players + prow)
    common.write_gz_json(tp, teams + trow)
    return True
