#!/usr/bin/env python3
"""replay.py: the live rule (config pin_solo) replayed on reads made BEFORE it went live, so Matt can see its history next to the
Record (Matt, 2026-10-28). Writes data/replay/pin_solo.json. Never touches the Record: these bets were never shown live.

Same code path as live (engine.solo_moves on consecutive reads, flag reads only, one pick per player per market a night, price frozen
at the flag read, graded from the box-score store like the Record). Not reproduced: injury eligibility at the time (no history of the
injury list), so every player counts as eligible. Usage: python scripts/replay.py [FROM] [TO]   (default 2026-10-25 .. day before live)
"""
import collections
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import engine  # noqa: E402
import odds  # noqa: E402
import stats  # noqa: E402
import teams  # noqa: E402


class _Ctx:
    def __init__(self, cfg, games):
        self.cfg, self.games, self.people = cfg, games, {}

    def eligible(self, *a):
        return None


def build(cfg, first, last, store):
    bets = []
    d = date.fromisoformat(first)
    while d.isoformat() <= last:
        day = d.isoformat()
        d += timedelta(days=1)
        doc = common.read_json(odds.odds_path(day))
        if not doc:
            continue
        byg = collections.defaultdict(list)
        for f in doc.get("fetches", []):
            byg[f["game_id"]].append(f)
        games = {g: {"id": g, "away": fs[0]["away"], "home": fs[0]["home"]} for g, fs in byg.items()}
        ctx = _Ctx(cfg, games)
        taken = set()
        rows = []
        for gid, fs in byg.items():
            for a, b in engine.solo_pairs(fs):
                if b["read"] in cfg["pin_solo"]["flag_reads"]:
                    rows += [r for r in engine.solo_moves(a, b, ctx) if r["why"] is None]
        for r in sorted(rows, key=lambda r: (r["at"], -abs(r["pin_after"] - r["pin_before"]), r["pid"], r["market"])):
            key = (r["pid"], r["market"])
            if key in taken:
                continue
            taken.add(key)
            box = [x for x in store.player_rows(r["pid"]) if x["game"] == r["game_id"]]
            it = {"shown": {"pid": r["pid"], "line": r["line"], "side": r["side"], "price": r["price"], "market": r["market"]}}
            res, actual, units = engine.grade_one(it, box, cfg) if r["game_id"] in store.games else (None, None, None)
            team = box[0]["team"] if box else None
            g = games[r["game_id"]]
            opp = g["home"] if team == g["away"] else g["away"]
            bets.append({"date": day, "player": r["name"], "team": teams.show(team) if team else None, "opp": teams.show(opp),
                         "home": team == g["home"], "market": r["market"], "line": r["line"], "side": r["side"],
                         "bet": engine.bet_text(r["side"], r["line"], cfg["markets"][r["market"]]["noun"]), "price": r["price"],
                         "read": r["read"], "at": r["at"], "pin_before": r["pin_before"], "pin_after": r["pin_after"],
                         "pin_price_before": r["pin_price_before"], "pin_price_after": r["pin_price_after"],
                         "others_move": r["others_move"], "n_others": r["n_others"], "window": r["window"],
                         "gap_vs_pin": r["gap_vs_pin"],
                         "result": res, "actual": actual,
                         "units": units})
    return bets


def summarize(bets):
    tot = {"w": 0, "l": 0, "push": 0, "void": 0, "pending": 0, "units": 0.0}
    for b in bets:
        if b["result"] is None:
            tot["pending"] += 1
        else:
            tot[{"W": "w", "L": "l", "PUSH": "push", "VOID": "void"}[b["result"]]] += 1
            tot["units"] += b["units"] or 0.0
    n = tot["w"] + tot["l"]
    tot["units"] = round(tot["units"], 2)
    tot["hit_rate"] = round(tot["w"] / n, 4) if n else None
    return tot


def main(argv):
    cfg = common.load_config()
    first = argv[0] if argv else "2026-10-25"
    last = argv[1] if len(argv) > 1 else (date.fromisoformat(cfg["pin_solo"]["live_from"]) - timedelta(days=1)).isoformat()
    bets = build(cfg, first, last, stats.load())
    nights = []
    for day in sorted({b["date"] for b in bets}, reverse=True):
        bs = [b for b in bets if b["date"] == day]
        nights.append(dict(summarize(bs), date=day, bets=bs))
    doc = {"rule": "pin_solo", "version": cfg["version"], "from": first, "to": last,
           "note": "Replay: the live rule run on price checks made before it went live (%s). These bets were never shown live and "
                   "are not on the Record. Injury status at the time is not replayed." % cfg["pin_solo"]["live_from"],
           "total": summarize(bets),
           "windows": [dict(summarize([b for b in bets if b["window"] == w]), window=w)
                       for w in engine.WINDOW_ORDER if any(b["window"] == w for b in bets)],
           "nights": nights}
    common.write_json(common.dpath("replay", "pin_solo.json"), doc)
    t = doc["total"]
    print("replay %s..%s: %d bets %d-%d %+.2fu, pending %d" % (first, last, len(bets), t["w"], t["l"], t["units"], t["pending"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
