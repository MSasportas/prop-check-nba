"""Tap-to-bet buttons (Matt, 2026-11-02): Hard Rock slip + DraftKings link on open picks, page and Discord."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import notify  # noqa: E402
import odds  # noqa: E402

HR_APP = "https://app.hardrock.bet/?deep_link_value=betslip/%s"
DK = "https://sportsbook.draftkings.com/event/31?outcomes=0QA%s"


def fetch(gid, read, hr_id=None, dk_id=None, dk_price=-110, line=7.5):
    o = {"pid": "p1", "line": line, "side": "over", "price": 105}
    if hr_id:
        o["link"] = HR_APP % hr_id
    d = {"pid": "p1", "line": line, "side": "over", "price": dk_price}
    if dk_id:
        d["link"] = DK % dk_id
    return {"game_id": gid, "read": read, "markets": {"rebounds": {"outcomes": [o]}},
            "others": {"draftkings": {"rebounds": {"outcomes": [d]}}}}


class BetLinks(unittest.TestCase):
    def test_hardrock_slip(self):
        self.assertEqual(odds.hardrock_id(HR_APP % "5101654532757258648"), "5101654532757258648")
        self.assertEqual(odds.hardrock_slip(["5101654532757258648"]),
                         "https://share.hardrock.bet/Pt0T/bet?deep_link_value=hardrock://betslip/5101654532757258648")
        self.assertTrue(odds.hardrock_slip(["1111111", "2222222"]).endswith("betslip/1111111,2222222"))
        self.assertIsNone(odds.hardrock_slip([]))
        self.assertIsNone(odds.hardrock_id("https://app.hardrock.bet/"))

    def test_newest_read_wins_and_older_pick_still_gets_links(self):
        doc = {"fetches": [fetch("g1", "B", "1000000000000000001", "111", -115),
                           fetch("g1", "C", "1000000000000000002", "222", -105)]}
        lk = odds.bet_links(doc, "g1", "rebounds", "p1", 7.5, "over")
        self.assertTrue(lk["hardrock"]["url"].endswith("betslip/1000000000000000002"))
        self.assertEqual(lk["draftkings"], {"url": DK % "222", "price": -105})

    def test_no_link_no_button(self):
        doc = {"fetches": [fetch("g1", "C")]}
        self.assertEqual(odds.bet_links(doc, "g1", "rebounds", "p1", 7.5, "over"), {"hardrock": None, "draftkings": None})
        # other line, other side, other game: nothing borrowed
        doc = {"fetches": [fetch("g1", "C", "1000000000000000002", "222", line=8.5)]}
        self.assertEqual(odds.bet_links(doc, "g1", "rebounds", "p1", 7.5, "over"), {"hardrock": None, "draftkings": None})
        self.assertEqual(odds.bet_links(doc, "g2", "rebounds", "p1", 8.5, "over"), {"hardrock": None, "draftkings": None})
        self.assertEqual(odds.bet_links(doc, "g1", "rebounds", "p1", 8.5, "under"), {"hardrock": None, "draftkings": None})

    def test_dk_link_must_be_draftkings(self):
        f = fetch("g1", "C")
        f["others"]["draftkings"]["rebounds"]["outcomes"][0]["link"] = "https://evil.example/x"
        self.assertIsNone(odds.bet_links({"fetches": [f]}, "g1", "rebounds", "p1", 7.5, "over")["draftkings"])

    def test_normalize_keeps_dk_links_on_non_a_reads_only(self):
        cfg = {"markets": {"rebounds": {"feed_key": "player_rebounds"}}, "ops": {"bookmakers": ["hardrockbet"]}}
        out = lambda k, link: {"key": k, "markets": [{"key": "player_rebounds", "outcomes": [
            {"name": "Over", "description": "A B", "point": 7.5, "price": -110, "link": link}]}]}
        payload = {"bookmakers": [out("hardrockbet", HR_APP % "1000000000000000002"), out("draftkings", DK % "9"),
                                  out("fanduel", "https://sportsbook.fanduel.com/x")]}
        game = {"id": "g1", "away": "A", "home": "B"}
        find = lambda who: {"pid": "p1", "team": "A"}
        c = odds.normalize(payload, game, find, "C", odds.common.now(), 4, cfg)
        self.assertIn("link", c["others"]["draftkings"]["rebounds"]["outcomes"][0])
        self.assertNotIn("link", c["others"]["fanduel"]["rebounds"]["outcomes"][0])
        a = odds.normalize(payload, game, find, "A", odds.common.now(), 4, cfg)
        self.assertNotIn("link", a["others"]["draftkings"]["rebounds"]["outcomes"][0])
        self.assertNotIn("link", a["markets"]["rebounds"]["outcomes"][0])

    def test_discord_masked_links(self):
        p = {"price": 115, "links": {"hardrock": {"url": odds.hardrock_slip(["1000000000000000002"])},
                                     "draftkings": {"url": DK % "222", "price": -110}}}
        txt = notify.bet_buttons(p)
        self.assertEqual(txt, "[Hard Rock +115](<%s>) · [DraftKings -110](<%s>)" % (
            odds.HR_SHARE + "1000000000000000002", DK % "222"))
        self.assertEqual(notify.bet_buttons({"price": 115, "links": None}), "")
        self.assertEqual(notify.bet_buttons({"price": 115, "links": {"hardrock": {"url": "https://app.hardrock.bet/x"}}}), "")


if __name__ == "__main__":
    unittest.main()


class SpareRead(unittest.TestCase):
    """reads.spare (Matt, 2026-11-02): the 11 AM read comes back from spare credits, never at the cost of B / C / D."""
    def cfg(self):
        import json
        return json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "rules.json")))

    def test_plan_adds_a_from_spare(self):
        cfg = self.cfg()
        p = odds.make_plan(2768, 196, 14, cfg)            # 14.1 credits a game: B, C, D paid, A from spare
        self.assertEqual(p["reads"], ["A", "B", "C", "D"])
        self.assertEqual(p["spare"], ["A"])
        p = odds.make_plan(4000, 196, 14, cfg)            # 20 a game: A is paid for, not spare
        self.assertEqual(p["spare"], [])

    def test_spare_ok_keeps_bcd_reserve(self):
        cfg = self.cfg()
        p = odds.make_plan(2768, 196, 14, cfg)
        self.assertTrue(odds.spare_ok(2768, 196, p, 4))   # 2764 >= 12 * 196 = 2352
        self.assertFalse(odds.spare_ok(2355, 196, p, 4))  # 2351 < 2352: A pauses, B / C / D keep their credits
        self.assertTrue(odds.spare_ok(2356, 196, p, 4))

    def test_world_runs_and_pauses_the_11am_read(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from world import World
        for keys, want_a, banner in (([230, 230, 230], True, False), ([196, 196, 196], False, True)):
            w = World(rule="pin_solo")
            try:
                w.lal_utah("2026-10-25T15:00:00Z", [("Luka Doncic", 7.5, -110, -110)], [("Luka Doncic", 7.5, -110, -110)])
                w.write_odds("pool.json", {"keys": keys})       # 49 games left: B / C / D need 588
                self.assertEqual(w.run("2026-10-25T11:01:00-04:00").returncode, 0)
                got = os.path.exists(os.path.join(w.data, "odds", "2026-10-25.json"))
                self.assertEqual(got, want_a)
                texts = [b["text"] for b in w.read("slate.json").get("banners", [])]
                self.assertEqual(any("11 AM price check is paused" in t for t in texts), banner)
            finally:
                w.close()
