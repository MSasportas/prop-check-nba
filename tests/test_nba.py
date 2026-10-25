"""End-to-end and unit tests for Prop Check NBA. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import common  # noqa: E402
import engine  # noqa: E402
import lineups  # noqa: E402
import model  # noqa: E402
import names  # noqa: E402
import odds  # noqa: E402
import record  # noqa: E402
import teams  # noqa: E402
from world import World  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
PICK_ID = "2026-10-25:401909861:3945274:rebounds:7.5:under"
HR_GOOD = [("Luka Doncic", 7.5, -135, 105), ("Lauri Markkanen", 6.5, -110, -110)]
MKT = [("Luka Doncic", 7.5, 105, -125), ("Lauri Markkanen", 6.5, -110, -110)]


class TestPrices(unittest.TestCase):
    def test_arithmetic(self):
        self.assertAlmostEqual(odds.break_even(-200), 2 / 3, 6)
        self.assertAlmostEqual(odds.decimal(105), 2.05)
        self.assertEqual(odds.american(1.5), -200)
        self.assertAlmostEqual(odds.ev(0.5, 100), 0.0)
        self.assertAlmostEqual(odds.fair_two_sided(-110, -110), 0.5)

    def test_plan_reads(self):
        self.assertEqual(odds.active_reads(6.7, CFG), {"A", "B", "C", "D"})
        self.assertEqual(odds.active_reads(2.4, CFG), {"C", "B"})
        self.assertEqual(odds.active_reads(0.3, CFG), {"C"})

    def test_due_reads_latest_type(self):
        g = {"id": "1", "start": "2026-10-25T19:00:00-04:00", "away": "LAL", "home": "UTAH"}
        now = common.parse_iso("2026-10-25T18:16:00-04:00")
        d = odds.due_reads(now, [g], {"A", "B", "C", "D"}, {}, {}, CFG)
        self.assertEqual(d[0]["read"], "C")
        done = {"1": [{"read": "C", "at": now, "returned": True}]}
        self.assertEqual(odds.due_reads(now, [g], {"A", "B", "C", "D"}, done, {}, CFG), [])
        late = common.parse_iso("2026-10-25T18:41:00-04:00")
        self.assertEqual(odds.due_reads(late, [g], {"A", "B", "C", "D"}, done, {}, CFG)[0]["read"], "D")
        self.assertEqual(odds.due_reads(common.parse_iso("2026-10-25T18:55:00-04:00"), [g], {"D"}, {}, {}, CFG), [])

    def test_safe_link(self):
        self.assertTrue(odds.safe_link("https://app.hardrock.bet/x?y=1"))
        self.assertIsNone(odds.safe_link("javascript:alert(1)"))
        self.assertIsNone(odds.safe_link('https://x.com/"><script>'))


class TestNamesTeams(unittest.TestCase):
    def test_match(self):
        m = names.Matcher([{"pid": "1", "name": "Luka Dončić", "team": "LAL"},
                           {"pid": "2", "name": "Michael Porter Jr.", "team": "BKN"},
                           {"pid": "3", "name": "Jalen Williams", "team": "OKC"},
                           {"pid": "4", "name": "Jaylin Williams", "team": "OKC"}])
        self.assertEqual(m.find("Luka Doncic")["pid"], "1")
        self.assertEqual(m.find("Michael Porter")["pid"], "2")
        self.assertIsNone(m.find("J. Williams"))          # two fit: never guessed
        self.assertEqual(m.find("Jalen Williams")["pid"], "3")

    def test_teams(self):
        self.assertEqual(teams.code("Los Angeles Clippers"), "LAC")
        self.assertEqual(teams.code("LA Clippers"), "LAC")
        self.assertEqual(teams.code("UTA"), "UTAH")
        self.assertEqual(teams.show("GS"), "GSW")


class TestSources(unittest.TestCase):
    def test_rotowire_parse(self):
        page = open(os.path.join(ROOT, "probe", "rotowire_lineups.html"), encoding="utf-8", errors="replace").read()
        p = lineups.parse(page)
        self.assertEqual(p["LAL"]["state"], "expected")
        self.assertEqual(len(p["LAL"]["starters"]), 5)
        self.assertEqual(p["PHI"]["status"]["Joel Embiid"], "doubtful")
        self.assertEqual(p["NY"]["status"]["Jose Alvarado"], "questionable")

    def test_model_sane(self):
        self.assertAlmostEqual(model.p_over(8.0, 7.5) + model.nb_cdf(7, 8.0, model.PARAMS["disp"]), 1.0, 9)
        self.assertGreater(model.p_over(10.0, 7.5), model.p_over(6.0, 7.5))


class TestRecord(unittest.TestCase):
    def test_grade_one(self):
        it = {"shown": {"pid": "9", "line": 7.5, "side": "under", "price": 105}}
        self.assertEqual(engine.grade_one(it, [{"pid": "9", "dnp": False, "min": 30, "reb": 6}], CFG)[0], "W")
        self.assertEqual(engine.grade_one(it, [{"pid": "9", "dnp": False, "min": 30, "reb": 9}], CFG)[0], "L")
        self.assertEqual(engine.grade_one(it, [{"pid": "9", "dnp": True, "min": None, "reb": None}], CFG)[0], "VOID")
        self.assertEqual(engine.grade_one(it, [], CFG)[0], "VOID")
        self.assertAlmostEqual(engine.grade_one(it, [{"pid": "9", "dnp": False, "min": 30, "reb": 6}], CFG)[2], 1.05)

    def test_guard_prefix(self):
        d = tempfile.mkdtemp()
        old, new = os.path.join(d, "a"), os.path.join(d, "b")
        open(old, "w").write('{"x":1}\n')
        open(new, "w").write('{"x":1}\n{"x":2}\n')
        g = os.path.join(ROOT, "scripts", "guard_record.py")
        self.assertEqual(subprocess.run([sys.executable, g, "--old", old, "--new", new]).returncode, 0)
        open(new, "w").write('{"x":9}\n')
        self.assertNotEqual(subprocess.run([sys.executable, g, "--old", old, "--new", new],
                                           capture_output=True).returncode, 0)


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def tearDown(self):
        self.w.close()

    def test_no_keys(self):
        p = self.w.run("2026-10-25T15:31:00-04:00", env={"ODDS_API_KEYS": ""})
        self.assertEqual(p.returncode, 0, p.stderr)
        s = self.w.read("slate.json")
        self.assertTrue(s["status"]["odds"]["no_keys"])
        self.assertEqual(s["banners"][0]["level"], "stop")
        self.assertEqual(s["picks"], [])

    def test_pick_pull_lock(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", HR_GOOD, MKT)
        self.assertEqual(self.w.run("2026-10-25T15:31:00-04:00").returncode, 0)
        s = self.w.read("slate.json")
        self.assertEqual([p["id"] for p in s["picks"]], [PICK_ID])
        p = s["picks"][0]
        self.assertEqual((p["price"], p["rank"], p["read"]), (105, 1, "B"))
        self.assertTrue(p["link"].startswith("https://"))
        # a second run with the same prices changes nothing in the Record
        n = len(self.w.events())
        self.w.run("2026-10-25T15:41:00-04:00")
        self.assertEqual(len(self.w.events()), n)
        # the 45-minute read: Hard Rock moved to -115, the gap is gone -> pulled, price stays frozen
        self.w.lal_utah("2026-10-25T20:15:00Z", [("Luka Doncic", 7.5, -105, -115), HR_GOOD[1]], MKT)
        self.w.run("2026-10-25T16:16:00-04:00")
        ev = self.w.events()
        self.assertEqual([e["t"] for e in ev], ["shown", "pulled"])
        self.assertIn("-115", ev[1]["reason"])
        s = self.w.read("slate.json")
        self.assertEqual(s["picks"][0]["price"], 105)
        self.assertIsNone(s["picks"][0]["rank"])
        self.assertIsNone(s["picks"][0]["link"])
        rec = self.w.read("record.json")
        self.assertEqual(rec["nights"][0]["entries"][0]["pulled"]["reason"], ev[1]["reason"])

    def test_injury_pull_and_lock(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", HR_GOOD, MKT)
        self.w.run("2026-10-25T15:31:00-04:00")
        page = open(os.path.join(self.w.espn, "rotowire_lineups.html"), encoding="utf-8", errors="replace").read()
        # Doncic gets a Questionable tag: the open pick is pulled at once
        page = page.replace('<a title="Luka Doncic" href="/basketball/player/luka-doncic-4396">Luka Doncic</a>',
                            '<a title="Luka Doncic" href="/basketball/player/luka-doncic-4396">Luka Doncic</a>'
                            '<span class="lineup__inj">Ques</span>', 1)
        open(os.path.join(self.w.espn, "rotowire_lineups.html"), "w").write(page)
        self.w.run("2026-10-25T15:41:00-04:00")
        ev = self.w.events()
        self.assertEqual(ev[-1]["t"], "pulled")
        self.assertEqual(ev[-1]["code"], "status")

    def test_lock_at_tip(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", HR_GOOD, MKT)
        self.w.run("2026-10-25T15:31:00-04:00")
        self.w.run("2026-10-25T17:01:00-04:00")
        ev = self.w.events()
        self.assertEqual(ev[-1]["t"], "locked")
        s = self.w.read("slate.json")
        self.assertEqual(s["picks"][0]["state"], "locked")

    def test_out_player_never_picked(self):
        # Jusuf Nurkic is listed Out on Rotowire in the probe
        self.w.lal_utah("2026-10-25T19:30:00Z", [("Jusuf Nurkic", 9.5, -135, 105)], [("Jusuf Nurkic", 9.5, 105, -125)])
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.w.events(), [])

    def test_too_few_books(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", HR_GOOD, MKT, extra_books=["draftkings", "fanduel", "pinnacle"])
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.w.events(), [])

    def test_no_pinnacle(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", HR_GOOD, MKT, extra_books=["draftkings", "fanduel", "betmgm", "novig", "betonlineag"])
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.w.events(), [])

    def test_price_worse_than_200(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", [("Luka Doncic", 7.5, 150, -210)], [("Luka Doncic", 7.5, 190, -250)])
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.w.events(), [])

    def test_morning_read_never_picks(self):
        self.w.lal_utah("2026-10-25T15:00:00Z", HR_GOOD, MKT)
        self.w.run("2026-10-25T11:01:00-04:00")
        self.assertEqual(self.w.events(), [])
        doc = self.w.read("odds", "2026-10-25.json")
        self.assertEqual({f["read"] for f in doc["fetches"]}, {"A"})

    def test_rules_doc(self):
        self.w.run("2026-10-25T09:31:00-04:00")
        r = self.w.read("rules.json")
        self.assertTrue(any("-200" in l for l in r["lines"]))


if __name__ == "__main__":
    unittest.main()
