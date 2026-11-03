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


def write(w, at, hr, pin, others, n_others=6, dk=None):
    """hr / pin / others: (over, under) for Luka rebounds 7.5. dk: DraftKings' prices (default: same as the other books)."""
    bms = [book("hardrockbet", [(LUKA, 7.5) + hr], at, link=True), book("pinnacle", [(LUKA, 7.5) + pin], at)]
    bms += [book(b, [(LUKA, 7.5) + (dk if (b == "draftkings" and dk) else others)], at, link=(b == "draftkings"))
            for b in OTHERS[:n_others]]
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
        # v2.5b (Matt): Hard Rock -120 and DraftKings -115 each beat Pinnacle's fair price: two independent picks, each at its own price
        self.assertEqual(sorted((e["pick"]["book"], e["pick"]["price"]) for e in sh), [("draftkings", -115), ("hardrock", -120)])
        self.assertEqual(sorted(e["id"].endswith(":draftkings") for e in sh), [False, True])
        p = [e["pick"] for e in sh if e["pick"]["book"] == "hardrock"][0]
        self.assertEqual((p["rule"], p["side"], p["price"], p["read"]), ("pin_solo", "under", -120, "C"))
        self.assertGreater(p["pin_after"], p["pin_before"] + 0.02)
        self.assertIn("Pinnacle moved the under", p["reason"])
        self.assertEqual(p["window"], "90 → 45 min")                    # B read -> C read
        self.assertGreaterEqual(p["ev_vs_pin"], 0.0)                      # HR -120 vs Pinnacle's fair price (Pinnacle -149)
        s = self.w.read("slate.json")
        self.assertEqual(len(s["picks"]), 2)
        by = {x["book"]: x for x in s["picks"]}
        txt = notify.pick_line(by["hardrock"])
        self.assertIn("Pinnacle moved", txt)
        self.assertIn("(Hard Rock)", txt)
        self.assertNotIn("DraftKings", txt)
        self.assertEqual(by["hardrock"]["links"]["hardrock"]["price"], -120)
        self.assertIsNone(by["hardrock"]["links"]["draftkings"])
        self.assertIsNone(by["draftkings"]["links"]["hardrock"])
        self.assertEqual(by["draftkings"]["links"]["draftkings"]["price"], -115)
        # a later read with Pinnacle back where it was does not pull it (a pick is a signal, frozen)
        write(self.w, "2026-10-25T20:40:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T16:41:00-04:00")
        self.assertFalse([e for e in self.w.events() if e["t"] == "pulled"])

    def test_others_moving_no_longer_matters(self):
        # v2.5 (Matt): the other books moved with Pinnacle; only Pinnacle and the pick book's same line matter now.
        # DraftKings moved to -135 (worse than Pinnacle's fair price): Hard Rock alone, with only a Hard Rock button
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (105, -135))
        self.w.run("2026-10-25T16:16:00-04:00")
        sh = self.shown()
        self.assertEqual(len(sh), 1)
        p = sh[0]["pick"]
        self.assertEqual((p["price"], p["book"], list(p["books"])), (-120, "hardrock", ["hardrock"]))
        lk = self.w.read("slate.json")["picks"][0]["links"]
        self.assertIsNotNone(lk["hardrock"])
        self.assertIsNone(lk["draftkings"])

    def test_draftkings_only(self):
        # v2.5: Hard Rock -150 is worse than fair, DraftKings -110 is better: a DraftKings pick with only a DraftKings button
        write(self.w, "2026-10-25T19:30:00Z", (115, -150), (-102, -118), (-105, -115), dk=(-110, -110))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (115, -150), (112, -149), (-105, -115), dk=(-110, -110))
        self.w.run("2026-10-25T16:16:00-04:00")
        sh = self.shown()
        self.assertEqual(len(sh), 1)
        p = sh[0]["pick"]
        self.assertEqual((p["price"], p["book"], list(p["books"])), (-110, "draftkings", ["draftkings"]))
        sp = self.w.read("slate.json")["picks"][0]
        self.assertIsNone(sp["links"]["hardrock"])
        self.assertEqual(sp["links"]["draftkings"]["price"], -110)
        txt = notify.pick_line(sp)
        self.assertIn("(DraftKings)", txt)
        self.assertNotIn("Hard Rock", txt)

    def test_others_moved_a_little_still_a_pick(self):
        # v2.1 (Matt): the other books may move up to 2 pts the same way; here ~1.2 pts
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-102, -120))
        self.w.run("2026-10-25T16:16:00-04:00")
        sh = self.shown()
        self.assertEqual(len(sh), 2)                                    # v2.5b: Hard Rock and DraftKings, each its own pick
        self.assertGreater(sh[0]["pick"]["others_move"], 0.005)
        self.assertLess(sh[0]["pick"]["others_move"], 0.02)

    def test_better_than_pinnacle_posted_but_under_fair_no_pick(self):
        # v2.3 (Matt): HR -135 beats Pinnacle's posted -149 by 2+ pts, but Pinnacle's FAIR price on the under is about -127
        # (its margin removed), so HR is still worse than fair -> no pick
        write(self.w, "2026-10-25T19:30:00Z", (105, -135), (-102, -118), (-105, -115), dk=(105, -135))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (105, -135), (112, -149), (-105, -115), dk=(105, -135))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(self.shown(), [])

    def test_hard_rock_worse_than_pinnacle_no_pick(self):
        # Pinnacle moved the under to -149 alone, but Hard Rock's under is -150 (worse than Pinnacle) -> no pick
        write(self.w, "2026-10-25T19:30:00Z", (115, -150), (-102, -118), (-105, -115), dk=(115, -155))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (115, -150), (112, -149), (-105, -115), dk=(115, -155))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(self.shown(), [])

    def test_rule_change_takes_down_open_pick(self):
        # a pick shown under v2.1 (no gap gate) that fails the 2-pt gap is pulled (rule_change) and leaves the Tonight list
        cfg = json.load(open(self.w.config))
        cfg["pin_solo"].pop("min_gap_vs_pin", None)
        cfg["pin_solo"].pop("min_ev_vs_pin", None)
        json.dump(cfg, open(self.w.config, "w"))
        write(self.w, "2026-10-25T19:30:00Z", (115, -150), (-102, -118), (-105, -115), dk=(115, -150))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (115, -150), (112, -149), (-105, -115), dk=(115, -150))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(len(self.shown()), 2)                           # Hard Rock and DraftKings, each its own pick
        cfg["pin_solo"]["min_gap_vs_pin"] = 0.02
        json.dump(cfg, open(self.w.config, "w"))
        self.w.run("2026-10-25T16:20:00-04:00")
        pulled = [e for e in self.w.events() if e["t"] == "pulled"]
        self.assertEqual([e["code"] for e in pulled], ["rule_change", "rule_change"])
        self.assertEqual(self.w.read("slate.json")["picks"], [])
        self.assertFalse(any(n["entries"] for n in self.w.read("record.json")["nights"]))   # pulled: log only, not on the page Record

    def test_game_checks_and_final(self):
        # Matt 2026-11-02: each game says when it was checked and when no more checks can make a pick
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        g = [x for x in self.w.read("slate.json")["games"] if x["id"] == "401909861"][0]
        self.assertEqual(([c["read"] for c in g["checks"]], g["final"]), (["B"], False))
        self.assertIsNotNone(g["next_check_at"])
        write(self.w, "2026-10-25T20:40:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T16:41:00-04:00")                         # the 20-minute (last) check
        g = [x for x in self.w.read("slate.json")["games"] if x["id"] == "401909861"][0]
        self.assertEqual((g["final"], g["picks"], g["next_check_at"]), (True, 0, None))
        self.assertEqual(g["last_check_at"], "2026-10-25T16:41:00-04:00")

    def test_few_other_books_still_a_pick(self):
        # v2.5: how many other books quote the line no longer matters (was: at least 4)
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115), n_others=1)
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-105, -115), n_others=1)
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(sorted(e["pick"]["book"] for e in self.shown()), ["draftkings", "hardrock"])

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

    def test_one_book_removing_the_line_pulls_only_its_pick(self):
        # v2.5b: Hard Rock and DraftKings picks are independent; Hard Rock takes the line down -> only the Hard Rock pick is pulled
        write(self.w, "2026-10-25T19:30:00Z", (-110, -120), (-102, -118), (-105, -115))
        self.w.run("2026-10-25T15:31:00-04:00")
        write(self.w, "2026-10-25T20:15:00Z", (-110, -120), (112, -149), (-105, -115))
        self.w.run("2026-10-25T16:16:00-04:00")
        self.assertEqual(len(self.shown()), 2)
        at = "2026-10-25T20:40:00Z"
        bms = [book("hardrockbet", [("Lauri Markkanen", 6.5, -110, -110)], at), book("pinnacle", [(LUKA, 7.5, 112, -149)], at),
               book("draftkings", [(LUKA, 7.5, -105, -115)], at)]
        self.w.write_odds("odds_lal_utah.json", {"id": "ev401909861", "bookmakers": bms})
        self.w.run("2026-10-25T16:41:00-04:00")
        pulled = [e for e in self.w.events() if e["t"] == "pulled"]
        self.assertEqual([(e["code"], e["id"].endswith(":draftkings")) for e in pulled], [("line_gone", False)])

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
