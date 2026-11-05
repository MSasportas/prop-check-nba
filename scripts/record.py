"""record.py: THE RECORD.

data/record/events.jsonl is the source of truth: one JSON object per line, only ever added at the end.
  shown    a pick (or parlay) exactly as first shown on the page
  price    a new price seen for a live pick (with the chance and break-even shown with it)
  update   the shown chance or reason changed without a new price
  state    settled level changed (early -> clear -> starters)
  pulled   with the reason shown
  locked   tip-off
  graded   result, what happened, the graded price (worst price shown) and units

data/record.json and data/record/YYYY-MM.json are views rebuilt from the log (`run.py --rebuild-record`
does exactly that and nothing else). They contain no fact that is not in the log.

Units: 1 unit staked per pick and per parlay. Win = decimal(worst price shown) - 1, loss = -1,
push / void = 0. A parlay drops void and push legs and is graded on the rest.
"""
import json
import os

import common
import teams
import odds

EVENT_TYPES = ("shown", "price", "update", "state", "pulled", "locked", "graded")


class RecordError(Exception):
    pass


def events_path():
    return common.dpath("record", "events.jsonl")


def read_raw():
    try:
        with open(events_path(), "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""


def parse(raw):
    """bytes -> list of events. A line that cannot be read stops everything: the Record is never guessed."""
    out = []
    if raw and not raw.endswith(b"\n"):
        raise RecordError("events.jsonl does not end with a newline (a write was cut short)")
    for i, line in enumerate(raw.decode("utf-8").split("\n")):
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            raise RecordError("events.jsonl line %d is not valid JSON" % (i + 1))
        if not isinstance(e, dict) or e.get("t") not in EVENT_TYPES or "id" not in e or "at" not in e:
            raise RecordError("events.jsonl line %d is not a Record event" % (i + 1))
        out.append(e)
    return out


def read_events():
    return parse(read_raw())


def append(events):
    """Add events at the end. The old bytes are written back untouched, then the new lines."""
    if not events:
        return 0
    raw = read_raw()
    parse(raw)                                              # refuse to build on a damaged log
    lines = []
    for e in events:
        if e.get("t") not in EVENT_TYPES or "id" not in e or "at" not in e:
            raise RecordError("refusing to write a malformed event")
        lines.append(json.dumps(e, separators=(",", ":"), ensure_ascii=True, sort_keys=True))
    common.write_bytes(events_path(), raw + ("\n".join(lines) + "\n").encode("utf-8"))
    return len(lines)


# ---------------------------------------------------------------- folding the log
def fold(events):
    """Replay the log. Returns {id: item}. An item is everything known about one pick or parlay."""
    items = {}
    for e in events:
        t, i = e["t"], e["id"]
        if t == "shown":
            if i in items:
                continue                                    # a second "shown" for the same id is ignored
            body = e.get("pick") or e.get("parlay") or {}
            items[i] = {"id": i, "kind": e.get("kind", "single"), "slate": e.get("slate"), "shown_at": e["at"],
                        "shown": body,
                        "prices": [{"at": body.get("price_at") or e["at"], "price": body.get("price"),
                                    "legs": body.get("leg_prices")}],
                        "p_pct": body.get("p_pct"), "breakeven_pct": body.get("breakeven_pct"),
                        "p": body.get("p"), "breakeven": body.get("breakeven"), "reason": body.get("reason"),
                        "fair": body.get("fair"),
                        "state": body.get("state"), "states": [{"at": e["at"], "state": body.get("state")}],
                        "pulled": None, "locked_at": None, "graded": None}
            continue
        it = items.get(i)
        if it is None:
            continue
        if t == "price":
            it["prices"].append({"at": e.get("price_at") or e["at"], "price": e["price"], "legs": e.get("leg_prices")})
            for k in ("p", "breakeven", "reason", "fair", "p_pct", "breakeven_pct"):
                if e.get(k) is not None:
                    it[k] = e[k]
        elif t == "update":
            for k in ("p", "breakeven", "reason", "fair", "p_pct", "breakeven_pct"):
                if e.get(k) is not None:
                    it[k] = e[k]
        elif t == "state":
            it["state"] = e["state"]
            it["states"].append({"at": e["at"], "state": e["state"]})
            if e.get("reason") is not None:
                it["reason"] = e["reason"]
        elif t == "pulled":
            if it["pulled"] is None and it["locked_at"] is None:
                it["pulled"] = {"at": e["at"], "reason": e.get("reason"), "code": e.get("code"), "if_bet": e.get("if_bet")}
        elif t == "locked":
            if it["locked_at"] is None:
                it["locked_at"] = e["at"]
                it["state"] = e.get("state", it["state"])
                it["states"].append({"at": e["at"], "state": it["state"]})
        elif t == "graded":
            if it["graded"] is None:
                it["graded"] = {k: e.get(k) for k in ("at", "result", "actual", "actual_text", "price", "units", "legs", "note")}
    return items


def worst_price(item):
    """The lowest-paying price ever shown for this pick."""
    return min((p["price"] for p in item["prices"] if p["price"] is not None), key=odds.decimal)


def parlay_snapshot(item):
    """The parlay price snapshot it is graded at: the WORST parlay price shown (lowest payout), with the leg
    prices it was made of. None for a parlay recorded before snapshots were stored."""
    snaps = [p for p in item["prices"] if p.get("legs") and p["price"] is not None]
    return min(snaps, key=lambda p: odds.decimal(p["price"])) if snaps else None


def first_price(item):
    return item["prices"][0]["price"]


def last_price(item):
    return item["prices"][-1]["price"]


def is_open(item):
    """Still bettable: not pulled, not locked, not graded."""
    return item["pulled"] is None and item["locked_at"] is None and item["graded"] is None


# ---------------------------------------------------------------- grading arithmetic
def single_units(result, price, stake=1):
    if result == "W":
        return round((odds.decimal(price) - 1.0) * stake, 4)
    if result == "L":
        return -float(stake)
    return 0.0


def grade_parlay(legs, stake=1):
    """legs: [(result, graded price)] for every leg. Returns (result, price, units).
    A void or push leg drops out. Any losing leg loses. No legs left = void."""
    alive = [(r, p) for r, p in legs if r in ("W", "L")]
    if any(r is None for r, _ in legs):
        return None, None, None
    if not alive:
        return "VOID", None, 0.0
    dec = 1.0
    for _, p in alive:
        dec *= odds.decimal(p)
    price = odds.american(dec)
    if any(r == "L" for r, _ in alive):
        return "L", price, -float(stake)
    return "W", price, round((odds.decimal(price) - 1.0) * stake, 4)    # paid at the price as shown (whole number)


# ---------------------------------------------------------------- views for the page
def _entry(it, items):
    sh, g = it["shown"], it["graded"]
    if it["kind"] == "parlay":
        legs = [_entry(items[l], items) for l in sh.get("legs", []) if l in items]
        e = {"id": it["id"], "kind": "parlay", "player": "Parlay", "bet": "%d legs" % len(sh.get("legs", [])),
             "price": (g or {}).get("price") if g else last_price(it), "first_price": first_price(it),
             "result": (g or {}).get("result"), "actual": (g or {}).get("actual_text"),
             "units": (g or {}).get("units"), "pulled": _pulled(it), "legs": legs}
        return e
    return {"id": it["id"], "kind": "single", "player": sh.get("player"), "bet": sh.get("bet"),
            "market": sh.get("market"), "team": teams.show(sh.get("team")),
            "game": "%s at %s" % tuple(teams.show(x) for x in ((sh.get("team"), sh.get("opp")) if not sh.get("home")
                                                              else (sh.get("opp"), sh.get("team")))),
            "price": (g or {}).get("price") if g else worst_price(it),
            "first_price": first_price(it), "last_price": last_price(it),
            "prices": [{"price": p["price"], "at": p["at"]} for p in it["prices"]],
            "result": (g or {}).get("result"), "actual": (g or {}).get("actual_text"),
            "units": (g or {}).get("units"), "pulled": _pulled(it), "legs": [], "window": window_of(sh),
            "book": sh.get("book") or "hardrock",
            "under_fair": under_fair(sh)}


def under_fair(sh):
    """v2.3 (Matt, 2026-10-29): a Pinnacle-rule pick shown while Hard Rock's price was worse than Pinnacle's FAIR price
    (ev_vs_pin < 0) is still on the Record and in the log exactly as shown, but is not counted in the scoreboard."""
    ev = sh.get("ev_vs_pin")
    return sh.get("rule") == "pin_solo" and isinstance(ev, (int, float)) and ev < 0


_WIN = ["11 AM → 90 min", "90 → 45 min", "45 → 20 min"]
_WIN_BY_READ = {"B": _WIN[0], "C": _WIN[1], "D": _WIN[2]}


def window_of(sh):
    """The price-check window of a Pinnacle pick. Picks shown before the window was stored (2026-10-28 evening) get it from
    their flag read (B / C / D after the read before it); the log itself is never edited."""
    if sh.get("window"):
        return sh["window"]
    return _WIN_BY_READ.get(sh.get("read")) if sh.get("rule") == "pin_solo" else None


def _pulled(it):
    return {"at": it["pulled"]["at"], "reason": it["pulled"]["reason"], "code": it["pulled"].get("code")} if it["pulled"] else None


def withdrawn(e):
    """A pick our own rule change took down (pulled, code rule_change, 2026-10-28): never shown as a bet, not on the Record view."""
    return bool(e.get("pulled")) and (e["pulled"] or {}).get("code") == "rule_change"


def counts(e):
    """THE set the Record counts (headline, rows, cuts, calendar, nights; the safety stop reads the same). Since 2026-11-04
    (Matt): a pick pulled after it was shown (TOO LATE: line moved or taken down, injury news) counts like any other pick,
    graded at its posted price. Out: picks under Pinnacle's fair price (v2.3) and rule_change withdrawals. A scratch (Out)
    grades VOID, and voids are 0 units outside W-L."""
    return e["kind"] == "single" and not e.get("under_fair") and not withdrawn(e)


def headline_units(items, cfg):
    """Units of exactly what the Record headline counts (live picks + replay bets), for engine.safety_paused."""
    live = [_entry(it, items) for it in items.values() if it["kind"] == "single"]
    rep = [e for es in _replay_entries(cfg).values() for e in es]
    return round(sum(e["units"] or 0 for e in live + rep if counts(e) and e["result"]), 2)


def _row(key, label, entries, needed_of):
    w = sum(1 for e in entries if e["result"] == "W")
    l = sum(1 for e in entries if e["result"] == "L")
    need = [needed_of(e) for e in entries if e["result"] in ("W", "L") and e["price"] is not None]
    return {"key": key, "label": label, "w": w, "l": l,
            "push": sum(1 for e in entries if e["result"] == "PUSH"),
            "void": sum(1 for e in entries if e["result"] == "VOID"),
            "units": round(sum(e["units"] or 0 for e in entries if e["result"]), 2),
            "hit_rate": round(w / (w + l), 4) if (w + l) else None,
            "needed": round(sum(need) / len(need), 4) if need else None, "n": w + l}


def _replay_entries(cfg):
    """Replay bets (the same rule run on price checks saved before it went live) as Record entries, tagged replay (Matt, 2026-10-30:
    the Record tracks the whole strategy, live or not). Read from data/replay/pin_solo.json (scripts/replay.py)."""
    doc = common.read_json(common.dpath("replay", "pin_solo.json")) or {}
    out = {}
    for n in doc.get("nights") or []:
        for i, b in enumerate(n.get("bets") or []):
            away, home = (b["opp"], b["team"]) if b.get("home") else (b["team"], b["opp"])
            noun = (cfg["markets"].get(b["market"]) or {}).get("noun", "")
            out.setdefault(n["date"], []).append({
                "id": "replay:%s:%s:%s:%s:%s" % (n["date"], b["player"], b["market"], b["line"], b["side"]), "kind": "single",
                "player": b["player"], "bet": b["bet"], "market": b["market"], "team": b["team"],
                "game": "%s at %s" % (away, home), "price": b["price"], "first_price": b["price"], "last_price": b["price"],
                "prices": [], "result": b.get("result"), "actual": b.get("actual"), "units": b.get("units"), "pulled": None,
                "legs": [], "window": b.get("window"), "replay": True, "under_fair": False, "_at": b.get("at") or ""})
    return out


def _merge_replay(nights, cfg):
    by = {n["date"]: n for n in nights}
    for d, es in _replay_entries(cfg).items():
        n = by.get(d)
        if n is None:
            n = by[d] = {"date": d, "graded": True, "w": 0, "l": 0, "units": 0.0, "entries": []}
        n["entries"] = sorted(n["entries"] + [{k: v for k, v in e.items() if k != "_at"} for e in es], key=lambda e: 0)
        counted = [e for e in n["entries"] if e["kind"] == "single"]
        n["graded"] = all(e["result"] is not None for e in n["entries"])
        n["w"] = sum(1 for e in counted if e["result"] == "W")
        n["l"] = sum(1 for e in counted if e["result"] == "L")
        n["units"] = round(sum(e["units"] or 0 for e in counted), 2)
    return [by[d] for d in sorted(by, reverse=True)]


# ---------------------------------------------------------------- cuts and calendar (page views only, Matt 2026-11-04)
# They count exactly what the headline counts (the same `singles`); a fact a pick lacks keeps it out of that one cut only.
EDGE_BANDS = [("e0", "0 to 2%", lambda f: 0 <= f["edge"] < 0.02),
              ("e2", "2 to 5%", lambda f: 0.02 <= f["edge"] < 0.05),
              ("e5", "5% or more", lambda f: f["edge"] >= 0.05)]
SETTLED_BANDS = [("early", "Early", lambda f: f["settled"] == "early"),
                 ("clear", "Injury report clear", lambda f: f["settled"] == "clear"),
                 ("starters", "Starters confirmed", lambda f: f["settled"] == "starters")]
PRICE_BANDS = [("plus", "Plus money", lambda f: f["price"] >= 100),
               ("fav", "-100 to -150", lambda f: -150 <= f["price"] <= -100),
               ("fav_big", "-151 to -200", lambda f: -200 <= f["price"] < -150)]


def _facts_live(it, e):
    sh = it["shown"]
    ev = sh.get("ev_vs_pin")
    return {"market": sh.get("market", "rebounds"), "edge": ev if isinstance(ev, (int, float)) else None,
            "settled": (it["states"][0] or {}).get("state") if it.get("states") else sh.get("state"),
            "price": e["price"] if isinstance(e["price"], (int, float)) else None,
            "side": _side(sh.get("side") or e.get("bet"))}


def _side(v):
    v = str(v or "").strip().lower()
    return "over" if v.startswith("over") else "under" if v.startswith("under") else None


def _replay_facts(cfg):
    """Replay bets: the edge is Pinnacle's new chance x Hard Rock's payout - 1 (the engine's own ev_vs_pin); no settled level."""
    doc = common.read_json(common.dpath("replay", "pin_solo.json")) or {}
    out = {}
    for n in doc.get("nights") or []:
        for b in n.get("bets") or []:
            i = "replay:%s:%s:%s:%s:%s" % (n["date"], b["player"], b["market"], b["line"], b["side"])
            ev = b.get("ev_vs_pin")
            if ev is None and isinstance(b.get("pin_after"), (int, float)) and isinstance(b.get("price"), (int, float)):
                ev = round(odds.ev(b["pin_after"], b["price"]), 4)
            out[i] = {"market": b.get("market"), "edge": ev, "settled": None,
                      "price": b["price"] if isinstance(b.get("price"), (int, float)) else None,
                      "side": _side(b.get("side"))}
    return out


def cuts(rows, need, cfg):
    """rows: [(entry, facts)] for every counted single. -> [{key, label, note, rows}]; a band with nothing graded is left out."""
    labels = {k: m["label"] for k, m in cfg["markets"].items()}
    market_bands = [(k, labels[k], (lambda k: lambda f: f["market"] == k)(k)) for k in cfg["markets"]]
    out = []
    for key, label, note, bands, has in (
            ("market", "By market", None, market_bands, lambda f: f["market"] is not None),
            ("side", "Over vs under", None, [("over", "Over", lambda f: f["side"] == "over"),
                                             ("under", "Under", lambda f: f["side"] == "under")],
             lambda f: f.get("side") is not None),
            ("edge", "By edge", "Hard Rock's price vs Pinnacle's fair price, when shown", EDGE_BANDS,
             lambda f: f["edge"] is not None),
            ("settled", "By how settled when shown", "Replay bets have no settled level, so they are not in this cut",
             SETTLED_BANDS, lambda f: f["settled"] is not None),
            ("price", "By price", "Hard Rock price as graded", PRICE_BANDS, lambda f: f["price"] is not None)):
        cut_rows = []
        for bk, bl, test in bands:
            sub = [e for e, f in rows if has(f) and test(f)]
            if any(e["result"] in ("W", "L", "PUSH", "VOID") for e in sub):
                row = _row(bk, bl, sub, need)
                row["ids"] = [e["id"] for e in sub if e.get("id")]          # the page opens a row to these picks (2026-11-05)
                cut_rows.append(row)
        if cut_rows:
            out.append({"key": key, "label": label, "note": note, "rows": cut_rows})
    return out


def days_view(nights):
    """One row per night (every month) for the page's calendar, counting what the headline counts."""
    out = []
    for n in nights:
        s = [e for e in n["entries"] if counts(e)]
        out.append({"date": n["date"], "w": sum(1 for e in s if e["result"] == "W"), "l": sum(1 for e in s if e["result"] == "L"),
                    "push": sum(1 for e in s if e["result"] == "PUSH"), "void": sum(1 for e in s if e["result"] == "VOID"),
                    "units": round(sum(e["units"] or 0 for e in s if e["result"]), 2), "n": len(s),
                    "graded": all(e["result"] is not None for e in s)})
    return out


def build_views(events, cfg):
    """-> (record.json dict, {"2026-10": month dict, ...})."""
    items = fold(events)
    labels = {k: m["label"] for k, m in cfg["markets"].items()}
    by_night = {}
    for it in items.values():
        by_night.setdefault(it["slate"], []).append(it)
    nights = []
    for d in sorted(by_night, reverse=True):
        its = sorted(by_night[d], key=lambda x: (x["kind"] != "single", x["shown"].get("rank") or 999, x["shown_at"], x["id"]))
        # v2.3 (Matt, 2026-10-30): the page's Record is the STRATEGY's record: picks at or better than Pinnacle's fair price.
        # Picks under fair price and rule_change withdrawals are not shown here (they stay in data/record/events.jsonl, untouched).
        # Since 2026-11-04 (Matt) a pick pulled after it was shown counts like any other pick (`pulled` kept on the entry, no
        # separate count).
        entries = [e for e in (_entry(x, items) for x in its) if not withdrawn(e) and not e.get("under_fair")]
        if not entries:
            continue
        counted = [e for e in entries if counts(e)]
        nights.append({"date": d, "graded": all(e["result"] is not None for e in entries),
                       "w": sum(1 for e in counted if e["result"] == "W"),
                       "l": sum(1 for e in counted if e["result"] == "L"),
                       "units": round(sum(e["units"] or 0 for e in counted), 2), "entries": entries})
    nights = _merge_replay(nights, cfg)
    every = [e for n in nights for e in n["entries"]]
    need = lambda e: odds.break_even(e["price"])
    singles = [e for e in every if counts(e)]
    rows = []
    for key in cfg["markets"]:
        sub = [e for e in singles if e.get("market") == key]
        if any(e["result"] for e in sub):
            rows.append(_row(key, labels[key], sub, need))
    wins = sorted({e["window"] for e in singles if e.get("window")}, key=lambda w: (_WIN.index(w) if w in _WIN else 9, w))
    for w in wins:
        sub = [e for e in singles if e.get("window") == w]
        if any(e["result"] for e in sub):
            rows.append(_row("window:" + w, "Window " + w, sub, need))
    # v2.5 (Matt, 2026-11-03): picks can be at Hard Rock or DraftKings; one row per book once a DraftKings pick is graded
    if any(e.get("book") == "draftkings" and e["result"] for e in singles):
        for bk, lab in (("hardrock", "Hard Rock"), ("draftkings", "DraftKings")):
            sub = [e for e in singles if (e.get("book") or "hardrock") == bk]
            if any(e["result"] for e in sub):
                rows.append(_row("book:" + bk, "Book " + lab, sub, need))
    par = [e for e in every if e["kind"] == "parlay" and not withdrawn(e)]
    if any(e["result"] for e in par):
        rows.append(_row("parlays", "Parlays", par, need))
    head = _row("headline", "Singles", singles, need)
    head.pop("key"); head.pop("label")
    keep = cfg["ui"]["record_nights"]
    months = {}
    for n in nights[keep:]:
        months.setdefault(n["date"][:7], {"nights": []})["nights"].append(n)
    rf = _replay_facts(cfg)
    facts = [(e, _facts_live(items[e["id"]], e) if e["id"] in items else rf.get(e["id"])) for e in singles]
    rec = {"generated_at": events[-1]["at"] if events else None,
           "summary": {"headline": head, "rows": rows, "cuts": cuts([x for x in facts if x[1]], need, cfg),
                       "days": days_view(nights)},
           "nights": nights[:keep],
           "older": ["record/%s.json" % m for m in sorted(months, reverse=True)]}
    return rec, months


def write_views(cfg, events=None):
    """Rebuild record.json and the month files from the log. Writes only files whose content changed."""
    events = read_events() if events is None else events
    rec, months = build_views(events, cfg)
    changed = []
    targets = [(common.dpath("record.json"), rec)] + \
              [(common.dpath("record", "%s.json" % m), doc) for m, doc in months.items()]
    for path, doc in targets:
        if common.read_json(path) != doc:
            common.write_json(path, doc)
            changed.append(os.path.basename(path))
    return changed
