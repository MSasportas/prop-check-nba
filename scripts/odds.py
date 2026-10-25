"""odds.py: Hard Rock rebounds prices from the-odds-api (bookmaker `hardrockbet`), with 9 other books beside it.

keys    env ODDS_API_KEYS (then ODDS_API_KEYS_2) only. Never printed, never written. Used-up or refused keys are skipped.
ledger  data/state/credits.json: credits left per key NUMBER (never the key) and every credit spent.
plan    allowance = pool credits left / games left before the keys refill on the 1st. It decides how many of the four reads
        (priority C, B, D, A: config reads.priority) each game gets.
reads   A morning baseline, B 90 min, C 45 min, D 20 min before tip. A read made at time t satisfies every read due at or before t.
cost    1 credit per market returned per region; Hard Rock + up to 9 other books bill as one region, so 1 credit a read.
        The events list is free. With PC_ODDS_FIXTURE_DIR set nothing here touches the network.
Hard Rock is THE book: a fetch's "markets" is Hard Rock; other books sit under "others".
"""
import json
import math
import os
import re
import urllib.parse
from datetime import datetime, timedelta

import common
import names

API_ROOT = "https://api.the-odds-api.com/v4/sports/"
MAX_BOOKS_PER_REGION = 10
SOURCE = {"ok": 0, "failed": 0}
READS = ("A", "B", "C", "D")


# ---------------------------------------------------------------- price arithmetic
def break_even(american):
    return (-american) / (-american + 100.0) if american < 0 else 100.0 / (american + 100.0)


def decimal(american):
    return 1.0 + (100.0 / -american if american < 0 else american / 100.0)


def american(dec):
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def fair_two_sided(price_side, price_other):
    a, b = break_even(price_side), break_even(price_other)
    return a / (a + b)


def hold(price_a, price_b):
    return break_even(price_a) + break_even(price_b) - 1.0


def ev(prob, price):
    """Expected value per unit at this price for a chance `prob`."""
    return prob * decimal(price) - 1.0


# ---------------------------------------------------------------- keys and ledger
def load_keys():
    keys = []
    for var in ("ODDS_API_KEYS", "ODDS_API_KEYS_2"):
        for k in os.environ.get(var, "").replace("\n", ",").split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    for k in keys:
        common.register_secret(k)
    return keys


def fixture_dir():
    return os.environ.get("PC_ODDS_FIXTURE_DIR")


def ledger_path():
    return common.dpath("state", "credits.json")


class Pool:
    """The key pool and its ledger. Keys are known only by position (n = 1, 2, ...)."""

    def __init__(self, keys, now):
        self.keys, self.now = keys, now
        self.fixture = bool(fixture_dir())
        led = common.read_json(ledger_path(), {}) or {}
        self.spent = led.get("spent", [])
        saved = led.get("keys", [])
        month = now.strftime("%Y-%m")
        if self.fixture and self.keys:                     # fixtures: credits from pool.json (no keys set = no keys)
            start = (common.read_json(os.path.join(fixture_dir(), "pool.json"), {}) or {}).get("keys", [500])
            self.keys = ["fixture-key-%d" % (i + 1) for i in range(len(start))]
        self.state = []
        for i in range(len(self.keys)):
            s = saved[i] if i < len(saved) and led.get("count") == len(self.keys) else {}
            left = s.get("left") if s.get("month") == month else None     # keys refill on the 1st
            if self.fixture and left is None:
                left = start[i]
            status = "ok" if left != 0 else "empty"
            if s.get("status") == "invalid" and s.get("month") == month and not self.fixture:
                status = "invalid"
            self.state.append({"n": i + 1, "left": left, "status": status, "checked_at": s.get("checked_at"),
                               "month": month})

    def count(self):
        return len(self.keys)

    def unknown(self):
        return sum(1 for s in self.state if s["left"] is None or s["status"] == "invalid")

    def known(self):
        return any(s["left"] is not None and s["status"] != "invalid" for s in self.state)

    def all_refused(self):
        st = self.state
        return bool(st) and all(s["status"] == "invalid" or s["left"] == 0 for s in st) and \
            any(s["status"] == "invalid" for s in st)

    def all_used_up(self):
        return bool(self.state) and all(s["left"] == 0 for s in self.state)

    def total_left(self):
        return sum(s["left"] for s in self.state if s["left"] is not None and s["status"] != "invalid")

    def public(self):
        return [{"n": s["n"], "left": s["left"], "status": s["status"]} for s in self.state]

    def spent_on(self, slate):
        return sum(e["cost"] for e in self.spent if e["date"] == slate)

    def note_headers(self, i, headers, slate=None, read=None, game_id=None, returned=0):
        s = self.state[i]
        try:
            s["left"] = int(float(headers.get("x-requests-remaining")))
        except (TypeError, ValueError):
            if s["left"] is not None and returned:
                s["left"] = max(0, s["left"] - returned)
        try:
            cost = int(float(headers.get("x-requests-last")))
        except (TypeError, ValueError):
            cost = returned
        s["checked_at"] = common.iso(self.now)
        s["status"] = "empty" if s["left"] == 0 else "ok"
        if slate and cost:
            self.spent.append({"at": common.iso(self.now), "date": slate, "read": read, "game_id": game_id,
                               "cost": cost, "key": s["n"]})
        return cost

    def save(self):
        keep_from = (self.now - timedelta(days=62)).date().isoformat()
        self.spent = [e for e in self.spent if e["date"] >= keep_from]
        common.write_json(ledger_path(), {"count": len(self.keys), "keys": self.state, "spent": self.spent})

    def candidates(self, need):
        return [i for i, s in enumerate(self.state) if s["status"] == "ok" and (s["left"] is None or s["left"] >= need)]


class Client:
    def __init__(self, pool, cfg):
        self.pool, self.cfg = pool, cfg
        self.api = API_ROOT + cfg["ops"]["sport_key"]
        self.errors = []

    def _get(self, path, params, need, slate=None, read=None, game_id=None):
        for i in self.pool.candidates(need):
            q = urllib.parse.urlencode(dict(params, apiKey=self.pool.keys[i]))
            r = common.http_get("%s%s?%s" % (self.api, path, q), timeout=30)
            if r.ok:
                js = r.json()
                if js is None:
                    self.errors.append("odds feed sent an unreadable answer")
                    SOURCE["failed"] += 1
                    return None, 0
                cost = self.pool.note_headers(i, r.headers, slate, read, game_id, markets_returned(js) if need else 0)
                SOURCE["ok"] += 1
                return js, cost
            if r.status in (401, 429):
                body = r.text().upper()
                st = self.pool.state[i]
                if "OUT_OF_USAGE" in body or "QUOTA" in body or "USAGE" in body:
                    st["left"], st["status"] = 0, "empty"
                elif r.status == 401:
                    st["status"] = "invalid"
                else:
                    st["status"] = "limited"
                st["checked_at"] = common.iso(self.pool.now)
                self.errors.append("key %d refused (%d), trying the next" % (i + 1, r.status))
                continue
            if r.status in (404, 422):                      # event or market not offered: not a feed failure
                SOURCE["ok"] += 1
                return {}, 0
            self.errors.append("odds feed did not answer (%s)" % (r.error or r.status))
            SOURCE["failed"] += 1
            return None, 0
        self.errors.append("every odds key was refused" if self.pool.all_refused() else "no odds key with credits left")
        return None, 0

    def _fixture(self, name):
        try:
            with open(os.path.join(fixture_dir(), name), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def events(self, only_unknown=False):
        """The free events list, asked once per key so every key reports what it has left."""
        if self.pool.fixture:
            ev = self._fixture("events.json")
            SOURCE["ok" if ev is not None else "failed"] += 1
            return ev
        out = None
        for i in range(self.pool.count()):
            st = self.pool.state[i]
            if only_unknown and st["left"] is not None and st["status"] != "invalid":
                continue
            q = urllib.parse.urlencode({"apiKey": self.pool.keys[i], "dateFormat": "iso"})
            r = common.http_get("%s/events?%s" % (self.api, q), timeout=30)
            if r.ok and r.json() is not None:
                self.pool.note_headers(i, r.headers)
                out = out if out is not None else r.json()
                SOURCE["ok"] += 1
            elif r.status in (401, 429):
                body = r.text().upper()
                if "USAGE" in body or "QUOTA" in body:
                    st["left"], st["status"] = 0, "empty"
                else:
                    st["status"] = "invalid" if r.status == 401 else "limited"
                st["checked_at"] = common.iso(self.pool.now)
                self.errors.append("key %d refused (%d)" % (i + 1, r.status))
            else:
                self.errors.append("odds feed did not answer (%s)" % (r.error or r.status))
                SOURCE["failed"] += 1
        return out

    def event_odds(self, event_id, away, home, slate, read, game_id, links=True):
        """Rebounds prices for one game from Hard Rock + the other books. (payload or None, cost); None = retry later."""
        books = request_books(self.cfg)
        keys = [m["feed_key"] for m in self.cfg["markets"].values()]
        if self.pool.fixture:
            js = self._fixture("odds_%s_%s.json" % (away.lower(), home.lower())) or self._fixture("odds_%s.json" % event_id)
            if js is None:
                self.errors.append("odds feed did not answer (no fixture for %s at %s)" % (away, home))
                SOURCE["failed"] += 1
                return None, 0
            js = json.loads(json.dumps(js))
            js["bookmakers"] = [b for b in js.get("bookmakers", []) or [] if b.get("key") in books]
            cost = markets_returned(js)
            for i in self.pool.candidates(cost):
                st = self.pool.state[i]
                st["left"] -= cost
                st["status"] = "empty" if st["left"] == 0 else "ok"
                if cost:
                    self.pool.spent.append({"at": common.iso(self.pool.now), "date": slate, "read": read,
                                            "game_id": game_id, "cost": cost, "key": st["n"]})
                SOURCE["ok"] += 1
                return js, cost
            self.errors.append("no odds key with credits left")
            return None, 0
        params = {"regions": self.cfg["ops"]["odds_region"], "bookmakers": ",".join(books), "markets": ",".join(keys),
                  "oddsFormat": "american", "dateFormat": "iso"}
        if links and read != "A":
            params["includeLinks"] = "true"
            js, cost = self._get("/events/%s/odds" % event_id, params, len(keys), slate, read, game_id)
            if js or (js is None and self.errors and self.errors[-1].startswith("odds feed sent an unreadable")):
                return js, cost
            params.pop("includeLinks")                     # never let the links option cost a price read
        return self._get("/events/%s/odds" % event_id, params, len(keys), slate, read, game_id)


def request_books(cfg):
    books = list(cfg["ops"]["bookmakers"])
    for b in cfg["ops"].get("consensus_books") or []:
        if b not in books and len(books) < MAX_BOOKS_PER_REGION:
            books.append(b)
    return books


def markets_returned(js):
    keys = set()
    if not isinstance(js, dict):
        return 0
    for b in js.get("bookmakers", []) or []:
        for m in b.get("markets", []) or []:
            keys.add(m.get("key"))
    return len(keys)


# ---------------------------------------------------------------- the plan (pure functions)
def days_to_reset(slate):
    d = datetime.fromisoformat(slate).date()
    first = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return (first - d).days


def reads_per_game(allowance, cfg):
    """How many reads each game gets: one per whole credit of allowance, at most 4, at least 1 (C only)."""
    n = int(math.floor(allowance + 1e-9))
    return max(1, min(len(READS), n))


def active_reads(allowance, cfg):
    pri = cfg["reads"]["priority"]
    return set(pri[:reads_per_game(allowance, cfg)])


def make_plan(pool_left, games_left, games_today, cfg):
    allowance = (pool_left / float(games_left)) if games_left else 0.0
    return {"allowance": round(allowance, 3), "reads": sorted(active_reads(allowance, cfg)),
            "budget_today": int(math.floor(allowance * games_today + 1e-9)) if games_left else 0,
            "pool_at_plan": pool_left, "games_left": games_left, "games_today": games_today}


def due_times(game, games, cfg):
    """{read: due datetime} for one game."""
    r = cfg["reads"]
    tip = common.parse_iso(game["start"])
    first = min(common.parse_iso(g["start"]) for g in games)
    hh, mm = [int(x) for x in r["a_clock"].split(":")]
    a_clock = tip.astimezone(common.ET).replace(hour=hh, minute=mm, second=0)
    a = min(a_clock, first - timedelta(minutes=r["a_before_first_min"]))
    return {"A": a, "B": tip - timedelta(minutes=r["b_min"]), "C": tip - timedelta(minutes=r["c_min"]),
            "D": tip - timedelta(minutes=r["d_min"])}


def due_reads(now, games, reads, done, started, cfg):
    """Which game needs a read right now. done: {game_id: [{"read","at"(datetime),"returned"(bool)}]}.
    A read is due when its time has passed, the game has not started (latest_min before tip), and no read that RETURNED
    rebounds has been made since its due time. If the market was not posted, ask again after retry_min.
    Returns [{"game", "read"}] in tip order; read = the latest due read type (it also covers earlier ones)."""
    r = cfg["reads"]
    out = []
    for g in sorted(games, key=lambda x: (x["start"], x["id"])):
        if started.get(g["id"]):
            continue
        tip = common.parse_iso(g["start"])
        if (tip - now).total_seconds() / 60.0 < r["latest_min"]:
            continue
        dt = due_times(g, games, cfg)
        cands = [k for k in READS if k in reads and dt[k] <= now]
        if not cands:
            continue
        k = max(cands, key=lambda x: dt[x])
        mine = done.get(g["id"], [])
        if any(f["returned"] and f["at"] >= dt[k] for f in mine):
            continue
        tries = [f["at"] for f in mine if f["at"] >= dt[k] and not f["returned"]]
        # A read that comes back without Hard Rock may still be billed (other books posted), so: the morning A read is
        # tried once, a B / C / D read at most twice (QA 2026-10-25: retries could eat the day's budget and starve B)
        if (k == "A" and tries) or len(tries) >= 2:
            continue
        if tries and (now - max(tries)).total_seconds() / 60.0 < r["retry_min"]:
            continue
        out.append({"game": g, "read": k})
    return out


def next_read_at(now, games, reads, done, started, cfg):
    best = None
    for g in games:
        if started.get(g["id"]):
            continue
        tip = common.parse_iso(g["start"])
        for k, t in due_times(g, games, cfg).items():
            if k in reads and t > now and tip - timedelta(minutes=cfg["reads"]["latest_min"]) > t:
                best = t if best is None else min(best, t)
    return best


# ---------------------------------------------------------------- matching events and normalizing
def match_events(events, games, hours, team_of_name):
    """Feed events -> ESPN game ids by both team names and a start time within `hours`."""
    out, unknown = {}, []
    for e in events or []:
        a, h = team_of_name(e.get("away_team")), team_of_name(e.get("home_team"))
        for nm, ab in ((e.get("away_team"), a), (e.get("home_team"), h)):
            if ab is None and nm and nm not in unknown:
                unknown.append(nm)
        if not a or not h:
            continue
        when = common.parse_iso(e.get("commence_time"))
        if when is None:
            continue
        for g in games:
            if g["away"] == a and g["home"] == h and abs((common.parse_iso(g["start"]) - when).total_seconds()) <= hours * 3600:
                out[str(g["id"])] = e["id"]
    return out, unknown


_LINK_RE = re.compile(r"https://[^\s<>\"'\\\x00-\x1f\x7f‎‏‪-‮⁦-⁩]{4,590}")


def safe_link(x):
    return x if isinstance(x, str) and _LINK_RE.fullmatch(x) else None


def _rows(m, find, unmatched, links=False):
    rows = []
    for o in m.get("outcomes", []) or []:
        who = o.get("description") or ""
        side = (o.get("name") or "").lower()
        if side not in ("over", "under") or o.get("price") is None:
            continue
        p = find(who)
        if p is None and unmatched is not None and who not in unmatched:
            unmatched.append(who)
        try:
            price = int(round(float(o["price"])))
            line = float(o["point"]) if o.get("point") is not None else None
        except (TypeError, ValueError):
            continue
        row = {"name": who, "pid": p["pid"] if p else None, "team": p["team"] if p else None,
               "side": side, "line": line, "price": price}
        if links and safe_link(o.get("link")):
            row["link"] = o["link"]
        rows.append(row)
    return rows


def normalize(payload, game, matcher, read, at, cost, cfg):
    """One game's raw feed answer -> what we keep in data/odds/<date>.json."""
    key_to_market = {m["feed_key"]: k for k, m in cfg["markets"].items()}
    hr_key = cfg["ops"]["bookmakers"][0]
    books = (payload or {}).get("bookmakers", []) or []
    hr = next((b for b in books if b.get("key") == hr_key), None)
    out = {"game_id": game["id"], "away": game["away"], "home": game["home"], "read": read, "at": common.iso(at),
           "cost": cost, "book": hr_key if hr else None, "markets": {}, "others": {}, "unmatched": []}
    seen = {}

    def find(who):
        if who not in seen:
            seen[who] = matcher(who) if matcher else None
        return seen[who]

    for m in (hr or {}).get("markets", []) or []:
        k = key_to_market.get(m.get("key"))
        if k:
            out["markets"][k] = {"last_update": m.get("last_update"),
                                 "outcomes": _rows(m, find, out["unmatched"], links=(read != "A"))}
    for b in books:
        if b is hr or not b.get("key"):
            continue
        bm = {}
        for m in b.get("markets", []) or []:
            k = key_to_market.get(m.get("key"))
            if k:
                bm[k] = {"last_update": m.get("last_update"), "outcomes": _rows(m, find, None)}
        if bm:
            out["others"][b["key"]] = bm
    return out


# ---------------------------------------------------------------- the read step
def day_path():
    return common.dpath("state", "odds_day.json")


def odds_path(slate):
    return common.dpath("odds", "%s.json" % slate)


def load_day(slate):
    d = common.read_json(day_path(), {}) or {}
    if d.get("date") != slate:
        d = {"date": slate, "plan": None, "events": {}, "events_at": None, "unknown_teams": [], "key_count": None}
    for k, dv in (("events", {}), ("unknown_teams", [])):
        d.setdefault(k, dv)
    return d


def done_map(slate):
    """{game_id: [{"read","at","returned"}]} from today's odds file."""
    out = {}
    for f in (common.read_json(odds_path(slate), {}) or {}).get("fetches", []):
        out.setdefault(f["game_id"], []).append({"read": f["read"], "at": common.parse_iso(f["at"]),
                                                 "returned": bool(f.get("markets"))})
    return out


def run_reads(now, slate, games, games_left_month, cfg, matcher_for, started, team_of_name, dry_run=False):
    """The whole odds step. Returns a result dict for status.json and the page."""
    keys = load_keys()
    pool = Pool(keys, now)
    client = Client(pool, cfg)
    day = load_day(slate)
    res = {"status": "ok", "note": "", "keys": pool.public(), "pool_left": None, "plan": day.get("plan"),
           "fetched_now": 0, "errors": client.errors, "no_keys": pool.count() == 0, "refused": False}
    if pool.count() == 0:
        res.update(status="skipped", note="no odds keys set")
        return _finish(day, pool, res, dry_run)
    if not games:
        res.update(status="skipped", note="no games today")
        return _finish(day, pool, res, dry_run)
    need_events = day.get("events_at") is None or day.get("key_count") != pool.count() or pool.unknown() > 0
    missing = any(str(g["id"]) not in day["events"] and not started.get(g["id"]) for g in games)
    last = common.parse_iso(day.get("events_at"))
    if missing and (last is None or (now - last).total_seconds() >= 1800):
        need_events = True
    if need_events and not dry_run:
        evs = client.events()
        if evs is not None:
            m, unknown = match_events(evs, games, cfg["ops"]["event_match_hours"], team_of_name)
            day["events"].update(m)
            day["unknown_teams"] = unknown
            day["events_at"] = common.iso(now)
            day["key_count"] = pool.count()
    old = day.get("plan")
    if pool.known() and (old is None or old.get("key_count") != pool.count() or
                         (old.get("pool_at_plan", 0) == 0 and pool.total_left() > 0)):
        plan = make_plan(pool.total_left() + pool.spent_on(slate), games_left_month, len(games), cfg)
        plan.update(key_count=pool.count(), made_at=common.iso(now))
        day["plan"] = plan
    plan = day.get("plan")
    res["plan"] = plan
    if plan is None:
        res["refused"] = pool.all_refused()
        res.update(status="skipped" if res["refused"] else ("failed" if client.errors else "skipped"),
                   note="every odds key was refused" if res["refused"] else "could not read the odds keys yet")
        return _finish(day, pool, res, dry_run)
    done = done_map(slate)
    due = due_reads(now, games, set(plan["reads"]), done, started, cfg)
    doc = common.read_json(odds_path(slate)) or {"date": slate, "fetches": []}
    failed, no_budget = [], []
    for d in due:
        g = d["game"]
        if dry_run:
            continue
        # C (the 45-minute read) may use tomorrow's share if today's is spent: it is the read that protects live picks
        if (pool.spent_on(slate) >= plan["budget_today"] and d["read"] not in ("C", "D")) or pool.total_left() < 1:
            no_budget.append(g["id"])
            continue
        ev = day["events"].get(str(g["id"]))
        if not ev:
            failed.append(g["id"])
            client.errors.append("no feed event for %s at %s" % (g["away"], g["home"]))
            continue
        payload, cost = client.event_odds(ev, g["away"], g["home"], slate, d["read"], g["id"])
        if payload is None:
            failed.append(g["id"])
            continue
        doc["fetches"].append(normalize(payload, g, matcher_for(g), d["read"], now, cost, cfg))
        res["fetched_now"] += 1
        common.write_json(odds_path(slate), doc, pretty=False)       # credits were spent: keep the answer even if we crash
        pool.save()
    if failed and not res["fetched_now"]:
        res["status"] = "failed"
    if pool.all_refused():
        res.update(status="skipped", refused=True, note="every odds key was refused")
    if not res["note"]:
        bits = []
        if res["fetched_now"]:
            got = sum(1 for f in doc["fetches"][-res["fetched_now"]:] if f["markets"])
            bits.append("%d game(s) priced" % got)
            if res["fetched_now"] - got:
                bits.append("%d not posted yet" % (res["fetched_now"] - got))
        if failed:
            bits.append("%d failed" % len(failed))
        if no_budget:
            bits.append("%d skipped, budget used" % len(no_budget))
        res["note"] = ", ".join(bits) or "no read due"
    res["next_read_at"] = common.iso(next_read_at(now, games, set(plan["reads"]), done, started, cfg)) \
        if next_read_at(now, games, set(plan["reads"]), done, started, cfg) else None
    return _finish(day, pool, res, dry_run)


def _finish(day, pool, res, dry_run):
    res["keys"] = pool.public()
    res["pool_left"] = pool.total_left() if pool.known() else None
    res["all_used_up"] = pool.all_used_up()
    res["spent_today"] = pool.spent_on(day["date"])
    res["unknown_teams"] = day.get("unknown_teams", [])
    if not dry_run:
        pool.save()
        common.write_json(day_path(), day)
    return res


# ---------------------------------------------------------------- reading prices back
def is_stale(last_update, read_at, stale_min):
    lu = common.parse_iso(last_update) if last_update else None
    return lu is None or (read_at - lu).total_seconds() / 60.0 >= stale_min


def pairs(rows):
    """[{pid,line,side,price,...}] -> {(pid, line): {"over", "under", "name", "team", "link_over", "link_under"}}"""
    out = {}
    for o in rows or []:
        if o.get("pid") is None or o.get("line") is None:
            continue
        p = out.setdefault((o["pid"], o["line"]), {"over": None, "under": None, "name": o["name"], "team": o["team"]})
        p[o["side"]] = o["price"]
        if o.get("link"):
            p["link_" + o["side"]] = o["link"]
    return out
