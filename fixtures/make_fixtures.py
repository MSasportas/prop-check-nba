#!/usr/bin/env python3
"""Writes the page's QA fixtures: fixtures/NAME/{slate,record,rules,live,headshots}.json (+ record/<month>.json, watch/).

Test data only: every slate carries "fixture": true and the page shows a "Test data" tag. Open with index.html?fixture=NAME.
Each slate carries "fixture_now" so the page's clock sits at a fixed moment (override with ?now=ISO).
The Record views come from scripts/record.py build_views and live.json from scripts/live.py build (fed ESPN summaries shaped
exactly like the real ones), so the fixtures show what the pipeline makes. The older hand-written fixtures (empty, nokeys,
normal, pinsolo) are left as they are.
Run:  python3 fixtures/make_fixtures.py
"""
import copy
import json
import os
import random
import shutil
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import common  # noqa: E402
import engine  # noqa: E402
import espn  # noqa: E402
import live  # noqa: E402
import odds  # noqa: E402
import record  # noqa: E402
import run  # noqa: E402
import teams  # noqa: E402

D = "2026-11-04"
HR_SLIP = "https://share.hardrock.bet/Pt0T/bet?deep_link_value=hardrock://betslip/"
DK = "https://sportsbook.draftkings.com/event/31?outcomes=0QA%s"
HS = "https://a.espncdn.com/i/headshots/nba/players/full/%s.png"
NOUN = {"rebounds": "rebounds", "points": "points", "assists": "assists", "threes": "threes"}
KEYS = ["minutes", "points", "fieldGoalsMade-fieldGoalsAttempted", "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "freeThrowsMade-freeThrowsAttempted", "rebounds", "assists", "turnovers", "steals", "blocks", "offensiveRebounds",
        "defensiveRebounds", "fouls", "plusMinus"]
NAMES = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]


def t(hm, day=D):
    return "%sT%s:00-05:00" % (day, hm)


def cfg():
    return json.load(open(os.path.join(ROOT, "config", "rules.json")))


# ---------------------------------------------------------------- ESPN summary, shaped like the real one (event 401909922)
def summary(gid, away, home, state, period=None, clock=None, detail=None, name=None, score=(0, 0), players=(), start=None):
    """players: [(ESPN id, name, team code, {"points", "rebounds", "assists", "threes"} or None = did not play)]"""
    short = {"in": detail, "post": "Final", "pre": "7:00 PM"}.get(state)
    st = {"displayClock": clock or "0.0", "period": period or 0,
          "type": {"state": state, "name": name or {"in": "STATUS_IN_PROGRESS", "post": "STATUS_FINAL", "pre": "STATUS_SCHEDULED"}[state],
                   "completed": state == "post", "detail": detail or short, "shortDetail": short},
          "displayPeriod": {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(period, "OT")}
    comp = [{"homeAway": "home", "score": str(score[1]), "team": {"abbreviation": home}, "linescores": [{}] * max(4, period or 0)},
            {"homeAway": "away", "score": str(score[0]), "team": {"abbreviation": away}, "linescores": [{}] * max(4, period or 0)}]
    blocks = []
    for code in (away, home):
        ath = []
        for pid, nm, tm, s in players:
            if tm != code:
                continue
            if s is None:
                ath.append({"active": False, "athlete": {"id": pid, "displayName": nm, "headshot": {"href": HS % pid}},
                            "starter": False, "didNotPlay": True, "reason": "INJURY", "ejected": False, "stats": []})
                continue
            row = ["24", str(s.get("points", 0)), "5-11", "%d-%d" % (s.get("threes", 0), s.get("threes", 0) + 3), "2-2",
                   str(s.get("rebounds", 0)), str(s.get("assists", 0)), "1", "1", "0", "1", "3", "2", "+4"]
            ath.append({"active": True, "athlete": {"id": pid, "displayName": nm, "headshot": {"href": HS % pid}},
                        "starter": True, "didNotPlay": False, "reason": None, "ejected": False, "stats": row})
        blocks.append({"team": {"abbreviation": code}, "statistics": [{"names": NAMES, "keys": KEYS, "labels": NAMES,
                                                                       "descriptions": NAMES, "athletes": ath, "totals": []}]})
    return {"header": {"id": gid, "competitions": [{"date": start or t("19:00"), "status": st, "competitors": comp}]},
            "boxscore": {"players": blocks, "teams": []}}


# ---------------------------------------------------------------- tonight (2026-11-04, 9:20 PM)
NOW = t("21:20")
# id, away, home, tip, scoreboard state, detail
GAMES = [
    ("401909901", "PHI", "DET", "19:00", "post", "Final"),
    ("401909902", "ATL", "WSH", "19:00", "in", "2:31 - OT"),
    ("401909903", "BKN", "CHA", "19:00", "post", "Final"),
    ("401909904", "NY", "BOS", "19:30", "in", "6:40 - 4th"),
    ("401909905", "ORL", "MIL", "20:10", "in", "Halftime"),
    ("401909906", "DEN", "HOU", "20:00", "in", "End of 3rd Quarter"),
    ("401909907", "POR", "SAC", "22:00", "pre", "10:00 PM"),
    ("401909908", "MEM", "LAL", "22:00", "pre", "10:00 PM"),
    ("401909909", "UTAH", "PHX", "22:30", "pre", "10:30 PM"),
]
LIVE = {   # game id -> (state, period, clock, detail, type name, score)
    "401909901": ("post", 4, "0.0", "Final", None, (104, 111)),
    "401909902": ("in", 5, "2:31", "2:31 - OT", None, (118, 116)),
    "401909903": ("post", 4, "0.0", "Final", None, (99, 107)),
    "401909904": ("in", 4, "6:40", "6:40 - 4th Quarter", None, (88, 91)),
    "401909905": ("in", 2, "0.0", "Halftime", "STATUS_HALFTIME", (52, 58)),
    "401909906": ("in", 3, "0.0", "End of 3rd Quarter", "STATUS_END_PERIOD", (80, 77)),
}
# key, game, ESPN id, player, team, market, side, line, price, Pinnacle before/after chance, Pinnacle prices, state when shown,
# added at, live stat (None = DNP), result
PICKS = [
    ("embi", "401909901", "3059318", "Joel Embiid", "PHI", "threes", "under", 0.5, 160, .37, .41, (190, 150), "clear", "17:30", 0, "W"),
    ("cade", "401909901", "4432166", "Cade Cunningham", "DET", "points", "over", 24.5, -125, .52, .565, (-108, -140), "starters", "18:20", 21, "L"),
    ("trae", "401909902", "4277905", "Trae Young", "ATL", "assists", "over", 10.5, 110, .45, .49, (125, 100), "clear", "17:30", 12, None),
    ("mill", "401909903", "4433134", "Miles Bridges", "CHA", "rebounds", "over", 6.5, -115, .50, .545, (-102, -128), "clear", "17:30", None, "VOID"),
    ("mpj", "401909903", "4278104", "Michael Porter Jr", "BKN", "points", "under", 21.5, -125, .48, .556, (-106, -147), "clear", "17:30", 25, "L"),
    ("brun", "401909904", "3934672", "Jalen Brunson", "NY", "points", "under", 27.5, -120, .49, .55, (-104, -132), "starters", "18:00", 29, None),
    ("brow", "401909904", "3917376", "Jaylen Brown", "BOS", "threes", "over", 2.5, 120, .42, .47, (135, 108), "clear", "18:00", 3, None),
    ("bane", "401909905", "4066354", "Paolo Banchero", "ORL", "rebounds", "over", 8.5, -110, .50, .54, (-104, -125), "early", "18:50", 5, None),
    ("gian", "401909905", "3032977", "Giannis Antetokounmpo", "MIL", "assists", "under", 6.5, -130, .52, .575, (-112, -142), "starters", "19:30", 2, None),
    ("joki", "401909906", "3112335", "Nikola Jokic", "DEN", "threes", "under", 1.5, -140, .55, .60, (-126, -158), "clear", "18:50", 1, None),
    # open (pre) picks: three from the 8:30 check, two NEW from the 9:15 check
    ("sabo", "401909907", "3155942", "Domantas Sabonis", "SAC", "rebounds", "over", 12.5, -115, .50, .55, (-104, -130), "starters", "20:30", None, None),
    ("simo", "401909907", "4683772", "Shaedon Sharpe", "POR", "points", "under", 19.5, 105, .45, .505, (118, -104), "clear", "20:30", None, None),
    ("jaja", "401909908", "4277961", "Jaren Jackson Jr", "MEM", "rebounds", "under", 6.5, -110, .50, .545, (-106, -128), "early", "20:30", None, None),
    ("dlux", "401909908", "3945274", "Luka Doncic", "LAL", "assists", "over", 8.5, -120, .51, .56, (-108, -136), "clear", "21:15", None, None),
    ("book", "401909909", "3136193", "Devin Booker", "PHX", "threes", "over", 2.5, 125, .41, .455, (142, 112), "early", "21:15", None, None),
    # off the board before tip: injury news (Questionable), Hard Rock took the line down, and a scratch (Out: hidden)
    ("reav", "401909908", "4066457", "Austin Reaves", "LAL", "points", "over", 18.5, -115, .50, .545, (-104, -129), "clear", "20:30", None, "PULL:status:questionable"),
    ("keon", "401909909", "4433136", "Keyonte George", "UTAH", "assists", "under", 5.5, -105, .49, .54, (-102, -124), "clear", "20:30", None, "PULL:line_gone"),
    ("murr", "401909907", "4278053", "Keegan Murray", "SAC", "rebounds", "under", 7.5, -110, .50, .545, (-106, -128), "clear", "20:30", None, "PULL:status:out"),
]
HEADS_SKIP = {"4433134"}                     # no photo on file (the page shows none)
HEADS_BAD = {"3136193": "http://evil.example/x.png"}   # a link that is not ESPN's: never shown


def be(price):
    return odds.break_even(price)


def pick_id(k):
    p = next(x for x in PICKS if x[0] == k)
    return "%s:%s:%s:%s:%s:%s" % (D, p[1], p[2], p[5], engine.fmt_line(p[7]), p[6])


def game_of(gid):
    return next(g for g in GAMES if g[0] == gid)


def body(p):
    k, gid, pid, nm, tm, mk, sd, ln, pr, pb, pa, pins, st, at = p[:14]
    g = game_of(gid)
    home = tm == g[2]
    opp = g[1] if home else g[2]
    ev = round(odds.ev(pa, pr), 4)
    read = {"17:30": "B", "18:00": "B", "18:20": "C", "18:50": "B", "19:30": "C", "20:30": "B", "21:15": "C"}[at]
    r = {"pin_price_before": pins[0], "pin_price_after": pins[1], "side": sd, "pin_before": pb, "pin_after": pa, "price": pr,
         "books": {"hardrock": {"price": pr, "ev_vs_pin": ev}}}
    if k == "dlux":                          # DraftKings passed too: the slate still lists it, the page never shows it
        r["books"]["draftkings"] = {"price": -110, "ev_vs_pin": round(odds.ev(pa, -110), 4)}
    return {"rule": "pin_solo", "player": nm, "pid": pid, "team": tm, "opp": opp, "home": home, "game_id": gid,
            "start": t(g[3]), "market": mk, "line": ln, "side": sd, "bet": engine.bet_text(sd, ln, NOUN[mk]), "price": pr,
            "price_at": t(at), "read": read, "p": pa, "p_pct": engine.pct_round(pa), "breakeven": round(be(pr), 4),
            "breakeven_pct": engine.pct_round(be(pr)), "pin_before": pb, "pin_after": pa, "pin_price_before": pins[0],
            "pin_price_after": pins[1], "ev_vs_pin": ev, "final_ev": round(pa - pb, 4), "reason": engine.solo_reason(r),
            "state": st, "window": engine.window_label({"B": "A", "C": "B", "D": "C"}[read], read), "book": "hardrock",
            "books": r["books"], "n_others": 6, "n_books": 6, "others_move": 0.004}


def tonight_events():
    ev = []
    for p in PICKS:
        b = body(p)
        i = pick_id(p[0])
        ev.append({"t": "shown", "id": i, "at": t(p[13]), "slate": D, "kind": "single", "pick": b})
        res = p[15]
        if isinstance(res, str) and res.startswith("PULL:"):
            bits = res.split(":")
            if bits[1] == "status":
                ev.append({"t": "pulled", "id": i, "at": t("21:10"), "code": "status", "reason": "Now listed %s" % bits[2],
                           "if_bet": engine.OUT_IF_BET})
            else:
                ev.append({"t": "pulled", "id": i, "at": t("21:15"), "code": "line_gone", "reason": "Hard Rock took the line down",
                           "if_bet": "Got %s? Your bet still stands." % common.fmt_price(p[8])})
            continue
        g = game_of(p[1])
        if g[4] in ("in", "post"):
            ev.append({"t": "locked", "id": i, "at": t(g[3]), "state": "locked"})
        if res in ("W", "L"):
            ev.append({"t": "graded", "id": i, "at": t("21:05"), "result": res, "actual": None,
                       "actual_text": "%d %s" % (p[14], NOUN[p[5]] if p[14] != 1 else NOUN[p[5]].rstrip("s")),
                       "price": p[8], "units": record.single_units(res, p[8])})
        elif res == "VOID":
            ev.append({"t": "graded", "id": i, "at": t("21:05"), "result": "VOID", "actual": None, "actual_text": "did not play",
                       "price": p[8], "units": 0.0})
    return ev


def history_events(rng):
    """Oct 20 - Nov 3: about 55 graded picks across both months (calendar, cuts, month files)."""
    ev, days = [], ["2026-10-%02d" % d for d in range(20, 32)] + ["2026-11-01", "2026-11-02"]
    players = [("Josh Hart", "3062679", "NY", "BOS"), ("Jalen Duren", "4433621", "DET", "ORL"), ("Alperen Sengun", "4871144", "HOU", "DAL"),
               ("Derrick White", "3078576", "BOS", "NY"), ("Tyrese Maxey", "4431678", "PHI", "MIA"), ("Scottie Barnes", "4433134", "TOR", "CHI"),
               ("Evan Mobley", "4432158", "CLE", "IND"), ("Anthony Edwards", "4594268", "MIN", "UTAH"), ("Jalen Green", "4437244", "PHX", "SA")]
    markets = list(NOUN)
    for d in days:
        if d in ("2026-10-23", "2026-10-29"):
            continue                          # nights with no picks
        for j in range(rng.choice([1, 2, 3, 4, 5])):
            nm, pid, tm, opp = rng.choice(players)
            mk = rng.choice(markets)
            ln = {"rebounds": 7.5, "points": 21.5, "assists": 5.5, "threes": 2.5}[mk] + rng.choice([-1, 0, 1])
            sd = rng.choice(["over", "under"])
            pr = rng.choice([-195, -170, -150, -140, -125, -120, -115, -110, -105, 100, 110, 125, 140])
            evp = rng.choice([0.004, 0.008, 0.012, 0.018, 0.026, 0.034, 0.061])
            pa = round(min(0.9, (1 + evp) * be(pr)), 4)
            gid = "4019%05d" % (rng.randrange(99999))
            i = "%s:%s:%s:%s:%s:%s" % (d, gid, pid, mk, engine.fmt_line(ln), sd)
            st = rng.choice(["early", "clear", "clear", "clear", "starters"])
            b = {"rule": "pin_solo", "player": nm, "pid": pid, "team": tm, "opp": opp, "home": False, "game_id": gid,
                 "start": "%sT19:00:00-04:00" % d, "market": mk, "line": ln, "side": sd, "bet": engine.bet_text(sd, ln, NOUN[mk]),
                 "price": pr, "price_at": "%sT18:20:00-04:00" % d, "read": "C", "p": pa, "p_pct": engine.pct_round(pa),
                 "breakeven": round(be(pr), 4), "breakeven_pct": engine.pct_round(be(pr)), "ev_vs_pin": evp, "state": st,
                 "window": "90 → 45 min", "book": "hardrock", "pin_before": round(pa - 0.03, 4), "pin_after": pa,
                 "reason": "Pinnacle moved."}
            ev.append({"t": "shown", "id": i, "at": "%sT18:20:00-04:00" % d, "slate": d, "kind": "single", "pick": b})
            ev.append({"t": "locked", "id": i, "at": "%sT19:00:00-04:00" % d, "state": "locked"})
            res = "VOID" if rng.random() < 0.05 else ("W" if rng.random() < pa + 0.06 else "L")
            x = int(ln + (1.5 if (res == "W") == (sd == "over") else -1.5))
            ev.append({"t": "graded", "id": i, "at": "%sT22:40:00-04:00" % d, "result": res, "actual": None,
                       "actual_text": "did not play" if res == "VOID" else "%d %s" % (x, NOUN[mk]), "price": pr,
                       "units": record.single_units(res, pr)})
    return ev


def build_record(events, c):
    tmp = tempfile.mkdtemp(prefix="pcnba_fx_")
    old = os.environ.get("PC_DATA_DIR")
    try:
        os.makedirs(os.path.join(tmp, "replay"))
        shutil.copy(os.path.join(ROOT, "data", "replay", "pin_solo.json"), os.path.join(tmp, "replay", "pin_solo.json"))
        os.environ["PC_DATA_DIR"] = tmp
        return record.build_views(events, c)
    finally:
        if old is None:
            os.environ.pop("PC_DATA_DIR", None)
        else:
            os.environ["PC_DATA_DIR"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def build_live(events, now_iso, gen_at=None):
    tmp = tempfile.mkdtemp(prefix="pcnba_fxl_")
    old = os.environ.get("PC_ESPN_FIXTURE_DIR")
    try:
        for gid, (state, per, clk, det, name, score) in LIVE.items():
            g = game_of(gid)
            ps = [(p[2], p[3], p[4], (None if p[14] is None else {p[5]: p[14]})) for p in PICKS if p[1] == gid]
            json.dump(summary(gid, g[1], g[2], state, per, clk, det, name, score, ps, t(g[3])),
                      open(os.path.join(tmp, "summary_%s.json" % gid), "w"))
        os.environ["PC_ESPN_FIXTURE_DIR"] = tmp
        espn.clear_cache()
        for gid in LIVE:
            espn.summary(gid)                 # what the grade step reads on a run
        doc = live.build(common.parse_iso(now_iso), D, sched_games(), events)
        if gen_at:
            doc["generated_at"] = gen_at
            for g in doc["games"]:
                g["updated_at"] = gen_at
        return doc
    finally:
        espn.clear_cache()
        if old is None:
            os.environ.pop("PC_ESPN_FIXTURE_DIR", None)
        else:
            os.environ["PC_ESPN_FIXTURE_DIR"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def sched_games():
    out = []
    for gid, a, hm, tip, st, det in GAMES:
        sc = LIVE.get(gid, (None,) * 5 + ((None, None),))[5]
        out.append({"id": gid, "start": t(tip), "away": a, "home": hm, "state": st, "detail": det,
                    "completed": st == "post", "score": {a: sc[0], hm: sc[1]}})
    return out


def slate_doc(events, c, now_iso, gen_at=None):
    items = record.fold(events)
    picks = []
    for it in sorted(items.values(), key=lambda x: (-(x["shown"].get("final_ev") or 0), x["id"])):
        if it["slate"] != D:
            continue
        sh, gr = it["shown"], it["graded"]
        p = {k: sh.get(k) for k in ("player", "pid", "game_id", "start", "bet", "market", "side", "line", "price", "price_at", "read",
                                    "p", "p_pct", "breakeven", "breakeven_pct", "reason", "rule", "pin_before", "pin_after",
                                    "pin_price_before", "pin_price_after", "ev_vs_pin", "window", "book", "books", "final_ev",
                                    "home")}
        p["id"] = it["id"]
        p["team"], p["opp"] = teams.show(sh["team"]), teams.show(sh["opp"])
        st = "locked" if it["locked_at"] else it["state"]
        p["state"], p["state_label"] = st, engine.STATE_LABEL.get(st, "Early")
        g = game_of(sh["game_id"])
        p["price_final"] = g[4] == "pre" and sh["price_at"] >= t("21:15")
        p["pulled"] = run.pulled_view(it["pulled"])
        p["added_at"] = it["shown_at"]
        p["result"] = {"result": gr["result"], "actual": gr.get("actual_text"), "units": gr["units"]} if gr else None
        p["links"] = None
        if not it["pulled"] and not it["locked_at"] and not gr:
            oid = "51016545%011d" % (zlib.crc32(it["id"].encode()) % 10 ** 11)
            p["links"] = {"hardrock": {"url": HR_SLIP + oid, "price": sh["price"]},
                          "draftkings": {"url": DK % oid, "price": -110} if "draftkings" in (sh.get("books") or {}) else None}
        picks.append(p)
    rank = 0
    for p in picks:
        if not p["pulled"] and p["state"] != "locked":
            rank += 1
            p["rank"] = rank
        else:
            p["rank"] = None
    glist = []
    for gid, a, hm, tip, st, det in GAMES:
        tipt = t(tip)
        checks = [{"read": "B", "at": t("%02d:%02d" % divmod(int(tip[:2]) * 60 + int(tip[3:]) - 90, 60))},
                  {"read": "C", "at": t("%02d:%02d" % divmod(int(tip[:2]) * 60 + int(tip[3:]) - 45, 60))}]
        checks = [x for x in checks if x["at"] <= now_iso]
        started = st != "pre"
        nxt = None if started else t("%02d:%02d" % divmod(int(tip[:2]) * 60 + int(tip[3:]) - 20, 60))
        lu = {"away": "confirmed" if started or gid == "401909907" else "expected",
              "home": "confirmed" if started or gid in ("401909907", "401909908") else "expected"}
        glist.append({"id": gid, "start": tipt, "away": teams.show(a), "home": teams.show(hm), "state": st, "detail": det,
                      "lineups": lu, "read_at": checks[-1]["at"] if checks else None,
                      "picks": sum(1 for p in picks if p["game_id"] == gid and not p["pulled"]), "checks": checks,
                      "last_check_at": checks[-1]["at"] if checks else None, "final": started, "next_check_at": nxt,
                      "next_check_read": None if started else "D",
                      "injury_clear": {"away": gid != "401909908", "home": gid not in ("401909908", "401909909")}})
    gen = gen_at or "2026-11-04T21:15:04-05:00"
    return {"fixture": True, "fixture_now": now_iso, "slate": D, "valid_until": "2026-11-05T05:00:00-05:00", "banners": [],
            "status": {"odds": {"keys": 6, "pool_left": 2412, "low": False, "refused": False, "no_keys": False, "days_left": 27,
                                "allowance": 14.1, "reads": ["A", "B", "C", "D"]},
                       "next_read_at": "2026-11-04T21:40:00-05:00", "last_read_at": "2026-11-04T21:15:00-05:00",
                       "last_run": {"ok": True, "at": gen},
                       "feeds": {"schedule": True, "injuries": True, "rosters": True, "grade": True, "live": True,
                                 "lineups": {"ok": True, "at": "2026-11-04T21:10:00-05:00",
                                             "confirmed": ["BKN", "BOS", "CHA", "DEN", "DET", "HOU", "LAL", "MEM", "MIL", "NY", "ORL",
                                                           "PHI", "POR", "SAC", "ATL", "WSH"]}}},
            "games": glist, "picks": picks, "empty": None, "counts": {"lines_read": 1302, "passing": 24, "games": len(GAMES)},
            "safety_paused": False, "ui": c["ui"], "generated_at": gen, "status_at": gen}


def headshots():
    out = {}
    for p in PICKS:
        if p[2] in HEADS_SKIP:
            continue
        out[p[2]] = HEADS_BAD.get(p[2], HS % p[2])
    return out


def lab_summary():
    return {"track": "pin_judge", "label": "Pinnacle as the price judge", "from_slate": "2026-10-28", "min_ev": 0.02,
            "updated_at": "2026-11-04T21:15:04-05:00",
            "total": {"w": 19, "l": 14, "push": 0, "void": 1, "units": 3.86, "pending": 4, "hit_rate": 0.5758}, "nights": []}


def write(name, files):
    d = os.path.join(HERE, name)
    if os.path.isdir(d):
        shutil.rmtree(d)
    for rel, doc in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")


def main():
    c = cfg()
    rng = random.Random(20261104)
    events = history_events(rng) + tonight_events()
    rec, months = build_record(events, c)
    rules = run.rules_doc(c)
    rules["fixture"] = True
    base = {"record.json": dict(rec, fixture=True), "rules.json": rules, "headshots.json": headshots(),
            "watch/pin_judge/summary.json": lab_summary()}
    for m, doc in months.items():
        base["record/%s.json" % m] = doc
    sl = slate_doc(events, c, NOW)
    lv = build_live(events, NOW)

    def fx(name, slate=None, livedoc=lv, extra=None, drop=()):
        files = dict(base, **{"slate.json": slate or sl})
        if livedoc is not None:
            files["live.json"] = livedoc
        files.update(extra or {})
        for k in drop:
            files.pop(k, None)
        write(name, files)

    fx("tonight")
    fx("livestale", livedoc=build_live(events, NOW, gen_at="2026-11-04T20:40:04-05:00"))
    st = slate_doc(events, c, NOW, gen_at="2026-11-04T20:35:04-05:00")
    fx("stale", slate=st)
    lp = copy.deepcopy(sl)
    lp["status"]["odds"].update({"pool_left": 96, "low": True, "days_left": 9})
    lp["banners"] = [{"level": "warn", "text": "Odds keys are running low: fewer price checks per game until they refill on the 1st. "
                                               "More keys would fix it."}]
    fx("lowpool", slate=lp)
    nk = copy.deepcopy(sl)
    nk["status"]["odds"] = {"keys": 0, "pool_left": None, "low": False, "refused": False, "no_keys": True, "days_left": None}
    nk["banners"] = [{"level": "stop", "text": "No odds keys yet: Hard Rock prices can't be read, so there are no picks."}]
    nk["picks"] = [p for p in nk["picks"] if p["state"] == "locked"]
    nk["empty"] = {"text": "No picks yet today", "why": "No Hard Rock prices can be read until odds keys are added.", "next": None}
    fx("nokeys2", slate=nk)
    # every game started: Picks says so, Live has everything
    al = copy.deepcopy(sl)
    al["fixture_now"] = "2026-11-04T23:05:00-05:00"
    for g in al["games"]:
        if g["state"] == "pre":
            g["state"], g["detail"], g["final"], g["next_check_at"] = "in", "8:12 - 2nd", True, None
    for p in al["picks"]:
        if p["rank"]:
            p["state"], p["state_label"], p["rank"], p["links"] = "locked", "Locked", None, None
    al["empty"] = {"text": "No open picks right now", "why": "Every game has started.", "next": None}
    fx("allstarted", slate=al, livedoc=dict(lv, generated_at="2026-11-04T23:00:04-05:00"))
    # a quiet night: games, no picks yet, live.json absent
    em = copy.deepcopy(sl)
    em["fixture_now"] = "2026-11-04T17:10:00-05:00"
    em["picks"] = []
    for g in em["games"]:
        g.update({"state": "pre", "detail": "7:00 PM", "checks": [], "final": False, "last_check_at": None, "read_at": None,
                  "next_check_at": t("%02d:%02d" % divmod(int(g["start"][11:13]) * 60 + int(g["start"][14:16]) - 90, 60)),
                  "next_check_read": "B", "lineups": {"away": "expected", "home": "none"}, "injury_clear": {"away": None, "home": None}})
    em["empty"] = {"text": "No picks yet today", "why": "1302 lines read. Pinnacle hasn't moved on any of them yet.",
                   "next": "2026-11-04T17:30:00-05:00"}
    em["generated_at"] = em["status_at"] = em["status"]["last_run"]["at"] = "2026-11-04T17:05:04-05:00"
    fx("quiet", slate=em, livedoc=None)
    # yesterday's slate still up the next morning
    ex = copy.deepcopy(sl)
    ex["fixture_now"] = "2026-11-05T09:40:00-05:00"
    fx("expired", slate=ex)
    # sources down: Rotowire and ESPN injuries failed, the last run failed, safety pause on
    fd = copy.deepcopy(sl)
    fd["status"]["feeds"].update({"injuries": False, "lineups": {"ok": False, "at": "2026-11-04T19:40:00-05:00", "confirmed": []}})
    fd["status"]["last_run"] = {"ok": False, "at": "2026-11-04T21:15:04-05:00"}
    fd["safety_paused"] = True
    fd["banners"] = [{"level": "stop", "text": c["safety_pause"]["text"] + " " + c["safety_pause"]["sub"]},
                     {"level": "info", "text": "The starting-lineup source didn't answer at 9:15 PM. Picks can't reach Starters confirmed until it does."},
                     {"level": "warn", "text": "The injury list didn't answer at 9:15 PM. Using the last known one."}]
    fx("feedsdown", slate=fd, drop=("headshots.json",))
    print("wrote: tonight livestale stale lowpool nokeys2 allstarted quiet expired feedsdown")


if __name__ == "__main__":
    main()
