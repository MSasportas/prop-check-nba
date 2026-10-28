"""QA v2.0: pin_solo must match research F7 (run3_pin_alone.py): Hard Rock quotes the SAME line on both reads."""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import engine  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
BOOKS = ["draftkings", "fanduel", "betmgm", "espnbet", "betrivers"]


def outs(line, over, under):
    return [{"name": "P One", "pid": "1", "team": "AAA", "side": "over", "line": line, "price": over},
            {"name": "P One", "pid": "1", "team": "AAA", "side": "under", "line": line, "price": under}]


def fetch(read, at, hr_line, pin_over, pin_under):
    others = {b: {"rebounds": {"outcomes": outs(7.5, -110, -110)}} for b in BOOKS}
    others["pinnacle"] = {"rebounds": {"outcomes": outs(7.5, pin_over, pin_under)}}
    return {"game_id": "g1", "away": "AAA", "home": "BBB", "read": read, "at": at,
            "markets": {"rebounds": {"last_update": at, "outcomes": outs(hr_line, -110, -110)}}, "others": others}


class Ctx:
    cfg, people = CFG, {}
    games = {"g1": {"id": "g1", "home": "BBB", "away": "AAA"}}

    def eligible(self, *a):
        return None


class TestPinSoloMatchesResearch(unittest.TestCase):
    def test_qualifies_when_hard_rock_line_same_on_both_reads(self):
        a = fetch("A", "2026-10-28T11:00:00-04:00", 7.5, -105, -115)
        b = fetch("B", "2026-10-28T17:30:00-04:00", 7.5, -130, +110)
        rows = [r for r in engine.solo_moves(a, b, Ctx()) if r["why"] is None]
        self.assertEqual([(r["side"], r["line"]) for r in rows], [("over", 7.5)])

    def test_no_pick_when_hard_rock_moved_its_line_between_reads(self):
        # research: `if k not in ha: continue` -- HR's 7.5 is new on read B (was 6.5 on A), so it is not a "Pinnacle alone" row
        a = fetch("A", "2026-10-28T11:00:00-04:00", 6.5, -105, -115)
        b = fetch("B", "2026-10-28T17:30:00-04:00", 7.5, -130, +110)
        rows = [r for r in engine.solo_moves(a, b, Ctx()) if r["why"] is None]
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
