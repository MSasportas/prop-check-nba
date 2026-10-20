"""Prop Check NBA v1 runner.
python -m engine.run auto            # timer: decides what is due (ET)
python -m engine.run slate [label]   # force a slate run
python -m engine.run ingest|grade    # box scores in / grade picks
"""
import sys, os, json, csv, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
from engine import espn, core

ET = ZoneInfo("America/New_York")
SEASON = 2026                 # 2026-27 (baseline file is 2025)
SEASON_START = "2026-10-20"
D, DOCS = "data", "docs"
OK_STATUS = {"", "Active", "Probable"}
PICK_COLS = ["date", "run", "run_ts", "game_id", "game", "tip_et", "espn_id", "player", "team", "opp", "rung",
             "rung_off", "tool", "fair", "bet_at", "list", "settled", "sgp_note"]
RES_COLS = ["date", "espn_id", "game_id", "pts", "min", "graded_ts"]
LOG_COLS = ["date", "run", "run_ts", "game_id", "game", "tip_et", "espn_id", "player", "team", "opp", "fair",
            "l5min", "settled"]


def now_et():
    return dt.datetime.now(ET)


def load_state():
    try:
        return json.load(open(f"{D}/state.json"))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(f"{D}/state.json", "w"), indent=1, sort_keys=True)


def append_csv(path, cols, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def read_csv(path, **kw):
    return pd.read_csv(path, dtype={"gameId": str, "game_id": str, "espn_id": str}, **kw) if os.path.exists(path) else None


# ---------------- ingest box scores ----------------
def ingest(state):
    """Append completed regular-season games (dates before today ET) not yet ingested."""
    today = now_et().date()
    seen = set()
    st = read_csv(f"{D}/season_teams.csv")
    if st is not None:
        seen = set(st.gameId)
    start = dt.date.fromisoformat(state.get("ingested_through", SEASON_START))
    d, prow, trow, last_full = start, [], [], None
    while d < today:
        games = espn.scoreboard(d.strftime("%Y%m%d"))
        full = True
        for gm in games:
            if not gm["completed"]:
                full = False
                continue
            if gm["id"] in seen:
                continue
            p, t = espn.box(espn.get(f"summary?event={gm['id']}"), gm["id"], d.isoformat())
            prow += p
            trow += t
        if full:
            last_full = d
        d += dt.timedelta(days=1)
    append_csv(f"{D}/season_players.csv", ["season", "gameId", "date", "pid", "team", "opp", "home", "min", "pts", "name"], prow)
    append_csv(f"{D}/season_teams.csv", ["season", "gameId", "date", "team", "opp", "home", "pts", "poss", "n_ot"], trow)
    if last_full:
        state["ingested_through"] = last_full.isoformat()
    return len(trow) // 2


# ---------------- grade ----------------
def grade():
    """Record points for every player on any slate (blank pts = DNP = void)."""
    logs = [x for x in (read_csv(f"{D}/slate_log.csv"), read_csv(f"{D}/picks.csv")) if x is not None]
    st = read_csv(f"{D}/season_teams.csv")
    if not logs or st is None:
        return 0
    allp = pd.concat([x[["date", "espn_id", "game_id"]] for x in logs]).drop_duplicates()
    res = read_csv(f"{D}/results.csv")
    done = set() if res is None else set(zip(res.date, res.espn_id))
    sp = read_csv(f"{D}/season_players.csv")
    played = set(st.gameId)
    box = {} if sp is None else {(r.gameId, r.pid[4:]): r for r in sp.itertuples()}
    rows, ts = [], now_et().isoformat(timespec="minutes")
    for r0 in allp.itertuples():
        if (r0.date, r0.espn_id) in done or r0.game_id not in played:
            continue
        r = box.get((r0.game_id, r0.espn_id))
        rows.append(dict(date=r0.date, espn_id=r0.espn_id, game_id=r0.game_id, pts="" if r is None else int(r.pts),
                         min="" if r is None else r.min, graded_ts=ts))
        done.add((r0.date, r0.espn_id))
    append_csv(f"{D}/results.csv", RES_COLS, rows)
    return len(rows)


# ---------------- slate ----------------
def load_history():
    bp = pd.read_csv(f"{D}/baseline_players.csv.gz", dtype={"gameId": str})
    bt = pd.read_csv(f"{D}/baseline_teams.csv.gz", dtype={"gameId": str})
    sp, st = read_csv(f"{D}/season_players.csv"), read_csv(f"{D}/season_teams.csv")
    pl = pd.concat([bp] + ([sp] if sp is not None else []), ignore_index=True)
    tm = pd.concat([bt] + ([st] if st is not None else []), ignore_index=True)
    pl["date"], tm["date"] = pl.date.astype(str), tm.date.astype(str)
    pl = pl[pl["min"] > 0]
    return pl, core.team_games(tm)


def settled_label(run, tip, now):
    if (tip - now).total_seconds() <= 30 * 60:
        return "Lineup confirmed"
    return "Early" if run == "morning" else "Injury report out"


def slate(run):
    now = now_et()
    today = now.date()
    games = espn.scoreboard(today.strftime("%Y%m%d"))
    pl, g = load_history()
    ratings, lg = core.team_ratings(g, SEASON, today.isoformat())
    margins = g[["gameId", "team", "margin"]]
    yday = espn.scoreboard((today - dt.timedelta(days=1)).strftime("%Y%m%d"))
    played_yday = {t for x in yday for t in (x["home"], x["away"])}
    base = pl[pl.season == SEASON - 1].dropna(subset=["name"]).drop_duplicates(["pid", "team"])[["pid", "team", "name"]]
    base["key"] = base.name.map(espn.norm)
    idx = base.groupby(["team", "key"]).pid.agg(list).to_dict()

    notes, out_games, log = [], [], []
    for gm in sorted(games, key=lambda x: x["date_utc"]):
        tip = dt.datetime.fromisoformat(gm["date_utc"].replace("Z", "+00:00")).astimezone(ET)
        label = f"{gm['away']} @ {gm['home']}"
        gout = dict(id=gm["id"], game=label, tip_et=tip.strftime("%-I:%M %p"), players=[], held=[], note="")
        if gm["state"] != "pre":
            gout["note"] = "Started or final, not shown"
            out_games.append(gout)
            continue
        summ = espn.get(f"summary?event={gm['id']}")
        spr, spr_txt = espn.spread(summ)
        gout.update(spread=spr, spread_txt=spr_txt, settled=settled_label(run, tip, now))
        if spr is None:
            gout["note"] = "No spread posted yet: everyone held (spread gate can't pass)."
        elif spr > core.MAX_SPREAD:
            gout["note"] = f"Spread {spr} is over 10: everyone held."
        for team, opp, tid in ((gm["away"], gm["home"], gm["away_id"]), (gm["home"], gm["away"], gm["home_id"])):
            if team not in ratings or opp not in ratings:
                gout["note"] += f" Missing team ratings for {team}/{opp}."
                continue
            opp_b2b = int(opp in played_yday)
            fac, dr, pr = core.factor(team, opp, ratings, lg, opp_b2b)
            for a in espn.roster(tid):
                eid = a["espn_id"]
                cands = idx.get((team, espn.name_i(a["name"])), [])
                pids = [f"espn{eid}"] + (cands if len(cands) == 1 else [])
                rows = pl[pl.pid.isin(pids) & (pl.date < today.isoformat())]
                if rows.empty:
                    continue
                cv = core.line_curve(core.clean_history(rows, margins), team, opp, SEASON, fac)
                if cv is None:
                    continue
                fails = []
                if a["status"] not in OK_STATUS:
                    fails.append(a["status"])
                if cv["l5min"] < core.MIN_L5:
                    fails.append(f"{cv['l5min']} min L5")
                if spr is None or spr > core.MAX_SPREAD:
                    fails.append("spread")
                if fails:
                    if cv["l5min"] >= core.MIN_L5 - 4 or a["status"] not in OK_STATUS:
                        gout["held"].append(dict(player=a["name"], team=team, fair=cv["fair"], why=", ".join(fails)))
                    continue
                gout["players"].append(dict(espn_id=eid, player=a["name"], team=team, opp=opp, status=a["status"],
                                            factor=round(fac, 3), def_ratio=round(dr, 3), pace_ratio=round(pr, 3),
                                            opp_b2b=opp_b2b, matched_last_season=len(cands) == 1, **cv))
                log.append(dict(date=today.isoformat(), run=run, run_ts=now.isoformat(timespec="minutes"),
                                game_id=gm["id"], game=label, tip_et=gout["tip_et"], espn_id=eid, player=a["name"],
                                team=team, opp=opp, fair=cv["fair"], l5min=cv["l5min"], settled=gout["settled"]))
        gout["players"].sort(key=lambda x: -x["fair"])
        out_games.append(gout)

    n_cur = {t: r["gp"] for t, r in ratings.items()}
    if max(n_cur.values() or [0]) < 15:
        mx = max(n_cur.values())
        notes.append("Early season: numbers lean on last season (blend until game 15; "
                     + ("no games played yet)." if mx == 0 else f"teams have played {mx} or fewer games)."))
    notes.append("Rest spots: only caught if the team lists him on the injury report.")
    out = dict(generated_et=now.isoformat(timespec="minutes"), run=run, date=today.isoformat(), notes=notes,
               games=out_games, n_players=len(log), lines=core.LINES,
               block_over_at=core.BLOCK_OVER_AT, block_under_at=core.BLOCK_UNDER_AT,
               ingested_through=load_state().get("ingested_through"))
    os.makedirs(DOCS, exist_ok=True)
    json.dump(out, open(f"{DOCS}/slate.json", "w"), separators=(",", ":"))
    append_csv(f"{D}/slate_log.csv", LOG_COLS, log)
    return out


# ---------------- record view ----------------
def build_record():
    """Every player shown (last run of each day): fair line vs. actual points."""
    lg, res = read_csv(f"{D}/slate_log.csv"), read_csv(f"{D}/results.csv")
    rows = []
    if lg is not None:
        last = lg.sort_values("run_ts").groupby(["date", "espn_id"]).tail(1)
        if res is not None:
            last = last.merge(res[["date", "espn_id", "pts"]].assign(graded=1), on=["date", "espn_id"], how="left")
        else:
            last["pts"], last["graded"] = None, None
        for r in last.sort_values(["date", "game", "fair"], ascending=[False, True, False]).itertuples():
            res_ = "" if pd.isna(r.graded) else ("void" if pd.isna(r.pts) else ("over" if r.pts > r.fair else "under"))
            rows.append(dict(date=r.date, game=r.game, player=r.player, fair=float(r.fair),
                             pts=None if pd.isna(r.pts) else int(r.pts), result=res_))
    json.dump(dict(rows=rows, generated_et=now_et().isoformat(timespec="minutes")), open(f"{DOCS}/record.json", "w"),
              separators=(",", ":"))


def dec(am):
    return 1 + (am / 100 if am > 0 else 100 / -am)


# ---------------- timer ----------------
def auto():
    s = load_state()
    now = now_et()
    day = now.date().isoformat()
    done = s.setdefault("runs", {}).setdefault(day, [])
    games = espn.scoreboard(now.strftime("%Y%m%d"))
    tips = [dt.datetime.fromisoformat(x["date_utc"].replace("Z", "+00:00")).astimezone(ET) for x in games]
    first = min(tips) if tips else None
    due = None
    hm = now.hour * 60 + now.minute
    if "morning" not in done and hm >= 9 * 60 + 30:
        due = "morning"
    elif first and "pretip" not in done and first - dt.timedelta(minutes=75) <= now < first:
        due = "pretip"
    elif first and "afternoon" not in done and hm >= 13 * 60 + 30 and now < first - dt.timedelta(minutes=75):
        due = "afternoon"
    if not due:
        print("nothing due")
        return False
    if due == "morning":
        n = ingest(s)
        print("ingested games:", n, "graded:", grade())
    if games and (first is None or now < max(tips)):
        out = slate(due)
        print(due, "players:", out["n_players"])
    done.append(due)
    s["runs"] = {k: v for k, v in s["runs"].items() if k >= (now.date() - dt.timedelta(days=7)).isoformat()}
    s["last_run"] = dict(label=due, ts=now.isoformat(timespec="minutes"))
    save_state(s)
    build_record()
    return True


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if mode == "auto":
        auto()
    elif mode == "slate":
        st = load_state()
        n = ingest(st)
        save_state(st)
        print("ingested", n, "graded", grade())
        o = slate(sys.argv[2] if len(sys.argv) > 2 else "manual")
        build_record()
        print("players", o["n_players"])
    elif mode == "ingest":
        st = load_state(); print(ingest(st)); save_state(st)
    elif mode == "grade":
        print(grade()); build_record()
