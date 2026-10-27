"""QA (2026-10-25): failure modes and Record edge cases. Run: python -m unittest discover -s tests"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)

import common  # noqa: E402
import odds  # noqa: E402
from world import World, book, BOOKS, GAMES  # noqa: E402

HR = [("Luka Doncic", 7.5, -135, 105)]
MKT = [("Luka Doncic", 7.5, 105, -125)]
PICK = "2026-10-25:401909861:3945274:rebounds:7.5:under"


def final_summary(w, reb=6):
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
    a["stats"][blk["labels"].index("REB")] = str(reb)
    w.write_espn("summary_401909861.json", s)


def set_game(w, ymd, gid, **status):
    p = os.path.join(w.espn, "scoreboard_%s.json" % ymd)
    sb = json.load(open(p))
    for e in sb["events"]:
        if e["id"] == gid:
            e["status"]["type"].update(status)
    sb["events"] = [e for e in sb["events"] if not status.get("_drop") or e["id"] != gid]
    w.write_espn("scoreboard_%s.json" % ymd, sb)


class TestQARecordEdges(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.lal_utah("2026-10-25T19:30:00Z", HR, MKT)
        self.w.write_espn("scoreboard_20261026.json", {"events": []})
        self.assertEqual(self.w.run("2026-10-25T15:31:00-04:00").returncode, 0)
        self.assertEqual([e["t"] for e in self.w.events()], ["shown"])

    def tearDown(self):
        self.w.close()

    def test_timer_stalls_past_rollover_pick_still_graded(self):
        """Pick shown, then no run until 6 AM the next day (chain down). The game is final: it must be graded."""
        set_game(self.w, "20261025", "401909861", state="post", completed=True, name="STATUS_FINAL")
        final_summary(self.w)
        self.w.run("2026-10-26T06:01:00-04:00")
        ts = [e["t"] for e in self.w.events()]
        self.assertIn("graded", ts, "open pick from yesterday's slate never locked, so never graded: %s" % ts)

    def test_game_vanishes_from_scoreboard_still_locks_and_grades(self):
        set_game(self.w, "20261025", "401909861", _drop=True)
        self.w.run("2026-10-25T17:05:00-04:00")
        ts = [e["t"] for e in self.w.events()]
        self.assertIn("locked", ts, "game gone from ESPN: pick never locks: %s" % ts)

    def test_postponed_game_is_voided(self):
        set_game(self.w, "20261025", "401909861", state="post", completed=False, name="STATUS_POSTPONED",
                 shortDetail="Postponed")
        self.w.run("2026-10-25T17:05:00-04:00")
        self.w.run("2026-10-26T06:05:00-04:00")
        ev = self.w.events()
        self.assertIn("graded", [e["t"] for e in ev], "postponed: locked but never graded: %s" % [e["t"] for e in ev])


class TestQASources(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def tearDown(self):
        self.w.close()

    def test_rotowire_layout_change_is_said_on_page(self):
        open(os.path.join(self.w.espn, "rotowire_lineups.html"), "w").write("<html>new layout</html>")
        self.w.run("2026-10-25T15:31:00-04:00")
        s = self.w.read("slate.json")
        self.assertTrue(any("lineup" in b["text"].lower() for b in s["banners"]),
                        "Rotowire parsed 0 teams but the page says nothing: %s" % s["banners"])

    def test_espn_down_first_run_does_not_crash(self):
        for f in os.listdir(self.w.espn):
            os.remove(os.path.join(self.w.espn, f))
        p = self.w.run("2026-10-25T15:31:00-04:00")
        self.assertEqual(p.returncode, 0, p.stderr)
        s = self.w.read("slate.json")
        self.assertTrue(s["banners"])

    def test_keys_never_written(self):
        key = "abcdef0123456789abcdef0123456789"
        self.w.lal_utah("2026-10-25T19:30:00Z", HR, MKT)
        p = self.w.run("2026-10-25T15:31:00-04:00", env={"ODDS_API_KEYS": key,
                                                          "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/1/SECRETTOKEN123"})
        blob = p.stdout + p.stderr
        for root, _, files in os.walk(self.w.data):
            for f in files:
                blob += open(os.path.join(root, f), "rb").read().decode("latin-1")
        self.assertNotIn(key, blob)
        self.assertNotIn("SECRETTOKEN123", blob)


class TestQAOddsClient(unittest.TestCase):
    """The real HTTP path (no fixture dir) with a fake http_get."""

    def setUp(self):
        self.old = common.http_get
        os.environ.pop("PC_ODDS_FIXTURE_DIR", None)
        self.tmp = World()
        os.environ["PC_DATA_DIR"] = self.tmp.data
        self.cfg = json.load(open(os.path.join(ROOT, "config", "rules.json")))

    def tearDown(self):
        common.http_get = self.old
        os.environ.pop("PC_DATA_DIR", None)
        self.tmp.close()

    def _pool(self):
        p = odds.Pool(["key-aaaaaa1", "key-bbbbbb2"], common.parse_iso("2026-10-25T15:31:00-04:00"))
        for s in p.state:
            s["left"] = 100
        return p

    def test_401_then_next_key(self):
        calls = []

        def fake(url, **kw):
            calls.append(url)
            if "key-aaaaaa1" in url:
                return common.Http(401, {}, b'{"message":"API key is not valid"}', "HTTP 401")
            return common.Http(200, {"x-requests-remaining": "99", "x-requests-last": "1"}, b'{"bookmakers":[]}')
        common.http_get = fake
        pool = self._pool()
        js, cost = odds.Client(pool, self.cfg).event_odds("ev1", "LAL", "UTAH", "2026-10-25", "B", "1")
        self.assertEqual(pool.state[0]["status"], "invalid")
        self.assertEqual(pool.state[1]["left"], 99)
        self.assertIsNotNone(js)

    def test_500_is_not_a_spend(self):
        common.http_get = lambda url, **kw: common.Http(500, {}, b"", "HTTP 500")
        pool = self._pool()
        js, cost = odds.Client(pool, self.cfg).event_odds("ev1", "LAL", "UTAH", "2026-10-25", "B", "1")
        self.assertIsNone(js)
        self.assertEqual(cost, 0)
        self.assertEqual([s["left"] for s in pool.state], [100, 100])


if __name__ == "__main__":
    unittest.main()


class TestQAOldRead(unittest.TestCase):
    def test_no_new_pick_from_an_old_read(self):
        """Doncic is Questionable at the B read (no pick). He is cleared 35 min later with no new read yet:
        a pick must not be made at a price read 35+ minutes ago."""
        w = World()
        try:
            w.lal_utah("2026-10-25T19:30:00Z", HR, MKT)
            rw = os.path.join(w.espn, "rotowire_lineups.html")
            clean = open(rw, encoding="utf-8", errors="replace").read()
            tag = '<a title="Luka Doncic" href="/basketball/player/luka-doncic-4396">Luka Doncic</a>'
            open(rw, "w").write(clean.replace(tag, tag + '<span class="lineup__inj">Ques</span>', 1))
            w.run("2026-10-25T15:31:00-04:00")
            self.assertEqual(w.events(), [])
            open(rw, "w").write(clean)
            w.run("2026-10-25T16:06:00-04:00")                 # C read is not due until 4:15
            ev = w.events()
            if ev:
                self.fail("pick made at 4:06 PM from the price read at %s" % ev[0]["pick"]["price_at"])
        finally:
            w.close()

    def test_a_read_retries_do_not_starve_b(self):
        """Hard Rock posts at 3:20 PM; other books are up all day (the real feed bills those reads).
        With a November-size allowance the B (90 min) read must still happen for the 5 PM game."""
        import teams
        import world as wd
        from datetime import datetime, timedelta
        w = World()
        try:
            w.write_odds("pool.json", {"keys": [170, 170, 170]})   # v1.2: 4 credits a read -> C and B

            def write(hr):
                for gid, (a, h, t) in GAMES.items():
                    bms = ([book("hardrockbet", HR, "2026-10-25T19:00:00Z", link=True)] if hr else []) + \
                          [book(b, MKT, "2026-10-25T19:00:00Z") for b in BOOKS]
                    w.write_odds("odds_%s_%s.json" % (teams.code(a).lower(), teams.code(h).lower()),
                                 {"id": "ev" + gid, "bookmakers": bms})
            write(False)
            t = datetime.fromisoformat("2026-10-25T11:01:00-04:00")
            while t <= datetime.fromisoformat("2026-10-25T15:41:00-04:00"):
                if t.hour == 15 and t.minute == 21:
                    write(True)
                w.run(t.isoformat())
                t += timedelta(minutes=10)
            doc = w.read("odds", "2026-10-25.json")
            b = [f for f in doc["fetches"] if f["game_id"] == "401909861" and f["read"] == "B"]
            spent_a = sum(1 for f in doc["fetches"] if f["read"] == "A")
            self.assertTrue(b, "no B read for the 5 PM game; %d A reads were billed first" % spent_a)
        finally:
            w.close()
