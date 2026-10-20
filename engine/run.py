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
    picks = read_csv(f"{D}/picks.csv")
    if picks is None:
        return 0
    res = read_csv(f"{D}/results.csv")
    done = set() if res is None else set(zip(res.date, res.espn_id))
    sp = read_csv(f"{D}/season_players.csv")
    st = read_csv(f"{D}/season_teams.csv")
    if st is None:
        return 0
    played = set(st.gameId)
    box = {} if sp is None else {(r.gameId, r.pid[4:]): r for r in sp.itertuples()}
    rows, ts = [], now_et().isoformat(timespec="minutes")
    for (date, eid, gid), _ in picks.groupby(["date", "espn_id", "game_id"]):
        if (date, eid) in done or gid not in played:
            continue
        r = box.get((gid, eid))
        rows.append(dict(date=date, espn_id=eid, game_id=gid, pts="" if r is None else int(r.pts),
                         min="" if r is None else r.min, graded_ts=ts))   # blank pts = DNP = void
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
    # last-season name index for matching ESPN players (same team only)
    base = pl[pl.season == SEASON - 1].drop_duplicates(["pid", "team"])[["pid", "team", "name"]]
    base["key"] = base.name.map(espn.norm)
    idx = base.groupby(["team", "key"]).pid.agg(list).to_dict()

    notes, out_games, picks = [], [], []
    for gm in sorted(games, key=lambda x: x["date_utc"]):
        tip = dt.datetime.fromisoformat(gm["date_utc"].replace("Z", "+00:00")).astimezone(ET)
        label = f"{gm['away']} @ {gm['home']}"
        gout = dict(id=gm["id"], game=label, tip_et=tip.strftime("%-I:%M %p"), legs=[], held=[], note="")
        if gm["state"] != "pre":
            gout["note"] = "Started or final, not shown"
            out_games.append(gout)
            continue
        summ = espn.get(f"summary?event={gm['id']}")
        spr, spr_txt = espn.spread(summ)
        gout.update(spread=spr, spread_txt=spr_txt, settled=settled_label(run, tip, now))
        if spr is None:
            gout["note"] = "No spread posted yet: all legs held (spread gate can't pass)"
        elif spr > core.MAX_SPREAD:
            gout["note"] = f"Spread {spr} > 10: all legs fail spread gate"
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
                hist = core.clean_history(rows, margins)
                ev = core.evaluate(hist, team, opp, SEASON, fac)
                if ev is None:
                    continue
                m = next(r for r in ev["rungs"] if r["off"] == 0)
                fails = []
                if a["status"] not in OK_STATUS:
                    fails.append(f"Injury: {a['status']}")
                if ev["l5min"] < core.MIN_L5:
                    fails.append(f"L5 min {ev['l5min']}")
                if spr is None:
                    fails.append("No spread")
                elif spr > core.MAX_SPREAD:
                    fails.append(f"Spread {spr}")
                if m["tool"] < core.MIN_TOOL:
                    fails.append(f"Tool {m['tool']:.0%}")
                leg = dict(espn_id=eid, player=a["name"], team=team, opp=opp, status=a["status"],
                           factor=round(fac, 3), def_ratio=round(dr, 3), pace_ratio=round(pr, 3), opp_b2b=opp_b2b,
                           matched_last_season=len(cands) == 1, **ev)
                if fails:
                    # only list near-misses worth knowing about (would pass on tool, or close)
                    if m["tool"] >= core.MIN_TOOL - 0.05:
                        gout["held"].append(dict(player=a["name"], team=team, rung=m["rung"],
                                                 tool=m["tool"], why=", ".join(fails)))
                    continue
                leg["parlay_ok"] = m["tool"] >= core.PARLAY_MIN
                gout["legs"].append(leg)
                picks.append(dict(date=today.isoformat(), run=run, run_ts=now.isoformat(timespec="minutes"),
                                  game_id=gm["id"], game=label, tip_et=gout["tip_et"], espn_id=eid, player=a["name"],
                                  team=team, opp=opp, rung=m["rung"], rung_off=0, tool=m["tool"], fair=m["fair"],
                                  bet_at=m["bet_at"], list="parlay" if leg["parlay_ok"] else "straight",
                                  settled=gout["settled"]))
        gout["legs"].sort(key=lambda x: x["player"])
        out_games.append(gout)

    n_cur = {t: r["gp"] for t, r in ratings.items()}
    if max(n_cur.values() or [0]) < 15:
        notes.append(f"Early season: team ratings and hit rates lean on last season (blend until game 15; "
                     f"teams have played {max(n_cur.values())} or fewer games this season).")
    notes.append("Rest spots: only caught if the team lists him on the injury report.")
    out = dict(generated_et=now.isoformat(timespec="minutes"), run=run, date=today.isoformat(), notes=notes,
               games=out_games, n_legs=len(picks), n_parlay=sum(p["list"] == "parlay" for p in picks),
               ingested_through=load_state().get("ingested_through"))
    os.makedirs(DOCS, exist_ok=True)
    json.dump(out, open(f"{DOCS}/slate.json", "w"), separators=(",", ":"))
    append_csv(f"{D}/picks.csv", PICK_COLS, picks)
    return out


# ---------------- record view ----------------
def build_record():
    picks = read_csv(f"{D}/picks.csv")
    if picks is None:
        json.dump(dict(rows=[], summary=[]), open(f"{DOCS}/record.json", "w"))
        return
    # the record is the last run of the day for each leg
    last = picks.sort_values("run_ts").groupby(["date", "espn_id"]).tail(1)
    res, prc = read_csv(f"{D}/results.csv"), read_csv(f"{D}/prices.csv")
    if res is not None:
        last = last.merge(res[["date", "espn_id", "pts"]].assign(graded=1), on=["date", "espn_id"], how="left")
    else:
        last["pts"], last["graded"] = None, None
    if prc is not None:
        p = prc.sort_values("ts").groupby(["date", "espn_id"]).tail(1)[["date", "espn_id", "hr_price"]]
        last = last.merge(p, on=["date", "espn_id"], how="left")
    else:
        last["hr_price"] = None
    rows = []
    for r in last.sort_values(["date", "game", "player"], ascending=[False, True, True]).itertuples():
        result = "" if pd.isna(r.graded) else ("void" if pd.isna(r.pts) else ("hit" if r.pts >= r.rung else "miss"))
        hr = None if pd.isna(r.hr_price) else int(r.hr_price)
        met = None if hr is None else (dec(hr) >= dec(int(r.bet_at)))
        rows.append(dict(date=r.date, game=r.game, player=r.player, rung=int(r.rung), tool=round(float(r.tool), 3),
                         bet_at=int(r.bet_at), hr_price=hr, met=met, pts=None if pd.isna(r.pts) else int(r.pts),
                         result=result, list=r.list, run=r.run))
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
        print(due, "legs:", out["n_legs"])
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
        print("legs", o["n_legs"], "parlay", o["n_parlay"])
    elif mode == "ingest":
        st = load_state(); print(ingest(st)); save_state(st)
    elif mode == "grade":
        print(grade()); build_record()
