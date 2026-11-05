"""2026-11-04 page redesign (NHL's Ballpark page brought to NBA): display-only data. Live tab (scripts/live.py -> data/live.json),
the espn.summary in-run memo, data/headshots.json, slate pulled.code, Record cuts/days, config/lab.json.
Run: python -m unittest discover -s tests"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import common  # noqa: E402
import espn  # noqa: E402
import live  # noqa: E402
import record  # noqa: E402
import run  # noqa: E402
from world import World  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
SLATE = "2026-11-04"
G1, G2, G3 = "401909922", "401909923", "401909924"
KEYS = ["minutes", "points", "fieldGoalsMade-fieldGoalsAttempted", "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "freeThrowsMade-freeThrowsAttempted", "rebounds", "assists", "turnovers", "steals", "blocks", "offensiveRebounds",
        "defensiveRebounds", "fouls", "plusMinus"]
NAMES = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]


def summary(state="in", period=2, clock="11:17", detail="11:17 - 2nd Quarter", name="STATUS_IN_PROGRESS", score=("23", "19"),
            athletes=None):
    """Shaped exactly like ESPN's in-progress summary (event 401909922, 2026-11-04)."""
    ath = athletes if athletes is not None else [
        {"active": True, "athlete": {"id": "1966", "displayName": "A. Player", "headshot": {"href": "x"}}, "starter": True,
         "didNotPlay": False, "reason": None, "ejected": False, "stats": ["9", "4", "1-2", "2-3", "2-2", "6", "2", "0", "0", "0", "1", "5", "1", "+3"]},
        {"active": False, "athlete": {"id": "1967", "displayName": "B. Bench"}, "starter": False, "didNotPlay": True,
         "reason": "INJURY", "ejected": False, "stats": []}]
    return {"header": {"id": G1, "competitions": [{
        "date": "2026-11-05T00:00Z",
        "status": {"displayClock": clock, "period": period, "displayPeriod": "2nd",
                   "type": {"state": state, "name": name, "completed": state == "post", "detail": detail, "shortDetail": detail}},
        "competitors": [{"homeAway": "home", "score": score[1], "team": {"abbreviation": "DET"}},
                        {"homeAway": "away", "score": score[0], "team": {"abbreviation": "PHI"}}]}]},
        "boxscore": {"players": [{"team": {"abbreviation": "PHI"}, "statistics": [{"names": NAMES, "keys": KEYS, "labels": NAMES,
                                                                                   "descriptions": NAMES, "athletes": ath, "totals": []}]},
                                 {"team": {"abbreviation": "DET"}, "statistics": [{"names": NAMES, "keys": KEYS, "labels": NAMES,
                                                                                   "descriptions": NAMES, "athletes": [], "totals": []}]}]}}


def shown(i, game, pid, market="points", line=3.5, side="over"):
    return {"t": "shown", "kind": "single", "id": i, "at": "2026-11-04T17:31:00-05:00", "slate": SLATE,
            "pick": {"rule": "pin_solo", "game_id": game, "player": "A. Player", "pid": pid, "team": "PHI", "opp": "DET", "home": False,
                     "start": "2026-11-04T19:00:00-05:00", "market": market, "line": line, "side": side, "bet": "x", "price": -120,
                     "state": "clear", "ev_vs_pin": 0.01}}


GAMES = [{"id": G1, "away": "PHI", "home": "DET", "start": "2026-11-04T19:00:00-05:00", "state": "in", "detail": "11:17 - 2nd",
          "score": {"PHI": "23", "DET": "19"}},
         {"id": G2, "away": "ATL", "home": "WSH", "start": "2026-11-04T19:00:00-05:00", "state": "in", "detail": "Q1",
          "score": {"ATL": "10", "WSH": "8"}},
         {"id": G3, "away": "BOS", "home": "NY", "start": "2026-11-04T22:00:00-05:00", "state": "pre", "detail": "10:00 PM"}]


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pcnba_rd_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.espn_dir = os.path.join(self.tmp, "espn")
        os.makedirs(self.espn_dir)
        for k, v in (("PC_DATA_DIR", os.path.join(self.tmp, "data")), ("PC_ESPN_FIXTURE_DIR", self.espn_dir)):
            old = os.environ.get(k)
            os.environ[k] = v
            self.addCleanup(lambda k=k, old=old: os.environ.__setitem__(k, old) if old is not None else os.environ.pop(k, None))
        espn.clear_cache()
        self.addCleanup(espn.clear_cache)
        self.now = common.parse_iso("2026-11-04T19:45:00-05:00")

    def put(self, gid, doc):
        with open(os.path.join(self.espn_dir, "summary_%s.json" % gid), "w") as f:
            json.dump(doc, f)


class LiveTab(Env):
    def setUp(self):
        super().setUp()
        self.ev = [shown("a", G1, "1966", "points", 3.5, "over"), shown("b", G1, "1966", "threes", 1.5, "under"),
                   shown("c", G1, "1966", "rebounds", 7.5, "over"), shown("d", G1, "1967", "assists", 2.5, "over"),
                   shown("e", G3, "2000")]

    def test_field_mapping_from_a_real_shaped_summary(self):
        self.put(G1, summary())
        self.assertIsNotNone(espn.summary(G1))                         # the grade step's read
        note = live.step(self.now, SLATE, GAMES, self.ev)
        self.assertIn("1 game", note)
        doc = common.read_json(live.path())
        self.assertEqual(doc["slate_date"], SLATE)
        self.assertEqual(len(doc["games"]), 1)                         # G2 has no pick, G3 has not started
        g = doc["games"][0]
        self.assertEqual((g["game_id"], g["state"], g["period"], g["clock"], g["detail"], g["in_break"]),
                         (G1, "in", 2, "11:17", "11:17 - 2nd Quarter", False))
        self.assertEqual((g["away"], g["home"]), ({"abbrev": "PHI", "score": 23}, {"abbrev": "DET", "score": 19}))
        self.assertEqual(g["updated_at"], common.iso(self.now))
        p = doc["picks"]
        # points 4 > 3.5: an over is decided (HIT) mid-game; threes 2 (made of "2-3") > 1.5: an under is LOST mid-game
        self.assertEqual((p["a"]["stat"], p["b"]["stat"], p["c"]["stat"]), (4, 2, 6))
        self.assertTrue(p["a"]["stat"] > 3.5 and p["b"]["stat"] > 1.5)
        self.assertEqual((p["d"]["stat"], p["d"]["dnp"]), (None, True))
        self.assertNotIn("e", p)
        self.assertEqual(live.step(self.now, SLATE, GAMES, self.ev), "skipped: no change")

    def test_halftime_and_end_of_quarter_are_breaks(self):
        self.assertTrue(espn.game_state(summary(clock="0.0", detail="Halftime", name="STATUS_HALFTIME"))["in_break"])
        self.assertTrue(espn.game_state(summary(clock="0.0", detail="End of 3rd Quarter", name="STATUS_END_PERIOD", period=3))["in_break"])
        ot = espn.game_state(summary(period=5, clock="2:31", detail="2:31 - OT"))
        self.assertEqual((ot["period"], ot["in_break"]), (5, False))

    def test_no_call_of_its_own_and_nothing_before_tip(self):
        calls = []
        real = espn._get
        espn._get = lambda *a, **k: calls.append(a)
        self.addCleanup(setattr, espn, "_get", real)
        early = common.parse_iso("2026-11-04T18:00:00-05:00")
        self.assertTrue(live.step(early, SLATE, [dict(g, state="pre") for g in GAMES], self.ev).startswith("skipped"))
        self.assertIsNone(common.read_json(live.path()))
        live.step(self.now, SLATE, GAMES, self.ev)                     # started, no summary read this run: scoreboard line
        self.assertEqual(calls, [])
        g = common.read_json(live.path())["games"][0]
        self.assertEqual((g["state"], g["updated_at"], g["away"]["score"]), ("in", None, 23))

    def test_a_game_not_read_keeps_its_last_entry_and_graded_takes_the_record(self):
        self.put(G1, summary(state="post", period=4, clock="0.0", detail="Final", name="STATUS_FINAL", score=("104", "111")))
        espn.summary(G1)
        live.step(self.now, SLATE, GAMES, self.ev)
        espn.clear_cache()                                             # next run: grade no longer reads this game
        ev = self.ev + [{"t": "graded", "id": "a", "at": "2026-11-04T22:30:00-05:00", "result": "W", "actual": None,
                         "actual_text": "5 points", "price": -120, "units": 0.83},
                        {"t": "graded", "id": "d", "at": "2026-11-04T22:30:00-05:00", "result": "VOID", "actual": None,
                         "actual_text": "did not play", "price": -120, "units": 0.0}]
        later = common.parse_iso("2026-11-04T22:40:00-05:00")
        live.step(later, SLATE, GAMES, ev)
        doc = common.read_json(live.path())
        g = doc["games"][0]
        self.assertEqual((g["state"], g["home"]["score"], g["updated_at"]), ("post", 111, common.iso(self.now)))
        self.assertEqual((doc["picks"]["a"]["stat"], doc["picks"]["b"]["stat"], doc["picks"]["d"]["dnp"]), (5, 2, True))

    def test_broken_summary_never_fails(self):
        self.put(G1, {"header": {"competitions": [{}]}})
        espn.summary(G1)
        self.assertIsInstance(live.step(self.now, SLATE, GAMES, self.ev), str)

    def test_soft_step_after_grade_never_fails_the_run(self):
        src = open(os.path.join(ROOT, "scripts", "run.py")).read()
        main = src[src.index("def main("):]
        self.assertLess(main.index('r.step("grade"'), main.index('r.step("live", r.live_step, soft=True)'))
        self.assertLess(main.index('r.step("live"'), main.index('r.step("publish"'))
        r = run.Run.__new__(run.Run)
        r.steps, r.errors = {}, []
        real = live.step
        live.step = lambda *a, **k: 1 / 0
        self.addCleanup(setattr, live, "step", real)
        r.now, r.slate, r.games = self.now, SLATE, GAMES
        r.step("live", r.live_step, soft=True)
        self.assertEqual((r.steps["live"]["ok"], r.steps["live"]["soft"]), (False, True))
        hard = [k for k, v in r.steps.items() if not v.get("ok") and not v.get("soft")]
        self.assertEqual(hard, [])


class SummaryCache(Env):
    def test_one_read_per_game_per_run(self):
        self.put(G1, summary())
        n = espn.SOURCE["ok"]
        a = espn.summary(G1)
        b = espn.summary(int(G1))
        self.assertIs(a, b)
        self.assertEqual(espn.SOURCE["ok"] - n, 1)
        self.assertIs(espn.summary_cached(G1), a)
        self.assertIsNone(espn.summary_cached(G2))
        self.assertIsNone(espn.summary(G2))                            # a miss is not cached: the next call tries again
        self.put(G2, summary())
        self.assertIsNotNone(espn.summary(G2))


class Headshots(Env):
    def test_roster_keeps_espn_link_and_merge_keeps_old(self):
        shutil.copy(os.path.join(ROOT, "probe", "roster_bos.json"), os.path.join(self.espn_dir, "roster_BOS.json"))
        r = espn.roster("BOS")
        self.assertTrue(r)
        p0 = r[0]
        self.assertEqual(p0["headshot"], "https://a.espncdn.com/i/headshots/nba/players/full/%s.png" % p0["pid"])
        os.makedirs(common.dpath())
        common.write_json(common.dpath("headshots.json"), {"999": "https://a.espncdn.com/i/headshots/nba/players/full/999.png"})
        run.save_headshots(r + [{"pid": "1", "headshot": "https://evil.example/1.png"}, {"pid": "2", "headshot": None}])
        hs = common.read_json(common.dpath("headshots.json"))
        self.assertIn("999", hs)                                       # old entries kept
        self.assertEqual(hs[p0["pid"]], p0["headshot"])
        self.assertNotIn("1", hs)
        self.assertNotIn("2", hs)
        self.assertTrue(all(espn.HEADSHOT_RE.match(u) for u in hs.values()))

    def test_written_by_the_run(self):
        w = World(rule="pin_solo")
        self.addCleanup(w.close)
        shutil.copy(os.path.join(ROOT, "probe", "roster_bos.json"), os.path.join(w.espn, "roster_LAL.json"))   # a team playing that day
        self.assertEqual(w.run("2026-10-25T15:31:00-04:00").returncode, 0)
        hs = w.read("headshots.json")
        self.assertTrue(hs)
        self.assertTrue(all(espn.HEADSHOT_RE.match(u) for u in hs.values()))


class PulledCode(unittest.TestCase):
    def test_out_vs_status_vs_line_gone(self):
        at = "2026-11-04T18:00:00-05:00"
        v = run.pulled_view({"at": at, "reason": "Now listed out", "code": "status", "if_bet": "x"})
        self.assertEqual((v["code"], v["status"], v["reason"]), ("out", "out", "Now listed out"))
        v = run.pulled_view({"at": at, "reason": "Now listed questionable", "code": "status", "if_bet": "x"})
        self.assertEqual((v["code"], v["status"]), ("status", "questionable"))
        v = run.pulled_view({"at": at, "reason": "Now listed doubtful", "code": "status", "if_bet": "x"})
        self.assertEqual(v["code"], "status")
        v = run.pulled_view({"at": at, "reason": "Hard Rock took the line down", "code": "line_gone", "if_bet": "y"})
        self.assertEqual((v["code"], v["status"], v["if_bet"]), ("line_gone", None, "y"))
        self.assertIsNone(run.pulled_view(None))

    def test_slate_carries_the_code_and_the_record_keeps_the_event(self):
        w = World()
        self.addCleanup(w.close)
        w.lal_utah("2026-10-25T19:30:00Z", [("Luka Doncic", 7.5, -135, 105), ("Lauri Markkanen", 6.5, -110, -110)],
                   [("Luka Doncic", 7.5, 105, -125), ("Lauri Markkanen", 6.5, -110, -110)])
        w.run("2026-10-25T15:31:00-04:00")
        page = open(os.path.join(w.espn, "rotowire_lineups.html"), encoding="utf-8", errors="replace").read()
        page = page.replace('<a title="Luka Doncic" href="/basketball/player/luka-doncic-4396">Luka Doncic</a>',
                            '<a title="Luka Doncic" href="/basketball/player/luka-doncic-4396">Luka Doncic</a>'
                            '<span class="lineup__inj">Out</span>', 1)
        open(os.path.join(w.espn, "rotowire_lineups.html"), "w").write(page)
        w.run("2026-10-25T15:41:00-04:00")
        ev = [e for e in w.events() if e["t"] == "pulled"]
        self.assertEqual([(e["code"], e["reason"]) for e in ev], [("status", "Now listed out")])   # Record event as engine wrote it
        p = w.read("slate.json")["picks"][0]
        self.assertEqual(p["pulled"]["code"], "out")
        self.assertTrue(p["added_at"])


class RecordCuts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pcnba_rc_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(os.path.join(ROOT, "data", "replay"), os.path.join(self.tmp, "replay"))
        old = os.environ.get("PC_DATA_DIR")
        os.environ["PC_DATA_DIR"] = self.tmp
        self.addCleanup(lambda: os.environ.__setitem__("PC_DATA_DIR", old) if old is not None else os.environ.pop("PC_DATA_DIR", None))

    def events(self):
        raw = open(os.path.join(ROOT, "data", "record", "events.jsonl"), "rb").read()
        return record.parse(raw), raw

    def test_existing_views_unchanged_and_new_keys_count_the_headline(self):
        ev, raw = self.events()
        before = hashlib.sha256(raw).hexdigest()
        rec, months = record.build_views(ev, CFG)
        cur = json.load(open(os.path.join(ROOT, "data", "record.json")))
        for k in cur:
            if k != "summary":
                self.assertEqual(rec[k], cur[k], k)
        for k in cur["summary"]:
            self.assertEqual(rec["summary"][k], cur["summary"][k], k)  # headline and rows: same values as before
        for m, doc in months.items():
            self.assertEqual(doc, json.load(open(os.path.join(ROOT, "data", "record", "%s.json" % m))))
        hd = rec["summary"]["headline"]
        days = rec["summary"]["days"]
        self.assertEqual((sum(d["w"] for d in days), sum(d["l"] for d in days)), (hd["w"], hd["l"]))
        self.assertAlmostEqual(sum(d["units"] for d in days), hd["units"], delta=0.05)
        self.assertEqual(sum(d["void"] for d in days), hd["void"])
        self.assertTrue(any(d["date"] < "2026-11-01" for d in days) and any(d["date"] >= "2026-11-01" for d in days))
        for c in rec["summary"]["cuts"]:
            n = sum(r["w"] + r["l"] for r in c["rows"])
            if c["key"] in ("market", "edge", "price"):
                self.assertEqual(n, hd["n"], c["key"])
            else:
                self.assertLessEqual(n, hd["n"])                       # replay bets have no settled level
        self.assertEqual([c["key"] for c in rec["summary"]["cuts"]], ["market", "edge", "settled", "price"])
        self.assertEqual(hashlib.sha256(open(os.path.join(ROOT, "data", "record", "events.jsonl"), "rb").read()).hexdigest(), before)

    def test_bands(self):
        f = lambda **k: dict({"market": "points", "edge": 0.01, "settled": "clear", "price": -120}, **k)
        e = lambda r: {"result": r, "units": 1.0 if r == "W" else -1.0, "price": -120}
        rows = [(e("W"), f(edge=0.0)), (e("L"), f(edge=0.03, price=110)), (e("W"), f(edge=0.07, price=-180, settled="early"))]
        cuts = {c["key"]: c for c in record.cuts(rows, lambda x: 0.55, CFG)}
        self.assertEqual([(r["key"], r["n"]) for r in cuts["edge"]["rows"]], [("e0", 1), ("e2", 1), ("e5", 1)])
        self.assertEqual([r["key"] for r in cuts["price"]["rows"]], ["plus", "fav", "fav_big"])
        self.assertEqual([r["key"] for r in cuts["settled"]["rows"]], ["early", "clear"])


class LabConfig(unittest.TestCase):
    def test_entries(self):
        doc = json.load(open(os.path.join(ROOT, "config", "lab.json")))
        self.assertEqual([t["id"] for t in doc["tests"]], ["pin_judge"])
        for t in doc["tests"]:
            for k in ("id", "title", "rule", "summary", "need", "gate"):
                self.assertIn(k, t)
            self.assertNotIn("..", t["summary"])
            sm = json.load(open(os.path.join(ROOT, "data", t["summary"])))
            self.assertIn(t.get("stats", "total"), sm)
            for k in ("w", "l", "units", "pending"):
                self.assertIn(k, sm[t.get("stats", "total")])
        self.assertEqual(doc["tests"][0]["need"], 150)


class Page(unittest.TestCase):
    """The page itself: Hard Rock only, bundled fonts, light Ballpark theme, six rail tabs."""

    def setUp(self):
        self.html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

    def test_shape(self):
        h = self.html
        self.assertNotIn("fonts.googleapis", h)
        self.assertNotIn("prefers-color-scheme", h)
        self.assertNotIn("sportsbook.draftkings.com", h)
        self.assertIn("<title>Prop Check NBA</title>", h)
        self.assertIn('content="#DCE9F7"', h)
        for c in ("#DCE9F7", "#F4F8FD", "#0B1F3A", "#4A6181", "#C8102E", "#1E5AA8", "#B9CDE6", "#FBE3E7", "#A00D25"):
            self.assertIn(c, h)
        for v in ("'picks', 'Picks'", "'live', 'Live'", "'games', 'Games'", "'record', 'Record'", "'lab', 'Lab'", "'info', 'Info'"):
            self.assertIn(v, h)
        self.assertIn("1-800-GAMBLER", h)
        for f in ("graduate-400", "ibm-plex-sans-400", "ibm-plex-sans-500", "ibm-plex-sans-600", "ibm-plex-sans-700",
                  "ibm-plex-mono-500", "ibm-plex-mono-600"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, "fonts", f + ".woff2")), f)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "fonts", "README.txt")))

    def test_every_fixture_has_a_slate(self):
        fx = os.path.join(ROOT, "fixtures")
        for d in os.listdir(fx):
            if os.path.isdir(os.path.join(fx, d)):
                s = json.load(open(os.path.join(fx, d, "slate.json")))
                self.assertIn("picks", s, d)


if __name__ == "__main__":
    unittest.main()
