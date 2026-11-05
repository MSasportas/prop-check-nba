"""2026-11-04 (Matt, 11:12 PM): a pick pulled after it was shown (TOO LATE) counts on the Record like any other pick; rule_change
withdrawals and under-fair picks stay out; the -10u safety stop reads the same set. The Live tab polls the feeds from the browser
(no timer step, no data/live.json) and shows started too-late picks, never scratches.
Run: python -m unittest discover -s tests"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import engine  # noqa: E402
import record  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "rules.json")))
D = "2026-11-04"


def ev_pick(key, market="points", ev=0.02, price=-110):
    i = "%s:4019:%s:%s:10.5:over" % (D, key, market)
    return i, {"t": "shown", "kind": "single", "id": i, "at": D + "T18:00:00-05:00", "slate": D,
               "pick": {"rule": "pin_solo", "player": key, "pid": key, "team": "NY", "opp": "BOS", "home": False, "game_id": "4019",
                        "start": D + "T19:30:00-05:00", "market": market, "line": 10.5, "side": "over", "bet": "Over 10.5",
                        "price": price, "ev_vs_pin": ev, "state": "clear", "window": "90 → 45 min"}}


def graded(i, res, price=-110):
    return {"t": "graded", "id": i, "at": D + "T22:30:00-05:00", "result": res, "actual": None,
            "actual_text": "did not play" if res == "VOID" else "12 points", "price": price, "units": record.single_units(res, price)}


def pulled(i, code, reason):
    return {"t": "pulled", "id": i, "at": D + "T19:10:00-05:00", "code": code, "reason": reason, "if_bet": "x"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pcnba_lp_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        old = os.environ.get("PC_DATA_DIR")
        os.environ["PC_DATA_DIR"] = self.tmp                 # no replay file: only these events
        self.addCleanup(lambda: os.environ.__setitem__("PC_DATA_DIR", old) if old is not None else os.environ.pop("PC_DATA_DIR", None))

    def world(self):
        ev = []
        a, e = ev_pick("plain"); ev += [e, graded(a, "W")]                                               # +0.91
        b, e = ev_pick("gone", "rebounds"); ev += [e, pulled(b, "line_gone", "Hard Rock took the line down"), graded(b, "W")]  # +0.91
        c, e = ev_pick("ques", "assists"); ev += [e, pulled(c, "status", "Now listed questionable"), graded(c, "L")]       # -1
        d, e = ev_pick("scr"); ev += [e, pulled(d, "status", "Now listed out"), graded(d, "VOID")]                     # 0
        r, e = ev_pick("rule"); ev += [e, pulled(r, "rule_change", "Rule change"), graded(r, "L")]                     # out
        f, e = ev_pick("under", ev=-0.01); ev += [e, graded(f, "W")]                                       # out
        return ev, {"plain": a, "gone": b, "ques": c, "scr": d, "rule": r, "under": f}


class RecordCountsPulled(Base):
    def test_headline_rows_days_cuts_and_entries(self):
        ev, ids = self.world()
        raw = "".join(json.dumps(e) + "\n" for e in ev)
        rec, _ = record.build_views(ev, CFG)
        hd = rec["summary"]["headline"]
        self.assertEqual((hd["w"], hd["l"], hd["void"], hd["units"]), (2, 1, 1, 0.82))
        rows = {r["key"]: r for r in rec["summary"]["rows"]}
        self.assertNotIn("pulled", rows)                                 # no separate row
        self.assertEqual((rows["rebounds"]["w"], rows["assists"]["l"], rows["points"]["w"]), (1, 1, 1))
        self.assertEqual(rows["window:90 → 45 min"]["n"], 3)
        day = rec["summary"]["days"][0]
        self.assertEqual((day["w"], day["l"], day["units"]), (2, 1, 0.82))
        n = rec["nights"][0]
        self.assertEqual((n["w"], n["l"], n["units"]), (2, 1, 0.82))
        listed = {e["id"]: e for e in n["entries"]}
        self.assertEqual(set(listed), {ids["plain"], ids["gone"], ids["ques"], ids["scr"]})
        self.assertEqual(listed[ids["gone"]]["pulled"]["code"], "line_gone")
        self.assertEqual(listed[ids["gone"]]["price"], -110)           # graded at the posted price
        mk = next(c for c in rec["summary"]["cuts"] if c["key"] == "market")
        self.assertEqual(sum(r["w"] + r["l"] for r in mk["rows"]), 3)
        self.assertEqual("".join(json.dumps(e) + "\n" for e in ev), raw)   # views only: events not touched

    def test_safety_stop_reads_the_same_set(self):
        ev, _ = self.world()
        rec, _ = record.build_views(ev, CFG)
        paused, units = engine.safety_paused(record.fold(ev), CFG)
        self.assertEqual(units, rec["summary"]["headline"]["units"])
        self.assertFalse(paused)
        # ten counted too-late losses trip it; ten rule_change or under-fair losses do not
        more = []
        for k in range(11):
            i, e = ev_pick("tl%d" % k); more += [e, pulled(i, "line_gone", "Hard Rock took the line down"), graded(i, "L")]
        self.assertTrue(engine.safety_paused(record.fold(ev + more), CFG)[0])
        more = []
        for k in range(11):
            i, e = ev_pick("rc%d" % k); more += [e, pulled(i, "rule_change", "Rule change"), graded(i, "L")]
            j, e2 = ev_pick("uf%d" % k, ev=-0.02); more += [e2, graded(j, "L")]
        self.assertFalse(engine.safety_paused(record.fold(ev + more), CFG)[0])

    def test_real_log_untouched_and_safety_matches_headline(self):
        shutil.copytree(os.path.join(ROOT, "data", "replay"), os.path.join(self.tmp, "replay"))
        path = os.path.join(ROOT, "data", "record", "events.jsonl")
        raw = open(path, "rb").read()
        h = hashlib.sha256(raw).hexdigest()
        ev = record.parse(raw)
        rec, _ = record.build_views(ev, CFG)
        self.assertEqual(engine.safety_paused(record.fold(ev), CFG)[1], rec["summary"]["headline"]["units"])
        self.assertEqual(hashlib.sha256(open(path, "rb").read()).hexdigest(), h)

    def test_rules_text(self):
        import run
        lines = " ".join(run.rules_doc(CFG)["lines"])
        self.assertIn("If Hard Rock moves the line after a pick is shown, the page marks it TOO LATE for anyone who hasn't bet it; "
                      "it still counts on the Record like any other pick.", lines)


class TimerHasNoLiveStep(unittest.TestCase):
    def test_gone(self):
        src = open(os.path.join(ROOT, "scripts", "run.py")).read()
        self.assertNotIn("live", re.findall(r'r\.step\("(\w+)"', src))
        self.assertFalse(os.path.exists(os.path.join(ROOT, "scripts", "live.py")))
        for wf in ("live_probe.yml", "cors_probe.yml"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, ".github", "workflows", wf)))


class Page(unittest.TestCase):
    def setUp(self):
        self.html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

    def test_live_reads_the_feeds_not_live_json(self):
        h = self.html
        self.assertNotIn("live.json", h)
        self.assertIn("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/", h)
        self.assertIn("https://cdn.nba.com/static/json/liveData/", h)
        self.assertIn("LIVE_MS = 10000", h)
        self.assertNotIn("innerHTML", h)
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", h))
        self.assertLessEqual(hosts, {"site.api.espn.com", "cdn.nba.com", "a.espncdn.com", "www.w3.org", "share.hardrock.bet"})

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_live_shows_started_too_late_and_hides_scratches(self):
        h = self.html
        src = "".join(re.search(r"\nfunction %s\([\s\S]*?\n}\n" % n, h).group(0) for n in ("isScratch", "counted"))
        js = ("function isObj(v){return v!==null&&typeof v==='object'&&!Array.isArray(v)} function str(v){return v==null?'':String(v)}"
              "function num(v){return typeof v==='number'&&isFinite(v)?v:null}" + src +
              "var t=function(c,r){return {pulled:{code:c,reason:r},rule:'pin_solo',ev_vs_pin:0.02}};"
              "console.log(JSON.stringify([counted(t('line_gone','x'))&&!isScratch(t('line_gone','x')),"
              "counted(t('status','Now listed questionable'))&&!isScratch(t('status','Now listed questionable')),"
              "isScratch(t('out','Now listed out')), counted(t('rule_change','x')),"
              "counted({rule:'pin_solo',ev_vs_pin:-0.01}), counted({rule:'pin_solo',ev_vs_pin:0.01})]))")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(json.loads(out.stdout), [True, True, True, False, False, True], out.stderr)

    def test_fixtures_have_the_live_feeds(self):
        fx = os.path.join(ROOT, "fixtures")
        for name in ("liveon", "liveespnfail", "livedone", "livepre"):
            for f in ("espn_scoreboard.json", "nba_scoreboard.json"):
                self.assertTrue(os.path.exists(os.path.join(fx, name, "feeds", f)), (name, f))
        sl = json.load(open(os.path.join(fx, "liveon", "slate.json")))
        codes = {p["player"]: (p["pulled"] or {}).get("code") for p in sl["picks"]}
        self.assertEqual((codes["Josh Hart"], codes["Franz Wagner"]), ("line_gone", "out"))   # Live shows Hart, never Wagner


if __name__ == "__main__":
    unittest.main()
