#!/usr/bin/env python3
"""run.py: the ONLY entry point. One run = one cycle; it decides what is due from the files on disk.

  schedule   ESPN scoreboard for today's slate (and yesterday's until it is graded); month game counts once a day
  rosters    ESPN rosters of today's teams once a day (names -> ids for the odds feed and Rotowire)
  injuries   ESPN league injury list every run; Rotowire lineups + tags every run inside the lineup window
  odds       the A / B / C / D reads that are due (odds.py)
  engine     picks, pulls, settled level, lock at tip (engine.py), straight into the Record
  grade      every locked or pulled pick whose game is final; every final game's box score into the stats store
  publish    data/record.json (+ month files), data/rules.json, data/slate.json, data/status.json, data/shadow/<slate>.json
  notify     Discord (notify.py)
Safe to run twice. Every write is atomic. Flags: --explain (print every line's verdict, write nothing),
--rebuild-record (rebuild the Record views from the log and stop).
"""
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import engine  # noqa: E402
import espn  # noqa: E402
import lineups as rotowire  # noqa: E402
import names  # noqa: E402
import notify  # noqa: E402
import odds  # noqa: E402
import record  # noqa: E402
import stats  # noqa: E402
import teams  # noqa: E402
import watch  # noqa: E402

SEASON_START = "2026-10-01"


def state(name):
    return common.dpath("state", name)


class Run:
    def __init__(self, explain=False):
        self.explain = explain
        self.cfg = common.load_config()
        self.now = common.now()
        self.slate = common.slate_date(self.now, self.cfg["ops"]["rollover_hour"])
        self.steps = {}
        self.errors = []

    def step(self, name, fn, soft=False):
        t0 = time.time()
        try:
            out = fn()
            if name not in self.steps:
                self.steps[name] = {"ok": True}
            self.steps[name]["sec"] = round(time.time() - t0, 1)
            return out
        except Exception as e:
            self.steps[name] = {"ok": False, "soft": soft, "error": common.short_err(e), "sec": round(time.time() - t0, 1)}
            common.log("step %s failed: %s" % (name, common.short_err(e)))
            traceback.print_exc()
            return None

    # ------------------------------------------------------------ schedule
    def schedule(self):
        cache = common.read_json(state("schedule.json"), {}) or {}
        games = espn.scoreboard(self.slate)
        if games is None:
            self.steps["schedule"] = {"ok": False, "soft": True, "error": "ESPN did not answer; using the last known schedule"}
            games = (cache.get("days") or {}).get(self.slate, [])
        days = cache.get("days") or {}
        days[self.slate] = games
        y = (datetime.fromisoformat(self.slate) - timedelta(days=1)).date().isoformat()
        if y not in days or any(not g["completed"] for g in days.get(y, [])):
            yg = espn.scoreboard(y)
            if yg is not None:
                days[y] = yg
        keep = (datetime.fromisoformat(self.slate) - timedelta(days=3)).date().isoformat()
        days = {d: v for d, v in days.items() if d >= keep}
        # games left this month (for the key allowance): counted once a day
        month = cache.get("month") or {}
        if month.get("made_for") != self.slate:
            counts, d = {}, datetime.fromisoformat(self.slate).date()
            end = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
            while d < end:
                gs = games if d.isoformat() == self.slate else espn.scoreboard(d.isoformat())
                counts[d.isoformat()] = len(gs) if gs is not None else (month.get("counts") or {}).get(d.isoformat(), 7)
                d += timedelta(days=1)
            month = {"made_for": self.slate, "counts": counts}
        common.write_json(state("schedule.json"), {"days": days, "month": month})
        self.days, self.games = days, games
        self.games_left_month = sum(n for d, n in month["counts"].items() if d >= self.slate)

    # ------------------------------------------------------------ rosters, injuries, lineups
    def rosters(self):
        cache = common.read_json(state("rosters.json"), {}) or {}
        if cache.get("slate") != self.slate:
            cache = {"slate": self.slate, "teams": {}}
        need = {g[k] for g in self.games for k in ("away", "home")}
        for code in sorted(need - set(cache["teams"])):
            r = espn.roster(code)
            if r is not None:
                cache["teams"][code] = r
        common.write_json(state("rosters.json"), cache)
        people = {}
        for code, rs in cache["teams"].items():
            for p in rs:
                people[p["pid"]] = {"pid": p["pid"], "name": p["name"], "team": code}
        # a team ESPN did not answer for: fall back to who played for it this season
        for code in need - set(cache["teams"]):
            for pid, rows in self.store.by_pid.items():
                if rows and rows[-1]["team"] == code and rows[-1]["date"] >= SEASON_START:
                    people.setdefault(pid, {"pid": pid, "name": rows[-1]["name"], "team": code})
            self.steps["rosters"] = {"ok": False, "soft": True, "error": "no ESPN roster for %s" % code}
        self.people = people

    def injuries(self):
        inj = espn.injuries()
        cache = state("injuries.json")
        if inj is None:
            self.steps["injuries"] = {"ok": False, "soft": True, "error": "ESPN injuries did not answer; last known used"}
            inj = (common.read_json(cache, {}) or {}).get("list", {})
        else:
            old = common.read_json(cache, {}) or {}
            if old.get("list") != inj:
                common.write_json(cache, {"at": common.iso(self.now), "list": inj})
        self.inj = inj

    def lineups(self):
        cache = common.read_json(state("lineups.json"), {}) or {}
        if cache.get("slate") != self.slate:
            cache = {"slate": self.slate, "teams": {}, "at": None}
        window = self.cfg["ops"]["lineups_window_min"]
        pre = [g for g in self.games if not g["completed"] and g["state"] == "pre"]
        due = any(0 <= (common.parse_iso(g["start"]) - self.now).total_seconds() / 60.0 <= window for g in pre) or \
            (pre and not cache.get("at"))
        if due:
            page = rotowire.fetch()
            if page is None:
                self.steps["lineups"] = {"ok": False, "soft": True, "error": "Rotowire did not answer"}
            else:
                parsed = rotowire.parse(page)
                if not parsed and pre:
                    self.steps["lineups"] = {"ok": False, "soft": True,
                                             "error": "Rotowire answered but no teams were found (layout changed?)"}
                today = {g[k] for g in self.games for k in ("away", "home")}
                for code, t in parsed.items():
                    if code in today:
                        cache["teams"][code] = t
                cache["at"] = common.iso(self.now)
                common.write_json(state("lineups.json"), cache)
        self.lineup_state = cache

    # ------------------------------------------------------------ odds + engine
    def odds_step(self):
        started = {g["id"]: engine.started(g, self.now) for g in self.games}

        def matcher_for(g):
            m = names.Matcher([p for p in self.people.values() if p["team"] in (g["away"], g["home"])])
            return m.find
        res = odds.run_reads(self.now, self.slate, self.games, self.games_left_month, self.cfg, matcher_for, started,
                             teams.code, dry_run=self.explain)
        self.odds_res = res
        if res["status"] == "failed":
            self.steps["odds"] = {"ok": False, "soft": True, "error": "; ".join(res["errors"][-2:])[:160]}
        return res

    def engine_step(self):
        self.ctx = engine.Context(self.cfg, self.now, self.slate, self.games, self.store, self.inj,
                                  self.lineup_state.get("teams"), self.people, SEASON_START)
        self.odds_doc = common.read_json(odds.odds_path(self.slate), {}) or {"fetches": []}
        if self.explain:
            for gid, fs in engine.latest_fetches(self.odds_doc).items():
                f = fs[-1]
                print("== %s @ %s  read %s at %s" % (f["away"], f["home"], f["read"], f["at"]))
                for r in engine.evaluate(f, self.ctx):
                    print("  %-24s %-5s %4s %5s  books %d  gap %s  final %s  %s" % (
                        r["name"][:24], r["side"], r["line"], common.fmt_price(r["price"]), r["n_books"],
                        "%+.1f%%" % (100 * r["gap_ev"]) if r["gap_ev"] is not None else "  -  ",
                        "%+.1f%%" % (100 * r["final_ev"]) if r["final_ev"] is not None else "  -  ",
                        r["why"] or "PASSES BOTH CHECKS"))
            return None
        evals, items, summ = engine.step(self.ctx, self.odds_doc)
        self.evals, self.items, self.summ = evals, items, summ
        shadow = {"slate": self.slate, "reads": []}
        for gid, pairs in evals.items():
            for f, rows in pairs:
                shadow["reads"].append({"game_id": gid, "read": f["read"], "at": f["at"],
                                        "rows": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                                  if k not in ("link", "name")} for r in rows]})
        shadow["solo"] = [{k: v for k, v in r.items() if k not in ("link", "name")}
                          for rows in (summ.get("solo_rows") or {}).values() for r in rows]
        common.write_json(common.dpath("shadow", "%s.json" % self.slate), shadow, pretty=False)
        try:
            self.watch_added = watch.flag(self.ctx, evals)
        except Exception as e:                              # behind the scenes only: never fails the run
            self.steps["watch"] = {"ok": False, "soft": True, "error": common.short_err(e)}

    # ------------------------------------------------------------ grading and the stats store
    def grade(self):
        items = record.fold(record.read_events())
        todo = [it for it in items.values() if it["kind"] == "single" and it["graded"] is None
                and (it["locked_at"] or it["pulled"])]
        boxes = {}
        finals = [g for d in self.days.values() for g in d if g["completed"] and g["id"] not in self.store.games]
        want = {it["shown"]["game_id"] for it in todo} | {g["id"] for g in finals}
        for gid in sorted(want):
            s = espn.summary(gid)
            if not s:
                continue
            pr, tr = espn.box(s)
            if pr is None:
                continue
            boxes[gid] = pr
            stats.add_game(stats.season_of(tr[0]["date"]), pr, tr)
        new = []
        for it in todo:
            gid = it["shown"]["game_id"]
            if gid not in boxes:
                # postponed / canceled, or still no final long after tip: void at 0 units (NHL rule), never left open
                g = next((x for d in self.days.values() for x in d if x["id"] == gid), None)
                name = (g or {}).get("status_name") or ""
                age_h = (self.now - common.parse_iso(it["shown"]["start"])).total_seconds() / 3600.0
                if "POSTPONED" in name or "CANCELED" in name or "CANCELLED" in name or \
                        age_h >= self.cfg["gap_guard"]["void_after_hours"]:
                    new.append({"t": "graded", "id": it["id"], "at": common.iso(self.now), "result": "VOID", "actual": None,
                                "actual_text": "game not played" if name else "no final result", "price": it["shown"]["price"],
                                "units": 0.0, "note": name or "no final %d hours after tip" % age_h})
                continue
            res, actual, units = engine.grade_one(it, boxes[gid], self.cfg)
            if res is None:
                continue
            new.append({"t": "graded", "id": it["id"], "at": common.iso(self.now), "result": res, "actual": None,
                        "actual_text": actual, "price": it["shown"]["price"], "units": units})
        if new:
            record.append(new)
        self.graded_now = len(new)

    # ------------------------------------------------------------ publish
    def publish(self):
        cfg, now = self.cfg, self.now
        record.write_views(cfg)
        common.write_json(common.dpath("rules.json"), rules_doc(cfg))
        items = record.fold(record.read_events())
        o = getattr(self, "odds_res", None) or {}
        plan = o.get("plan") or {}
        games = sorted(self.games, key=lambda g: (g["start"], g["id"]))
        last_read = {}
        for f in (getattr(self, "odds_doc", None) or {}).get("fetches", []):
            last_read[f["game_id"]] = max(last_read.get(f["game_id"], ""), f["at"])
        d_reads = {}
        for f in (getattr(self, "odds_doc", None) or {}).get("fetches", []):
            if f["read"] == cfg["gap_guard"]["final_pull"] and f.get("markets"):
                d_reads[f["game_id"]] = f["at"]
        picks = []
        for it in sorted([x for x in items.values() if x["slate"] == self.slate and x["kind"] == "single"],
                         key=lambda x: (-(x["shown"].get("final_ev") or 0), x["id"])):
            if it["pulled"] and it["pulled"].get("code") == "rule_change":
                continue                                   # taken down by a rule change: on the Record (pulled), not on Tonight
            sh, gr = it["shown"], it["graded"]
            p = {k: sh.get(k) for k in ("player", "pid", "team", "opp", "home", "game_id", "start", "bet", "market", "side", "line",
                                        "price", "price_at", "read", "p", "p_pct", "breakeven", "breakeven_pct",
                                        "market_fair", "n_books", "gap_ev", "final_ev", "model_p", "reason", "link", "rule",
                                        "pin_before", "pin_after", "pin_price_before", "pin_price_after", "others_move",
                                        "n_others", "ev_vs_pin", "window", "gap_vs_pin")}
            p["id"] = it["id"]
            p["window"] = record.window_of(sh)
            p["team"], p["opp"] = teams.show(sh["team"]), teams.show(sh["opp"])
            st = "locked" if it["locked_at"] else it["state"]
            p["state"], p["state_label"] = st, engine.STATE_LABEL.get(st, "Early")
            p["price_final"] = bool(d_reads.get(sh["game_id"])) and not it["locked_at"]
            p["pulled"] = {"at": it["pulled"]["at"], "reason": it["pulled"]["reason"], "if_bet": it["pulled"].get("if_bet")} \
                if it["pulled"] else None
            p["result"] = {"result": gr["result"], "actual": gr.get("actual_text"), "units": gr["units"]} if gr else None
            if p["link"] and (it["pulled"] or it["locked_at"] or not odds.safe_link(p["link"])):
                p["link"] = None
            picks.append(p)
        rank = 0
        for p in picks:
            if not p["pulled"] and p["state"] != "locked":
                rank += 1
                p["rank"] = rank
            else:
                p["rank"] = None
        lines_read = sum(len(rows) for pairs in getattr(self, "evals", {}).values() for _, rows in pairs[-1:])
        solo = [r for rows in ((getattr(self, "summ", None) or {}).get("solo_rows") or {}).values() for r in rows]
        passing = sum(1 for r in solo if r["why"] is None)
        try:
            watch.summary(stats.load(), self.cfg)
        except Exception as e:                              # behind the scenes only: never fails the page
            self.steps["watch"] = {"ok": False, "soft": True, "error": common.short_err(e)}
        lu = self.lineup_state.get("teams") or {}
        glist = []
        for g in games:
            glist.append({"id": g["id"], "start": g["start"], "away": teams.show(g["away"]), "home": teams.show(g["home"]),
                          "state": g["state"], "detail": g.get("detail"),
                          "lineups": {k: (lu.get(g[k]) or {}).get("state") or "none" for k in ("away", "home")},
                          "read_at": last_read.get(g["id"]),
                          "picks": sum(1 for p in picks if p["game_id"] == g["id"] and not p["pulled"])})
        banners = []
        keys_n = len(o.get("keys") or [])
        refused = bool(o.get("refused"))
        if o.get("no_keys"):
            banners.append({"level": "stop", "text": "No odds keys yet: Hard Rock prices can't be read, so there are no picks."})
        elif refused:
            banners.append({"level": "stop", "text": "Hard Rock prices are off: the odds keys were refused. New keys are needed."})
        elif o.get("all_used_up"):
            banners.append({"level": "stop", "text": "Odds keys are used up for this month: no new prices until they refill on the 1st."})
        elif plan and plan.get("allowance") is not None and plan["allowance"] < cfg["ops"]["pool_low_allowance"] * cfg["ops"].get("cost_per_read", 1):
            banners.append({"level": "warn", "text": "Odds keys are running low: fewer price checks per game until they refill "
                                                     "on the 1st. More keys would fix it."})
        if self.summ_paused():
            banners.append({"level": "stop", "text": cfg["safety_pause"]["text"] + " " + cfg["safety_pause"]["sub"]})
        if not self.steps.get("schedule", {}).get("ok", True):
            banners.append({"level": "warn", "text": "The schedule source didn't answer at %s. Showing the last known games." %
                                                     common.fmt_time(now)})
        if not self.steps.get("lineups", {}).get("ok", True):
            banners.append({"level": "info", "text": "The starting-lineup source didn't answer at %s. Picks can't reach "
                                                     "Starters confirmed until it does." % common.fmt_time(now)})
        if not self.steps.get("injuries", {}).get("ok", True):
            banners.append({"level": "warn", "text": "The injury list didn't answer at %s. Using the last known one." %
                                                     common.fmt_time(now)})
        nxt = o.get("next_read_at")
        open_picks = [p for p in picks if p["rank"]]
        empty = None
        if not open_picks:
            if not games and not self.steps.get("schedule", {}).get("ok", True):
                empty = {"text": "Today's games haven't loaded yet", "why": "The schedule source didn't answer.", "next": None}
            elif not games:
                empty = {"text": "No NBA games today", "why": "Nothing to check.", "next": None}
            elif all(engine.started(g, now) for g in self.games):
                empty = {"text": "No open picks right now", "why": "Every game has started.", "next": None}
            elif o.get("no_keys") or refused:
                empty = {"text": "No picks yet today", "why": "No Hard Rock prices can be read until odds keys are added.",
                         "next": None}
            elif not lines_read and self.hr_missing_at():
                empty = {"text": "No picks yet today",
                         "why": "Hard Rock hasn't posted NBA player props yet (last checked %s).%s "
                                "We look again before each tip." % (common.fmt_time(self.hr_missing_at()),
                                " Other books have." if any(f.get("others") for f in self.odds_doc.get("fetches", []))
                                else ""), "next": nxt}
            elif not lines_read:
                empty = {"text": "No picks yet today", "why": "No prices read yet. The first close look is 90 minutes before each tip.",
                         "next": nxt}
            else:
                empty = {"text": "No picks yet today",
                         "why": "%d lines read. Pinnacle moved alone on %d, none of them bettable yet." % (lines_read, len(solo))
                         if solo else "%d lines read. Pinnacle hasn't moved alone on any of them yet." % lines_read, "next": nxt}
        tomorrow = datetime.fromisoformat(self.slate) + timedelta(days=1)
        valid_until = common.iso(tomorrow.replace(hour=cfg["ops"]["rollover_hour"], tzinfo=common.ET))
        last_reads = [f["at"] for f in (getattr(self, "odds_doc", None) or {}).get("fetches", [])]
        body = {"slate": self.slate, "valid_until": valid_until, "banners": banners,
                "status": {"odds": {"keys": keys_n, "pool_left": o.get("pool_left"), "low": any(b["level"] == "warn" and
                                    "keys" in b["text"] for b in banners), "refused": refused, "no_keys": bool(o.get("no_keys")),
                                    "days_left": odds.days_to_reset(self.slate), "allowance": plan.get("allowance"), "reads": plan.get("reads")},
                           "next_read_at": nxt, "last_read_at": max(last_reads) if last_reads else None,
                           "last_run": {"ok": all(s.get("ok") or s.get("soft") for s in self.steps.values()), "at": common.iso(now)}},
                "games": glist, "picks": picks, "empty": empty, "counts": {"lines_read": lines_read, "passing": passing,
                                                                           "games": len(games)},
                "safety_paused": self.summ_paused(), "ui": cfg["ui"]}
        old = common.read_json(common.dpath("slate.json"), {}) or {}
        strip = lambda d: {k: v for k, v in d.items() if k not in ("generated_at", "status_at", "status")}
        changed = strip(old) != strip(body) or (old.get("status") or {}).get("odds") != body["status"]["odds"]
        stale = (now - (common.parse_iso(old.get("status_at")) or now - timedelta(days=1))).total_seconds() / 60.0 >= \
            cfg["ops"]["heartbeat_min"]
        if changed or stale:
            body["generated_at"] = common.iso(now) if changed else old.get("generated_at", common.iso(now))
            body["status_at"] = common.iso(now)
            common.write_json(common.dpath("slate.json"), body)
            self.write_status()
        self.slate_doc = body if (changed or stale) else old

    def hr_missing_at(self):
        """Latest read time today when reads came back but none carried Hard Rock (book not posted yet); else None."""
        fs = (getattr(self, "odds_doc", None) or {}).get("fetches", [])
        if not fs or any(f.get("markets") for f in fs):
            return None
        return max(common.parse_iso(f["at"]) for f in fs)

    def summ_paused(self):
        return bool(getattr(self, "summ", {}) and self.summ.get("paused"))

    def write_status(self):
        o = getattr(self, "odds_res", None) or {}
        env = os.environ
        num = lambda k: int(env[k]) if env.get(k, "").isdigit() else None
        st = {"finished_at": common.iso(self.now), "slate": self.slate, "ok": all(s.get("ok") or s.get("soft")
                                                                                   for s in self.steps.values()),
              "steps": self.steps, "keys": o.get("keys"), "pool_left": o.get("pool_left"), "plan": o.get("plan"),
              "spent_today": o.get("spent_today"), "odds_note": o.get("note"), "odds_errors": (o.get("errors") or [])[-5:],
              "unknown_teams": o.get("unknown_teams"), "graded_now": getattr(self, "graded_now", 0),
              "sources": {"espn": dict(espn.SOURCE), "rotowire": dict(rotowire.SOURCE), "odds": dict(odds.SOURCE)},
              "unmatched_rotowire": sorted(set(getattr(getattr(self, "ctx", None), "rw_unmatched", [])))[:40],
              "unmatched": sorted({n for f in (getattr(self, "odds_doc", None) or {}).get("fetches", []) for n in f.get("unmatched", [])})[:40],
              "runner": {"event": env.get("PC_RUNNER_EVENT"), "run_id": env.get("PC_RUNNER_RUN_ID"),
                         "iteration": num("PC_RUNNER_ITERATION"), "chain_link": num("PC_RUNNER_LINK"),
                         "chain_started_at": env.get("PC_RUNNER_CHAIN_STARTED") or None,
                         "run_started_at": env.get("PC_RUNNER_RUN_STARTED") or None}}
        common.write_json(common.dpath("status.json"), st)


def rules_doc(cfg):
    ps, r, c, el, w = cfg["pin_solo"], cfg["reads"], cfg["customer"], cfg["eligibility"], cfg["watch"]["pin_judge"]
    return {"version": cfg["version"], "updated": cfg["updated"], "ui": cfg["ui"], "lines": [
        "Hard Rock (Florida) prices only: player rebounds, points, assists and 3-pointers made, the main line, over or under. "
        "No leg worse than %d." % c["worst_price"],
        "The rule: Pinnacle (the sharpest book) moves its odds on a line by %d+ points of chance between two of our price checks, "
        "while the other books on that same line move less than %d points that way, AND Hard Rock's price is still %d+ points "
        "better than Pinnacle's new price (about 10 cents). We bet the side Pinnacle moved toward, at Hard Rock's price."
        % (round(100 * ps["min_move"]), round(100 * ps["others_max"]), round(100 * ps["min_gap_vs_pin"])),
        "Prices are checked about %d, %d and %d minutes before each tip (plus a morning look). A pick can come from the 90, 45 or "
        "20 minute check. The price shown is frozen and is the one graded." % (r["b_min"], r["c_min"], r["d_min"]),
        "This is a signal, not a price gap: Hard Rock's price is not always better than Pinnacle's new number. It is being proven "
        "on the Record (started 2026-10-28; judged at about 150 bets).",
        "A player listed Out or Doubtful is never picked. Questionable or game-time decision waits until he is cleared or "
        "confirmed starting. Needs %d+ games of history." % el["min_history"],
        "Early = injury news still open. Injury report clear = he and his team's main rotation are cleared. "
        "Starters confirmed = both teams' starting fives are posted.",
        "A pick is pulled if he is ruled out or doubtful, or Hard Rock takes the line down. Pulled picks stay on the Record.",
        "One pick per player per market a night. No cap per game or per night. No parlays.",
        "Graded after the game at the shown price, 1 unit flat. Overtime counts. Did not play = void.",
        "Behind the scenes (Backstage tab, not the Record or Discord): %s, Hard Rock %d%%+ better than Pinnacle's price on the same line."
        % (w["label"], round(100 * w["min_ev"])),
        "New picks stop by themselves if the Record falls to %d units." % cfg["safety_pause"]["units"],
    ]}


def main(argv):
    common.install_scrubbers()
    if "--rebuild-record" in argv:
        cfg = common.load_config()
        print("rebuilt:", record.write_views(cfg))
        return 0
    r = Run(explain="--explain" in argv)
    r.store = stats.load()
    r.step("schedule", r.schedule)
    if not hasattr(r, "games"):
        r.games, r.days, r.games_left_month = [], {}, 0
    r.step("rosters", r.rosters, soft=True)
    if not hasattr(r, "people"):
        r.people = {}
    r.step("injuries", r.injuries, soft=True)
    if not hasattr(r, "inj"):
        r.inj = {}
    r.step("lineups", r.lineups, soft=True)
    if not hasattr(r, "lineup_state"):
        r.lineup_state = {}
    r.step("odds", r.odds_step)
    r.step("engine", r.engine_step)
    if r.explain:
        return 0
    r.step("grade", r.grade)
    r.step("publish", r.publish)
    if "publish" in r.steps and not r.steps["publish"]["ok"]:
        return 1
    sent = notify.notify(getattr(r, "slate_doc", None))
    common.log("run done: %s; %d discord message(s)" % (", ".join("%s %s" % (k, "ok" if v.get("ok") else "FAILED")
                                                              for k, v in r.steps.items()), sent))
    hard = [k for k, v in r.steps.items() if not v.get("ok") and not v.get("soft")]
    return 1 if hard and "engine" in hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
