"""QA (2026-10-26, v1.2 3-pointers made): ESPN "3PT" parsing, a threes pick end to end (shown, graded from fg3m, Record
bucket), the read plan at 4 credits a read. Run: python -m unittest discover -s tests"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import engine  # noqa: E402
import espn  # noqa: E402
import odds  # noqa: E402
import seed_probe  # noqa: E402
from world import World  # noqa: E402
from test_qa_failures import set_game  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
REB = [("Luka Doncic", 7.5, -135, 105)]
REB_MKT = [("Luka Doncic", 7.5, 105, -125)]
HR3 = {"player_threes": [("Quentin Grimes", 1.5, -135, 105)]}       # under +105 at Hard Rock
MK3 = {"player_threes": [("Quentin Grimes", 1.5, 105, -125)]}       # books: under ~53%
TID = "2026-10-25:401909861:4397014:threes:1.5:under"


def summary(three="1-4", dnp=False, drop_label=False):
    s = json.load(open(os.path.join(ROOT, "probe", "summary_final.json")))
    s["header"]["id"] = "401909861"
    s["header"]["competitions"][0]["date"] = "2026-10-25T21:00Z"
    m = {"CHA": "UTAH", "MIA": "LAL"}
    for c in s["header"]["competitions"][0]["competitors"]:
        c["team"]["abbreviation"] = m[c["team"]["abbreviation"]]
    for p in s["boxscore"]["players"] + s["boxscore"]["teams"]:
        p["team"]["abbreviation"] = m[p["team"]["abbreviation"]]
    blk = next(p for p in s["boxscore"]["players"] if p["team"]["abbreviation"] == "LAL")["statistics"][0]
    a = blk["athletes"][1]
    a["athlete"]["id"], a["athlete"]["displayName"] = "4397014", "Quentin Grimes"
    if dnp:
        a["didNotPlay"], a["stats"] = True, []
    elif three is None:
        a["stats"][blk["labels"].index("3PT")] = None
    else:
        a["stats"][blk["labels"].index("3PT")] = three
    if drop_label:
        for sp in s["boxscore"]["players"]:
            st = sp["statistics"][0]
            i = st["labels"].index("3PT")
            st["labels"] = st["labels"][:i] + st["labels"][i + 1:]
            for at in st["athletes"]:
                if at.get("stats"):
                    at["stats"] = at["stats"][:i] + at["stats"][i + 1:]
    return s


class TestParse3PT(unittest.TestCase):
    def test_made_values(self):
        for f in (espn._made, seed_probe.made):
            self.assertEqual(f("0-1"), 0.0)
            self.assertEqual(f("3-7"), 3.0)
            for bad in ("--", "", None, "-", "x-y"):
                self.assertIsNone(f(bad), (f.__module__, bad))

    def test_box_rows(self):
        for kw, want in ((dict(three="0-1"), 0.0), (dict(three="--"), None), (dict(three=""), None),
                         (dict(three=None), None), (dict(drop_label=True), None)):
            pr, tr = espn.box(summary(**kw))
            g = next(r for r in pr if r["pid"] == "4397014")
            self.assertEqual(g["fg3m"], want, kw)
            self.assertFalse(g["dnp"])
            _, pr2, _ = seed_probe.box(summary(**kw))
            self.assertEqual(next(r for r in pr2 if r["pid"] == "4397014")["fg3m"], want, kw)
        pr, tr = espn.box(summary(dnp=True))
        g = next(r for r in pr if r["pid"] == "4397014")
        self.assertTrue(g["dnp"])
        self.assertIsNone(g["fg3m"])
        self.assertTrue(all(t["fg3m"] is not None for t in tr))
        it = {"shown": {"pid": "4397014", "line": 1.5, "side": "under", "price": 105, "market": "threes"}}
        self.assertEqual(engine.grade_one(it, pr, CFG)[0], "VOID")
        # played, but 3PT unreadable: wait, never a 0
        pr, _ = espn.box(summary(three="--"))
        self.assertEqual(engine.grade_one(it, pr, CFG)[0], None)


class TestThreesEndToEnd(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.write_espn("scoreboard_20261026.json", {"events": []})

    def tearDown(self):
        self.w.close()

    def _show(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=HR3, others_extra=MK3)
        self.assertEqual(self.w.run("2026-10-25T15:31:00-04:00").returncode, 0)
        ids = [e["id"] for e in self.w.events() if e["t"] == "shown"]
        self.assertIn(TID, ids)
        pk = next(p for p in self.w.read("slate.json")["picks"] if p["id"] == TID)
        self.assertEqual((pk["bet"], pk["price"], pk["line"]), ("Under 1.5 threes", 105, 1.5))

    def _grade(self, **kw):
        set_game(self.w, "20261025", "401909861", state="post", completed=True, name="STATUS_FINAL")
        self.w.write_espn("summary_401909861.json", summary(**kw))
        self.assertEqual(self.w.run("2026-10-26T00:01:00-04:00").returncode, 0)
        return {e["id"]: (e["result"], e["actual_text"]) for e in self.w.events() if e["t"] == "graded"}

    def test_shown_graded_bucket(self):
        self._show()
        g = self._grade(three="1-4")
        self.assertEqual(g[TID], ("W", "1 three"))
        rows = self.w.read("record.json")["summary"]["rows"]
        b = next(r for r in rows if r["key"] == "threes")
        self.assertEqual((b["label"], b["w"], b["l"]), ("3-pointers made", 1, 0))

    def test_loss_from_fg3m(self):
        self._show()
        self.assertEqual(self._grade(three="2-6")[TID], ("L", "2 threes"))

    def test_dnp_void(self):
        self._show()
        self.assertEqual(self._grade(dnp=True)[TID][0], "VOID")

    def test_unreadable_waits(self):
        self._show()
        self.assertNotIn(TID, self._grade(three="--"))


class TestPlan4Credits(unittest.TestCase):
    def test_plans(self):
        self.assertEqual(CFG["ops"]["cost_per_read"], 4)
        self.assertEqual(odds.make_plan(3000, 225, 7, CFG)["reads"], ["B", "C", "D"])
        self.assertEqual(odds.make_plan(1500, 225, 7, CFG)["reads"], ["C"])
        rest = odds.make_plan(2800, 36, 7, CFG)                        # rest of October
        self.assertEqual(rest["reads"], ["A", "B", "C", "D"])
        self.assertGreaterEqual(rest["budget_today"], 7 * 4 * 4)
        # a full month at 3 reads never overspends 6 keys
        self.assertLessEqual(225 * 3 * 4, 3000)


if __name__ == "__main__":
    unittest.main()
