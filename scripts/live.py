"""live.py: data/live.json, the page's Live tab. Display only: never a pick, a price, a grade or a Record event.

For every game of tonight's slate that has started and has a pick on the Record, from the ESPN summary that the grade step
already read this run (espn's in-run memo: no extra calls; grade reads every game that still has a locked or pulled pick
waiting for its grade):
  games[]  game_id, state (pre / in / post), period (5 = OT), clock ("11:17"), detail ("11:17 - 2nd Quarter", "Halftime"),
           in_break (halftime or end of a quarter), away / home {abbrev, score}, updated_at (when that summary was read)
  picks{}  pick id -> {game_id, market, stat, dnp}: the player's number so far for the pick's market (points, rebounds, assists,
           threes made), null when he is not in the box (yet)
A game whose summary was not read this run keeps its last entry from the previous live.json of the same slate (or, if it has
none, the scoreboard's score and detail); a graded pick's stat comes from the Record's grade ("14 points" -> 14). Nothing is
written when no slate game with a pick has started, or when nothing changed. A soft step: a failure never fails a run.
"""
import re

import common
import engine
import espn
import record
import teams


def path():
    return common.dpath("live.json")


def _graded_stat(gr):
    """The Record's own number once graded ("14 points" -> 14); None for a void ("did not play")."""
    if not gr or gr.get("result") not in ("W", "L", "PUSH"):
        return None
    if isinstance(gr.get("actual"), (int, float)) and not isinstance(gr.get("actual"), bool):
        return int(gr["actual"])
    m = re.match(r"^\s*(\d+)\b", str(gr.get("actual_text") or ""))
    return int(m.group(1)) if m else None


def _from_scoreboard(g):
    sc = g.get("score") or {}
    side = lambda k: {"abbrev": teams.show(g[k]), "score": _int(sc.get(g[k]))}
    return {"game_id": g["id"], "state": g.get("state"), "period": None, "clock": None, "detail": g.get("detail"),
            "in_break": False, "away": side("away"), "home": side("home"), "updated_at": None}


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def build(now, slate, games, events, old=None):
    """-> the live.json doc, or None when there is nothing to show."""
    at = common.iso(now)
    items = record.fold(events)
    by_game = {}
    for it in items.values():
        if it["kind"] == "single" and it["slate"] == slate:
            by_game.setdefault(str(it["shown"].get("game_id")), []).append(it)
    old = old if isinstance(old, dict) and old.get("slate_date") == slate else {}
    old_games = {str(g.get("game_id")): g for g in old.get("games") or [] if isinstance(g, dict)}
    old_picks = old.get("picks") if isinstance(old.get("picks"), dict) else {}
    out_games, out_picks = [], {}
    for g in sorted(games, key=lambda x: (x["start"], x["id"])):
        gid = str(g["id"])
        its = by_game.get(gid)
        if not its or not engine.started(g, now):
            continue
        s = espn.summary_cached(gid)                     # this run's read only
        ent = espn.game_state(s) if s else None
        players = None
        if ent is not None:
            ent = {"game_id": gid, "state": ent["state"], "period": ent["period"], "clock": ent["clock"],
                   "detail": ent["detail"], "in_break": ent["in_break"], "away": ent["away"], "home": ent["home"],
                   "updated_at": at}
            players = espn.player_stats(s)
        else:
            ent = old_games.get(gid) or _from_scoreboard(g)
        out_games.append(ent)
        for it in sorted(its, key=lambda x: x["id"]):
            sh = it["shown"]
            mk = sh.get("market", "rebounds")
            if players is not None:
                row = players.get(str(sh.get("pid"))) or {}
                stat, dnp = row.get(mk), bool(row.get("dnp"))
            else:
                o = old_picks.get(it["id"]) or {}
                stat, dnp = o.get("stat"), bool(o.get("dnp"))
            gs = _graded_stat(it["graded"])
            if gs is not None:
                stat, dnp = gs, False
            elif it["graded"] and it["graded"].get("result") == "VOID":
                dnp = True
            out_picks[it["id"]] = {"game_id": gid, "market": mk, "stat": stat if isinstance(stat, int) else None, "dnp": dnp}
    if not out_games:
        return None
    return {"slate_date": slate, "generated_at": at, "games": out_games, "picks": out_picks}


def step(now, slate, games, events):
    """The run.py step. Returns a short note."""
    old = common.read_json(path())
    doc = build(now, slate, games or [], events or [], old)
    if doc is None:
        return "skipped: no started game with a pick"
    same = isinstance(old, dict) and {k: v for k, v in old.items() if k != "generated_at"} == \
        {k: v for k, v in doc.items() if k != "generated_at"}
    if same:
        return "skipped: no change"
    common.write_json(path(), doc)
    fresh = sum(1 for g in doc["games"] if g.get("updated_at") == doc["generated_at"])
    return "%d game(s), %d read this run" % (len(doc["games"]), fresh)
