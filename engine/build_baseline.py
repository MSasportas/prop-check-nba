"""Build last-season (2025-26) player logs and team games from shufinskiy cdnnba play-by-play.
Same logic as backtest build_logs.py, plus initial-name and tricode for matching to ESPN.
Usage: python engine/build_baseline.py path/to/cdnnba_2025.csv data/"""
import sys, re
import pandas as pd, numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
SEASON = 2025
COLS = ['gameId', 'orderNumber', 'period', 'clock', 'timeActual', 'actionType', 'subType', 'personId', 'teamId',
        'teamTricode', 'shotResult', 'pointsTotal', 'scoreHome', 'scoreAway', 'assistPersonId', 'stealPersonId',
        'blockPersonId', 'foulDrawnPersonId', 'playerNameI']
clock_re = re.compile(r'PT(\d+)M([\d.]+)S')
def clock_sec(c):
    m = clock_re.match(str(c)); return int(m.group(1)) * 60 + float(m.group(2)) if m else np.nan

df = pd.read_csv(SRC, usecols=COLS, low_memory=False).sort_values(['gameId', 'orderNumber'])
df['rem'] = df['clock'].map(clock_sec)
player_rows, team_rows, names = [], [], {}
for gid, g in df.groupby('gameId', sort=False):
    g = g.reset_index(drop=True)
    ts = pd.to_datetime(g['timeActual'].dropna().iloc[0], utc=True)
    date = ts.tz_convert('America/New_York').date()
    prim = g[(g.personId > 0) & g.teamId.notna()]
    p2t = prim.groupby('personId')['teamId'].agg(lambda x: x.mode().iloc[0]).to_dict()
    for pid, nm in prim.drop_duplicates('personId')[['personId', 'playerNameI']].values:
        names[int(pid)] = nm
    teams = sorted(set(prim.teamId.astype(int)))
    if len(teams) != 2: continue
    tri = {int(t): g.teamTricode[g.teamId == t].iloc[0] for t in teams}
    made = g[(g.shotResult == 'Made') & g.teamId.notna()]
    home, prev_h = None, 0
    for _, r in g.iterrows():
        if r.shotResult == 'Made' and pd.notna(r.teamId):
            home = int(r.teamId) if r.scoreHome > prev_h else [t for t in teams if t != int(r.teamId)][0]; break
        if pd.notna(r.scoreHome): prev_h = r.scoreHome
    if home is None: continue
    away = [t for t in teams if t != home][0]
    final = g.iloc[-1]
    pts_team = {home: final.scoreHome, away: final.scoreAway}
    pp = made[made.personId > 0].groupby('personId')['pointsTotal'].max().to_dict()
    secs = {}
    for per, pg in g.groupby('period', sort=True):
        plen = 720 if per <= 4 else 300
        first = {}
        for r in pg.itertuples(index=False):
            ids = []
            if r.personId > 0: ids.append((int(r.personId), r.subType if r.actionType == 'substitution' else 'act'))
            for c in ('assistPersonId', 'stealPersonId', 'blockPersonId', 'foulDrawnPersonId'):
                v = getattr(r, c)
                if pd.notna(v) and v > 0: ids.append((int(v), 'act'))
            for pid, kind in ids:
                if pid not in first: first[pid] = 'in' if kind == 'in' else 'on'
        on = {pid: 0.0 for pid, k in first.items() if k == 'on' and pid in p2t}
        for r in pg[pg.actionType == 'substitution'].itertuples(index=False):
            pid = int(r.personId); t = plen - (r.rem if pd.notna(r.rem) else plen)
            if r.subType == 'out' and pid in on: secs[pid] = secs.get(pid, 0) + t - on.pop(pid)
            elif r.subType == 'in': on[pid] = t
        for pid, t0 in on.items(): secs[pid] = secs.get(pid, 0) + plen - t0
    n_ot = max(0, int(g.period.max()) - 4)
    for pid in set(secs) | set(pp):
        if pid not in p2t: continue
        tm = int(p2t[pid]); op = away if tm == home else home
        player_rows.append((SEASON, str(gid), date, f'nba{pid}', tri[tm], tri[op], int(tm == home),
                            round(secs.get(pid, 0) / 60, 2), int(pp.get(pid, 0) or 0)))
    for tm in (home, away):
        tg = g[g.teamId == tm]
        fga = int(tg.actionType.isin(['2pt', '3pt']).sum()); fta = int((tg.actionType == 'freethrow').sum())
        orb = int(((tg.actionType == 'rebound') & (tg.subType == 'offensive') & (tg.personId > 0)).sum())
        tov = int((tg.actionType == 'turnover').sum())
        team_rows.append((SEASON, str(gid), date, tri[tm], tri[away if tm == home else home], int(tm == home),
                          pts_team[tm], fga + 0.44 * fta - orb + tov, n_ot))
pl = pd.DataFrame(player_rows, columns=['season', 'gameId', 'date', 'pid', 'team', 'opp', 'home', 'min', 'pts'])
pl['name'] = pl.pid.map(lambda p: names.get(int(p[3:])))
tm = pd.DataFrame(team_rows, columns=['season', 'gameId', 'date', 'team', 'opp', 'home', 'pts', 'poss', 'n_ot'])
pl.to_csv(f'{OUT}/baseline_players.csv.gz', index=False)
tm.to_csv(f'{OUT}/baseline_teams.csv.gz', index=False)
print(pl.shape, tm.shape)
