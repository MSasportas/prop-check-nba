"""QA (2026-10-25, v1.1 points + assists): cross-market isolation, grading by the market's stat, the read plan at
3 credits a read, customer facts per market. Run: python -m unittest discover -s tests"""
import gzip
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import engine  # noqa: E402
import odds  # noqa: E402
from world import World  # noqa: E402
from test_qa_failures import set_game  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
REB = [("Luka Doncic", 7.5, -135, 105)]
REB_MKT = [("Luka Doncic", 7.5, 105, -125)]
# assists on the SAME line number as rebounds (7.5): ids and pull matching must still keep them apart
HR_X = {"player_points": [("Luka Doncic", 36.5, -135, 105)], "player_assists": [("Luka Doncic", 7.5, -135, 105)]}
MK_X = {"player_points": [("Luka Doncic", 36.5, 105, -125)], "player_assists": [("Luka Doncic", 7.5, 105, -125)]}
ID = "2026-10-25:401909861:3945274:%s:%s:under"


def final_summary(w, reb=6, pts=40, ast=9, drop=()):
    s = json.load(open(os.path.join(ROOT, "probe", "summary_final.json")))
    s["header"]["id"] = "401909861"
    s["header"]["competitions"][0]["date"] = "2026-10-25T21:00Z"
    m = {"CHA": "UTAH", "MIA": "LAL"}
    for c in s["header"]["competitions"][0]["competitors"]:
        c["team"]["abbreviation"] = m[c["team"]["abbreviation"]]
    for p in s["boxscore"]["players"] + s["boxscore"]["teams"]:
        p["team"]["abbreviation"] = m[p["team"]["abbreviation"]]
    blk = next(p for p in s["boxscore"]["players"] if p["team"]["abbreviation"] == "LAL")["statistics"][0]
    a = blk["athletes"][0]
    a["athlete"]["id"], a["athlete"]["displayName"] = "3945274", "Luka Doncic"
    for lab, v in (("REB", reb), ("PTS", pts), ("AST", ast)):
        a["stats"][blk["labels"].index(lab)] = str(v)
    for lab in drop:                                       # an old-format box score without that column
        for sp in s["boxscore"]["players"]:
            st = sp["statistics"][0]
            i = st["labels"].index(lab)
            st["labels"] = st["labels"][:i] + st["labels"][i + 1:]
            for at in st["athletes"]:
                if at.get("stats"):
                    at["stats"] = at["stats"][:i] + at["stats"][i + 1:]
    w.write_espn("summary_401909861.json", s)


class TestQAV11(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.write_espn("scoreboard_20261026.json", {"events": []})

    def tearDown(self):
        self.w.close()

    def shown(self):
        return sorted(e["id"] for e in self.w.events() if e["t"] == "shown")

    def test_three_markets_same_line_number_kept_apart(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=HR_X, others_extra=MK_X)
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.shown(), sorted([ID % ("assists", "7.5"), ID % ("points", "36.5"), ID % ("rebounds", "7.5")]))
        # C read: only the REBOUNDS price moves (gap gone). Points and assists (assists on the same 7.5) must stay.
        self.w.lal_utah("2026-10-25T20:15:00Z", [("Luka Doncic", 7.5, -105, -115)], REB_MKT, hr_extra=HR_X, others_extra=MK_X)
        self.w.run("2026-10-25T16:16:00-04:00")
        pulled = [e["id"] for e in self.w.events() if e["t"] == "pulled"]
        self.assertEqual(pulled, [ID % ("rebounds", "7.5")])

    def test_hr_posts_points_but_books_dont(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=HR_X, others_extra=MK_X)
        self.w.run("2026-10-25T15:31:00-04:00")
        self.w.lal_utah("2026-10-25T20:15:00Z", REB, REB_MKT, hr_extra=HR_X,
                        others_extra={"player_assists": MK_X["player_assists"]})
        self.w.run("2026-10-25T16:16:00-04:00")
        pulled = {e["id"]: e["code"] for e in self.w.events() if e["t"] == "pulled"}
        self.assertEqual(pulled, {ID % ("points", "36.5"): "books_low"})

    def test_customer_facts_per_market(self):
        hr = {"player_points": [("Luka Doncic", 36.5, 150, -210)],             # under at -210: never
              "player_assists": [("Luka Doncic", 8.5, -110, -110), ("Luka Doncic", 10.5, 230, -320)]}   # alt ladder
        mk = {"player_points": [("Luka Doncic", 36.5, 190, -250)],
              "player_assists": [("Luka Doncic", 8.5, -110, -110), ("Luka Doncic", 10.5, 400, -600)]}
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=hr, others_extra=mk)
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.shown(), [ID % ("rebounds", "7.5")])
        s = self.w.read("slate.json")
        self.assertTrue(all(p["price"] >= -200 for p in s["picks"]))
        self.assertFalse(s.get("parlays"))

    def test_grade_each_market_by_its_stat_and_box_rebuilt(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=HR_X, others_extra=MK_X)
        self.w.run("2026-10-25T15:31:00-04:00")
        set_game(self.w, "20261025", "401909861", state="post", completed=True, name="STATUS_FINAL")
        final_summary(self.w, reb=6, pts=40, ast=9)
        self.assertEqual(self.w.run("2026-10-26T00:01:00-04:00").returncode, 0)
        g = {e["id"]: (e["result"], e["actual_text"]) for e in self.w.events() if e["t"] == "graded"}
        self.assertEqual(g, {ID % ("rebounds", "7.5"): ("W", "6 rebounds"), ID % ("points", "36.5"): ("L", "40 points"),
                             ID % ("assists", "7.5"): ("L", "9 assists")})
        live = os.path.join(self.w.data, "state", "box", "players_2026-27.json.gz")
        if os.path.exists(live):
            rows = json.load(gzip.open(live, "rt"))
            d = next(r for r in rows if r["pid"] == "3945274" and r["game"] == "401909861")
            self.assertEqual((d["reb"], d["pts"], d["ast"]), (6, 40, 9))
        else:   # since the 2026-10-26 re-seed this game is in data/seed, so the live cache does not store it again
            seed = json.load(gzip.open(os.path.join(ROOT, "data", "seed", "teams_2026-27.json.gz"), "rt"))
            self.assertTrue(any(r["game"] == "401909861" for r in seed))
        rec = self.w.read("record.json")
        self.assertIn("Points", json.dumps(rec))
        self.assertIn("Assists", json.dumps(rec))

    def test_box_without_ast_waits_never_guesses(self):
        self.w.lal_utah("2026-10-25T19:30:00Z", REB, REB_MKT, hr_extra=HR_X, others_extra=MK_X)
        self.w.run("2026-10-25T15:31:00-04:00")
        set_game(self.w, "20261025", "401909861", state="post", completed=True, name="STATUS_FINAL")
        final_summary(self.w, drop=("AST",))
        p = self.w.run("2026-10-26T00:01:00-04:00")
        self.assertEqual(p.returncode, 0, p.stderr[-800:])
        graded = {e["id"] for e in self.w.events() if e["t"] == "graded"}
        self.assertNotIn(ID % ("assists", "7.5"), graded)
        self.assertIn(ID % ("rebounds", "7.5"), graded)
        st = self.w.read("status.json")
        self.assertTrue(all(v.get("ok", True) for k, v in (st.get("steps") or {}).items() if k == "grade"), st.get("steps"))

    def test_plan_remade_when_cost_and_keys_change(self):
        os.makedirs(os.path.join(self.w.data, "state"), exist_ok=True)
        old = {"date": "2026-10-25", "plan": {"allowance": 28.846, "reads": ["A", "B", "C", "D"], "budget_today": 201,
                                               "pool_at_plan": 1500, "games_left": 52, "games_today": 7, "key_count": 3,
                                               "made_at": "2026-10-25T19:50:14-04:00"},
               "events": {}, "events_at": None, "unknown_teams": [], "key_count": 3}
        json.dump(old, open(os.path.join(self.w.data, "state", "odds_day.json"), "w"))
        self.w.write_odds("pool.json", {"keys": [60, 60, 60]})          # same 3 keys, cost now 4 (v1.2): must re-plan
        self.w.run("2026-10-25T15:31:00-04:00")
        plan = self.w.read("state", "odds_day.json")["plan"]
        self.assertEqual((plan["key_count"], plan["cost_per_read"]), (3, 4))
        self.assertEqual(plan["reads"], sorted(odds.active_reads(plan["allowance"], CFG)))
        self.w.write_odds("pool.json", {"keys": [60] * 6})              # 3 more keys mid-day
        self.w.run("2026-10-25T15:41:00-04:00")
        plan2 = self.w.read("state", "odds_day.json")["plan"]
        self.assertEqual(plan2["key_count"], 6)
        self.assertGreater(plan2["allowance"], plan["allowance"])


class TestQAV11Plan(unittest.TestCase):
    def test_month_plans(self):
        p6 = odds.make_plan(3000, 225, 7, CFG)
        self.assertEqual(p6["reads"], ["B", "C", "D"])                  # v1.2: 4 markets, the morning A read drops
        self.assertGreaterEqual(p6["budget_today"], 7 * 3 * 4)
        p3 = odds.make_plan(1500, 225, 7, CFG)
        self.assertEqual(p3["reads"], ["C"])
        self.assertGreaterEqual(p3["budget_today"], 7 * 1 * 4)

    def test_grade_one_uses_market_stat(self):
        row = [{"pid": "9", "dnp": False, "min": 30, "reb": 3, "pts": 30, "ast": 12}]
        for mk, line, want in (("rebounds", 7.5, "W"), ("points", 28.5, "L"), ("assists", 9.5, "L")):
            it = {"shown": {"pid": "9", "line": line, "side": "under", "price": 105, "market": mk}}
            self.assertEqual(engine.grade_one(it, row, CFG)[0], want, mk)
        it = {"shown": {"pid": "9", "line": 9.5, "side": "under", "price": 105, "market": "assists"}}
        self.assertIsNone(engine.grade_one(it, [{"pid": "9", "dnp": False, "min": 30, "reb": 3}], CFG)[0])


if __name__ == "__main__":
    unittest.main()
