"""watch.py: behind-the-scenes tracks (TEAM.md section 4, "Behind the scenes"). Research only: never the Record, never Discord.
The page shows them on its Backstage tab.

Track `pin_judge` (Matt, 2026-10-28): "Pinnacle as the price judge". On the newest B/C/D read of each unstarted game (read <= 15 min
old), every Hard Rock main-line side whose EV against Pinnacle's de-vigged chance on the SAME line is >= watch.pin_judge.min_ev, price
inside the customer limit, player eligible. First flag per player / market / night, price frozen at that read. Graded like the Record
(1 unit, overtime counts, did not play = void) from the box-score store.

Files: data/watch/pin_judge/flags.jsonl (append-only, one flag per line) and summary.json (rebuilt every run).
"""
import json
import os

import common
import engine
import odds

TRACK = "pin_judge"


def _dir():
    return common.dpath("watch", TRACK)


def _flags_path():
    return os.path.join(_dir(), "flags.jsonl")


def read_flags():
    out = []
    try:
        with open(_flags_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return out


def _append(rows):
    if not rows:
        return
    try:
        with open(_flags_path(), "rb") as f:
            raw = f.read()
    except OSError:
        raw = b""
    add = "".join(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n" for r in rows).encode("utf-8")
    common.write_bytes(_flags_path(), raw + add)


def flag(ctx, evals):
    """Add today's new flags from the newest flag read of each unstarted game. Returns the number added."""
    cfg = ctx.cfg
    w = (cfg.get("watch") or {}).get(TRACK) or {}
    if not w.get("active") or ctx.slate < w.get("from_slate", "9999"):
        return 0
    have = {(f["slate"], f["game_id"], f["pid"], f["market"]) for f in read_flags()}
    new = []
    for gid, pairs in evals.items():
        g = ctx.games.get(gid)
        if not g or engine.started(g, ctx.now) or not pairs:
            continue
        f, rows = pairs[-1]
        if f["read"] not in w["reads"] or (ctx.now - common.parse_iso(f["at"])).total_seconds() > w["max_age_min"] * 60:
            continue
        for r in sorted(rows, key=lambda r: -(r.get("pin_ev") or -9)):
            if r.get("pin_fair") is None or r.get("pin_ev") is None or r["pin_ev"] < w["min_ev"] - engine.EPS:
                continue
            if not (cfg["customer"]["worst_price"] <= r["price"] <= w["max_price"]):
                continue
            key = (ctx.slate, gid, r["pid"], r["market"])
            if key in have or ctx.eligible(r["pid"], r["team"], g):
                continue
            have.add(key)
            new.append({"slate": ctx.slate, "game_id": gid, "start": g["start"], "pid": r["pid"], "player": r["name"],
                        "team": r["team"], "opp": r["opp"], "home": r["home"], "market": r["market"], "line": r["line"],
                        "side": r["side"], "price": r["price"], "at": f["at"], "read": f["read"],
                        "pin_fair": round(r["pin_fair"], 4), "pin_ev": round(r["pin_ev"], 4),
                        "market_fair": round(r["market_fair"], 4) if r.get("market_fair") is not None else None,
                        "gap_ev": round(r["gap_ev"], 4) if r.get("gap_ev") is not None else None,
                        "bet": engine.bet_text(r["side"], r["line"], cfg["markets"][r["market"]]["noun"])})
    _append(new)
    return len(new)


def _grade(fl, store, cfg):
    rows = [r for r in store.player_rows(fl["pid"]) if r["game"] == fl["game_id"]]
    if fl["game_id"] not in store.games:
        return None, None, None
    it = {"shown": {"pid": fl["pid"], "line": fl["line"], "side": fl["side"], "price": fl["price"], "market": fl["market"]}}
    return engine.grade_one(it, rows, cfg)


def summary(store, cfg):
    """Rebuild data/watch/pin_judge/summary.json from the flags and the box-score store."""
    w = (cfg.get("watch") or {}).get(TRACK) or {}
    nights = {}
    tot = {"w": 0, "l": 0, "push": 0, "void": 0, "units": 0.0, "pending": 0}
    for fl in read_flags():
        res, actual, units = _grade(fl, store, cfg)
        b = dict(fl, result=res, actual=actual, units=units)
        nights.setdefault(fl["slate"], []).append(b)
        if res is None:
            tot["pending"] += 1
        else:
            tot[{"W": "w", "L": "l", "PUSH": "push", "VOID": "void"}[res]] += 1
            tot["units"] += units or 0.0
    out = []
    for d in sorted(nights, reverse=True):
        bs = sorted(nights[d], key=lambda b: (b["start"], -b["pin_ev"]))
        out.append({"date": d, "w": sum(b["result"] == "W" for b in bs), "l": sum(b["result"] == "L" for b in bs),
                    "units": round(sum(b["units"] or 0 for b in bs), 2), "bets": bs})
    n = tot["w"] + tot["l"]
    doc = {"track": TRACK, "label": w.get("label", "Pinnacle as the price judge"), "about": w.get("about"),
           "from_slate": w.get("from_slate"), "min_ev": w.get("min_ev"), "updated_at": common.iso(common.now()),
           "total": dict(tot, units=round(tot["units"], 2), hit_rate=round(tot["w"] / n, 4) if n else None), "nights": out}
    path = os.path.join(_dir(), "summary.json")
    old = common.read_json(path) or {}
    if {k: v for k, v in old.items() if k != "updated_at"} != {k: v for k, v in doc.items() if k != "updated_at"}:
        common.write_json(path, doc)
    return doc
