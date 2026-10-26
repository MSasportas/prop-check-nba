"""tests/world.py: a fake world for end-to-end runs. Real ESPN / Rotowire payloads saved by the setup probe on 2026-10-25
(probe/), plus a made-up odds feed. Nothing touches the network: every client reads PC_*_FIXTURE_DIR."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "probe")
GAMES = {  # 2026-10-25 slate from the probe scoreboard
    "401909861": ("Los Angeles Lakers", "Utah Jazz", "2026-10-25T21:00:00Z"),
    "401909862": ("Indiana Pacers", "Brooklyn Nets", "2026-10-25T22:00:00Z"),
    "401909863": ("Orlando Magic", "New York Knicks", "2026-10-25T23:00:00Z"),
    "401909864": ("Toronto Raptors", "Minnesota Timberwolves", "2026-10-25T23:00:00Z"),
    "401909865": ("Los Angeles Clippers", "Oklahoma City Thunder", "2026-10-25T23:00:00Z"),
    "401909866": ("Detroit Pistons", "Philadelphia 76ers", "2026-10-25T23:30:00Z"),
    "401909867": ("Memphis Grizzlies", "Sacramento Kings", "2026-10-26T01:00:00Z"),
}
BOOKS = ["draftkings", "fanduel", "betmgm", "pinnacle", "betonlineag", "novig"]


def outcome(name, side, line, price):
    return {"name": side.capitalize(), "description": name, "point": line, "price": price}


def book(key, rows, at, link=False, feed_key="player_rebounds", extra=None):
    """rows: [(player, line, over, under)]; extra: {feed_key: rows} for more markets from the same book"""
    outs = []
    for nm, line, o, u in rows:
        a, b = outcome(nm, "over", line, o), outcome(nm, "under", line, u)
        if link:
            a["link"] = "https://app.hardrock.bet/slip?o=%s-over" % nm.split()[-1].lower()
            b["link"] = "https://app.hardrock.bet/slip?o=%s-under" % nm.split()[-1].lower()
        outs += [a, b]
    return {"key": key, "title": key, "last_update": at,
            "markets": [{"key": feed_key, "last_update": at, "outcomes": outs}] +
            [book(key, r, at, link, fk)["markets"][0] for fk, r in (extra or {}).items()]}


class World:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="pcnba_")
        self.data = os.path.join(self.tmp, "data")
        self.espn = os.path.join(self.tmp, "espn")
        self.odds = os.path.join(self.tmp, "odds")
        for d in (self.data, self.espn, self.odds):
            os.makedirs(d)
        shutil.copy(os.path.join(PROBE, "scoreboard_today.json"), os.path.join(self.espn, "scoreboard_20261025.json"))
        shutil.copy(os.path.join(PROBE, "injuries.json"), os.path.join(self.espn, "injuries.json"))
        shutil.copy(os.path.join(PROBE, "rotowire_lineups.html"), os.path.join(self.espn, "rotowire_lineups.html"))
        shutil.copy(os.path.join(PROBE, "roster_bos.json"), os.path.join(self.espn, "roster_BOS.json"))
        self.write_espn("scoreboard_20261024.json", {"events": []})
        self.write_odds("events.json", [{"id": "ev%s" % gid, "sport_key": "basketball_nba", "commence_time": t,
                                          "away_team": a, "home_team": h} for gid, (a, h, t) in GAMES.items()])
        self.write_odds("pool.json", {"keys": [500, 500, 500]})

    def write_espn(self, name, obj):
        with open(os.path.join(self.espn, name), "w") as f:
            json.dump(obj, f)

    def write_odds(self, name, obj):
        with open(os.path.join(self.odds, name), "w") as f:
            json.dump(obj, f)

    def lal_utah(self, at, hr, others, extra_books=None, hr_extra=None, others_extra=None):
        """hr / others: [(player, line, over, under)] rebounds for Hard Rock and for every other book; *_extra: {feed_key: rows}."""
        bms = [book("hardrockbet", hr, at, link=True, extra=hr_extra)] + \
              [book(b, others, at, extra=others_extra) for b in (extra_books or BOOKS)]
        self.write_odds("odds_lal_utah.json", {"id": "ev401909861", "bookmakers": bms})

    def run(self, now, *args, env=None):
        e = dict(os.environ, PC_NOW=now, PC_DATA_DIR=self.data, PC_ESPN_FIXTURE_DIR=self.espn,
                 PC_ODDS_FIXTURE_DIR=self.odds, ODDS_API_KEYS="k1,k2,k3")
        e.pop("DISCORD_WEBHOOK_URL", None)
        e.update(env or {})
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "run.py")] + list(args), env=e,
                           capture_output=True, text=True, timeout=300)
        return p

    def read(self, *parts):
        with open(os.path.join(self.data, *parts)) as f:
            return json.load(f)

    def events(self):
        p = os.path.join(self.data, "record", "events.jsonl")
        if not os.path.exists(p):
            return []
        return [json.loads(l) for l in open(p) if l.strip()]

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
