"""v2.0 live rule: Pinnacle moves alone (config pin_solo), and the behind-the-scenes Pinnacle price judge (watch.pin_judge)."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import notify  # noqa: E402
from world import World, book  # noqa: E402

OTHERS = ["draftkings", "fanduel", "betmgm", "betonlineag", "novig", "betrivers"]
LUKA = "Luka Doncic"


def write(w, at, hr, pin, others, n_others=6):
    """hr / pin / others: (over, under) for Luka rebounds 7.5."""
    bms = [book("hardrockbet", [(LUKA, 7.5) + hr], at, link=True), book("pinnacle", [(LUKA, 7.5) + pin], at)]
    bms += [book(b, [(LUKA, 7.5) + others], at) for b in OTHERS[:n_others]]
    w.write_odds("odds_lal_utah.json", {"id": "ev401909861", "bookmakers": bms})


class TestPinSolo(unittest.TestCase):
    def setUp(self):
        self.w = World(rule="pin_solo")

    def tearDown(self):
        self.w.close()

    def shown(self):
        return [e for e in self.w.events() if e["t"] == "shown"]

    def test_pinnacle_moves_alone_makes_a_pick(self):
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")                         # B read: nothing to compare yet
        self.assertEqual(self.shown(), [])
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-105, -115))
        self.w.run("2026-10-25T16:16:00-04:00")                         # C read: Pinnacle moved the under alone
        sh = self.shown()
        self.assertEqual(len(sh), 1)
        p = sh[0]["pick"]
        self.assertEqual((p["rule"], p["side"], p["price"], p["read"]), ("pin_solo", "under", -120, "C"))
        self.assertGreater(p["pin_after"], p["pin_before"] + 0.02)
        self.assertIn("Pinnacle moved the under", p["reason"])
        self.assertEqual(p["window"], "90 → 45 min")                    # B read -> C read
        s = self.w.read("slate.json")
        self.assertEqual(s["picks"][0]["rule"], "pin_solo")
        self.assertIn("Pinnacle moved alone", notify.pick_line(dict(s["picks"][0], start=s["picks"][0]["start"])))
        # a later read with Pinnacle back where it was does not pull it (a pick is a signal, frozen)
        write(self.w, "2026-10-25T20:40:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T16:41:00-04:00")
        self.assertFalse([e for e in self.w.events() if e["t"] == "pulled"])

    def test_others_moved_too_no_pick(self):
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (105, -135))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(self.shown(), [])

    def test_others_moved_a_little_still_a_pick(self):
        # v2.1 (Matt): the other books may move up to 2 pts the same way; here ~1.2 pts
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-102, -120))
        self.w.run("2026-10-25T16:16:00-04:00")
        sh = self.shown()
        self.assertEqual(len(sh), 1)
        self.assertGreater(sh[0]["pick"]["others_move"], 0.005)
        self.assertLess(sh[0]["pick"]["others_move"], 0.02)

    def test_too_few_other_books_no_pick(self):
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115), n_others=3)
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-105, -115), n_others=3)
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(self.shown(), [])

    def test_small_move_no_pick(self):
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (-100, -120), (-105, -115))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(self.shown(), [])

    def test_line_removed_pulls(self):
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-105, -115))
        self.w.run("2026-10-25T16:16:00-04:00")
        at = "2026-10-25T20:40:00Z"
        bms = [book("hardrockbet", [("Lauri Markkanen", 6.5, -110, -110)], at), book("pinnacle", [(LUKA, 7.5, 112, -149)], at)]
        self.w.write_odds("odds_lal_utah.json", {"id": "ev401909861", "bookmakers": bms})
        self.w.run("2026-10-25T16:41:00-04:00")
        pulled = [e for e in self.w.events() if e["t"] == "pulled"]
        self.assertEqual([e["code"] for e in pulled], ["line_gone"])

    def test_price_judge_is_behind_the_scenes_only(self):
        # Hard Rock under +105 vs Pinnacle fair under ~55%: +13% vs Pinnacle; no move between reads -> no live pick
        write(self.w, "2026-10-25T19:30:00Z", (-135, 105), (110, -130), (-110, -110))
        self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(self.shown(), [])
        flags = [json.loads(l) for l in open(os.path.join(self.w.data, "watch", "pin_judge", "flags.jsonl"))]
        self.assertEqual([(f["player"], f["side"], f["price"]) for f in flags], [(LUKA, "under", 105)])
        summ = self.w.read("watch", "pin_judge", "summary.json")
        t = summ["total"]
        self.assertEqual(t["w"] + t["l"] + t["push"] + t["void"] + t["pending"], 1)   # Oct 25 is in the seed, so it may grade
        self.assertFalse(os.path.exists(os.path.join(self.w.data, "record", "events.jsonl")) and self.w.events())
        self.w.run("2026-10-25T15:41:00-04:00")                         # same night: flagged once
        self.assertEqual(len(open(os.path.join(self.w.data, "watch", "pin_judge", "flags.jsonl")).readlines()), 1)

    def test_rules_sheet(self):
        self.w.run("2026-10-25T09:31:00-04:00")
        lines = " ".join(self.w.read("rules.json")["lines"])
        self.assertIn("Pinnacle", lines)
        self.assertIn("-200", lines)


if __name__ == "__main__":
    unittest.main()
