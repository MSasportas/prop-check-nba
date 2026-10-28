"""engine.py: Gap + Guard for Hard Rock rebounds, points and assists (TEAM.md section 4). Evaluates every price read, shows picks, pulls them,
locks them at tip, grades them, and builds slate.json for the page. The Record (record.py) is written only through here.

A shown pick is never silently removed: it stays, is pulled with a reason, or locks at tip. Its price is FROZEN at the read
that made it; that is the price shown, sent and graded.
"""
import math
import statistics

import common
import model
import names
import odds
import record
import teams

EPS = 1e-9
STATE_LABEL = {"early": "Early", "clear": "Injury report clear", "starters": "Starters confirmed", "locked": "Locked"}
STATE_ORDER = {"early": 0, "clear": 1, "starters": 2}
OUT_IF_BET = "Already bet? If he doesn't play it voids and refunds."


def fmt_line(x):
    return "%g" % x


def pick_id(slate, game_id, pid, line, side, market="rebounds"):
    return "%s:%s:%s:%s:%s:%s" % (slate, game_id, pid, market, fmt_line(line), side)


def pct_floor(x):
    return int(math.floor(x * 100 + 1e-7))


def pct_round(x):
    return int(math.floor(x * 100 + 0.5))


# ---------------------------------------------------------------- statuses and settled level
class Context:
    """Everything the engine reads for one slate. Built by run.py; tests build it by hand.
    games: today's games. store: stats.Store. injuries: {pid: {"status", ...}} from ESPN (may be None if ESPN failed).
    lineups: {team code: {"state", "starters": [names], "status": {name: word}}} from Rotowire (may be {}).
    people: {pid: {"pid", "name", "team"}} for every rostered player on today's teams."""

    def __init__(self, cfg, now, slate, games, store, injuries, lineups, people, season_start):
        self.cfg, self.now, self.slate = cfg, now, slate
        self.games = {g["id"]: g for g in games}
        self.store, self.injuries, self.lineups = store, injuries or {}, lineups or {}
        self.people = people or {}
        self.season_start = season_start
        self._rw_status, self._rw_starters, self.rw_unmatched = {}, {}, []
        for code, t in self.lineups.items():
            m = names.Matcher([p for p in self.people.values() if p["team"] == code])
            for nm, w in (t.get("status") or {}).items():
                p = m.find(nm)
                if p:
                    self._rw_status[p["pid"]] = w
                else:
                    self.rw_unmatched.append(nm)
            st = []
            for nm in t.get("starters") or []:
                p = m.find(nm)
                if p:
                    st.append(p["pid"])
            self._rw_starters[code] = st

    def status(self, pid):
        """Our word for a player's status. Rotowire (game-day tags: out / doubtful / questionable / probable / gtd) decides
        when it covers his team today; ESPN's injury list adds only "out" then (ESPN's day-to-day lags game-day news).
        Without Rotowire for his team, ESPN's list decides. None = healthy."""
        e = (self.injuries.get(pid) or {}).get("status")
        team = (self.people.get(pid) or {}).get("team")
        if team in self.lineups:
            w = self._rw_status.get(pid)
            if w is not None:
                return w
            return e if e in ("out", "doubtful", "questionable", "day-to-day", "gtd") else None
        return e

    def confirmed(self, code):
        return (self.lineups.get(code) or {}).get("state") == "confirmed"

    def confirmed_starter(self, pid, code):
        return self.confirmed(code) and pid in self._rw_starters.get(code, [])

    def rotation(self, code):
        """His team's top players by recent minutes (current-roster players only)."""
        n = self.cfg["eligibility"]["rotation_size"]
        mins = []
        for pid, p in self.people.items():
            if p["team"] != code:
                continue
            rows = [r for r in self.store.player_rows(pid, self.slate) if not r["dnp"] and r["min"]][-10:]
            if rows:
                mins.append((sum(r["min"] for r in rows) / len(rows), pid))
        return [pid for _, pid in sorted(mins, reverse=True)[:n]]

    def settled(self, pid, code, game):
        """early / clear / starters for this player in this game."""
        if self.confirmed(game["away"]) and self.confirmed(game["home"]):
            return "starters"
        wait = set(self.cfg["eligibility"]["wait_status"]) | {"doubtful"}
        if self.status(pid) in wait:
            return "early"
        for mate in self.rotation(code):
            if self.status(mate) in wait:
                return "early"
        return "clear"

    def eligible(self, pid, code, game):
        """None when he can be picked, else a short reason."""
        el = self.cfg["eligibility"]
        st = self.status(pid)
        if st in el["never_status"]:
            return "listed %s" % st
        if st in el["wait_status"] and not self.confirmed_starter(pid, code):
            return "listed %s: waits until cleared" % st
        rows = self.store.player_rows(pid, self.slate)
        played = [r for r in rows if not r["dnp"] and (r["min"] or 0) > 0]
        if len(played) < el["min_history"]:
            return "fewer than %d games" % el["min_history"]
        last = self.store.last_team_game(code, self.slate)
        if last and not any(r["game"] == last["game"] and not r["dnp"] and (r["min"] or 0) > 0 for r in rows) \
                and last["date"] >= self.season_start and not self.confirmed_starter(pid, code):
            return "missed his team's last game: waits for confirmed starters"
        k = el["minutes_drop_games"]
        if len(played) >= k + 10:
            recent = sum(r["min"] for r in played[-k:]) / k
            before = sum(r["min"] for r in played[-k - 10:-k]) / 10.0
            if before > 0 and recent < el["minutes_drop_ratio"] * before:
                return "minutes down (%.0f vs %.0f): role changed" % (recent, before)
        return None


# ---------------------------------------------------------------- one read -> every side, judged
def book_pairs(fetch, read_at, cfg, market="rebounds"):
    """Other books' two-sided, fresh, sane-hold prices for one market: {book: {(pid, line): (over, under)}}."""
    gg = common.gap_guard(cfg)
    out = {}
    for book, mk in (fetch.get("others") or {}).items():
        m = mk.get(market)
        if not m or odds.is_stale(m.get("last_update"), read_at, gg["book_fresh_min"]):
            continue
        bp = {}
        for k, p in odds.pairs(m.get("outcomes")).items():
            if p["over"] is None or p["under"] is None:
                continue
            h = odds.hold(p["over"], p["under"])
            if h < 0 or h > gg["book_hold_max"]:
                continue
            bp[k] = (p["over"], p["under"])
        if bp:
            out[book] = bp
    return out


def main_lines(hr_pairs):
    """Hard Rock's main line per player: the pair with both sides whose prices are closest to even."""
    best = {}
    for (pid, line), p in hr_pairs.items():
        if p["over"] is None or p["under"] is None:
            continue
        gap = abs(odds.fair_two_sided(p["over"], p["under"]) - 0.5)
        if pid not in best or gap < best[pid][0]:
            best[pid] = (gap, line, p)
    return {pid: (line, p) for pid, (_, line, p) in best.items()}


def evaluate(fetch, ctx):
    """Judge every Hard Rock side, every locked market, on one read. Returns rows (dicts), each with `market` and `why` = None when
    it passes both checks."""
    rows = []
    for market in ctx.cfg["markets"]:
        rows += evaluate_market(fetch, ctx, market)
    return rows


def evaluate_market(fetch, ctx, market):
    cfg = ctx.cfg
    gg, rd = common.gap_guard(cfg), cfg["reads"]
    at = common.parse_iso(fetch["at"])
    g = ctx.games.get(fetch["game_id"])
    hr = (fetch.get("markets") or {}).get(market)
    if not g or not hr:
        return []
    stat = cfg["markets"][market]["stat"]
    hr_stale = odds.is_stale(hr.get("last_update"), at, rd["stale_min"])
    others = book_pairs(fetch, at, cfg, market)
    rows = []
    for pid, (line, p) in main_lines(odds.pairs(hr.get("outcomes"))).items():
        team = p.get("team") or (ctx.people.get(pid) or {}).get("team")
        opp = g["home"] if team == g["away"] else g["away"]
        hold = odds.hold(p["over"], p["under"])
        mp, minfo = model.chance(ctx.store, pid, team, opp, ctx.slate, line, ctx.season_start, stat)
        for side in ("over", "under"):
            price = p[side]
            other = p["under" if side == "over" else "over"]
            r = {"pid": pid, "name": p["name"], "team": team, "opp": opp, "home": team == g["home"], "game_id": g["id"],
                 "market": market,
                 "line": line, "side": side, "price": price, "other_price": other, "read": fetch["read"], "at": fetch["at"],
                 "link": p.get("link_" + side), "hold": round(hold, 4)}
            fairs, pin = [], None
            for book, bp in others.items():
                q = bp.get((pid, line))
                if not q:
                    continue
                f = odds.fair_two_sided(q[0], q[1]) if side == "over" else odds.fair_two_sided(q[1], q[0])
                fairs.append(f)
                if book == "pinnacle":
                    pin = f
            r["n_books"] = len(fairs)
            r["market_fair"] = statistics.median(fairs) if fairs else None
            r["pin_fair"] = pin
            r["gap_ev"] = odds.ev(r["market_fair"], price) if fairs else None
            r["pin_ev"] = odds.ev(pin, price) if pin is not None else None
            ms = None
            if mp is not None:
                off = (gg.get("offsets") or {}).get(market, 0.0)
                ms = mp + off if side == "over" else 1.0 - (mp + off)
                ms = min(0.999, max(0.001, ms))
            r["model_p"] = ms
            r["mean"] = round(minfo["mean"], 2) if isinstance(minfo, dict) else None
            r["final"] = gg["market_weight"] * r["market_fair"] + gg["model_weight"] * ms \
                if (fairs and ms is not None) else None
            r["final_ev"] = odds.ev(r["final"], price) if r["final"] is not None else None
            r["why"] = why_not(r, hr_stale, hold, gg, rd, cfg, ctx, g, minfo)
            rows.append(r)
    return rows


def why_not(r, hr_stale, hold, gg, rd, cfg, ctx, g, minfo):
    """The first reason this side does not qualify, or None."""
    price = r["price"]
    if hr_stale:
        return "Hard Rock price is stale"
    if hold < rd["hold_min"] or hold > rd["hold_max"]:
        return "Hard Rock hold out of range"
    if price < cfg["customer"]["worst_price"]:
        return "price worse than %d" % cfg["customer"]["worst_price"]
    if price > gg["max_price"]:
        return "price above +%d" % gg["max_price"]
    if r["n_books"] < gg["books_min"]:
        return "only %d other books on this line" % r["n_books"]
    if gg["pin_required"] and r["pin_fair"] is None:
        return "Pinnacle not on this line"
    if r["gap_ev"] < gg["gap_ev"] - EPS:
        return "gap %+.1f%% (needs %+.1f%%)" % (100 * r["gap_ev"], 100 * gg["gap_ev"])
    if r["pin_ev"] is not None and r["pin_ev"] < gg["pin_ev_min"] - EPS:
        return "Pinnacle disagrees"
    if r["model_p"] is None:
        return "no model (%s)" % (minfo if isinstance(minfo, str) else "no data")
    if r["final_ev"] < gg["final_ev"] - EPS:
        return "model guard: final %+.1f%% (needs %+.1f%%)" % (100 * r["final_ev"], 100 * gg["final_ev"])
    el = ctx.eligible(r["pid"], r["team"], g)
    if el:
        return el
    return None


def reason_text(r):
    need = odds.break_even(r["price"])
    s = "%d other books say %.1f%%; Hard Rock's %s only needs %.1f%%." % (
        r["n_books"], 100 * r["market_fair"], common.fmt_price(r["price"]), 100 * need)
    s += (" Our model agrees (%d%%)." if r["model_p"] >= need else " Our model is lower (%d%%), but the blend still clears.") \
        % pct_round(r["model_p"])
    return s


def bet_text(side, line, noun="rebounds"):
    return "%s %s %s" % ("Over" if side == "over" else "Under", fmt_line(line), noun)


# ---------------------------------------------------------------- pull advice (copied from NHL v3.2)
def advice(code, row_now, shown_price, cfg):
    fp = common.fmt_price
    bar = common.gap_guard(cfg)["final_ev"]
    if code == "status":
        return None, OUT_IF_BET
    if code == "line_gone":
        return "Hard Rock took the line down", "Got %s? Your bet still stands." % fp(shown_price)
    if code in ("books_low", "pinnacle_gone"):
        what = "Too few other books to check it against" if code == "books_low" else "Pinnacle stopped quoting it"
        return what, "Got %s? Nothing says it got worse. Haven't bet? Skip it." % fp(shown_price)
    now_price = row_now.get("price") if row_now else None
    moved = now_price is not None and now_price != shown_price
    what = "Hard Rock moved it to %s" % fp(now_price) if moved else (
        "Pinnacle moved against it" if code == "pinnacle_flip" else "The other books moved against it")
    if not row_now or row_now.get("market_fair") is None:
        return what, None
    yours = odds.ev(common.gap_guard(cfg)["market_weight"] * row_now["market_fair"] +
                    common.gap_guard(cfg)["model_weight"] * (row_now["model_p"] if row_now.get("model_p") is not None
                                                              else row_now["market_fair"]), shown_price)
    if code == "pinnacle_flip" and row_now.get("pin_fair") is not None and odds.ev(row_now["pin_fair"], shown_price) < -EPS:
        return what, "Pinnacle, the sharpest book, leans against it even at %s. Haven't bet? Skip it." % fp(shown_price)
    if yours >= bar - EPS:
        return what, "Got %s? Still a good bet.%s" % (fp(shown_price), (" Don't bet it at %s." % fp(now_price)) if moved else "")
    if yours >= -EPS:
        return what, "Got %s? Still a small plus. Too thin to bet now." % fp(shown_price)
    return what, "Edge is gone even at %s. Haven't bet? Skip it." % fp(shown_price)


def pull_check(shown, rows_now, cfg):
    """A shown, open pick against a LATER read of its game. Returns (code, row_now) or (None, row_now)."""
    gg = common.gap_guard(cfg)
    same = [r for r in rows_now if r["pid"] == shown["pid"] and r["side"] == shown["side"]
            and r.get("market", "rebounds") == shown.get("market", "rebounds")]
    row = next((r for r in same if r["line"] == shown["line"]), None)
    if row is None:
        return "line_gone", same[0] if same else None
    if row["n_books"] < gg["books_min"]:
        return "books_low", row
    if gg["pin_required"] and row["pin_fair"] is None:
        return "pinnacle_gone", row
    if odds.ev(row["pin_fair"], shown["price"]) < gg["pin_ev_min"] - EPS:
        return "pinnacle_flip", row
    if row["price"] != shown["price"] and row["gap_ev"] is not None and row["gap_ev"] < gg["pull_ev"] - EPS:
        return "gap_gone", row
    # the guard, judged at the price Matt was shown
    if row["model_p"] is not None:
        fin = gg["market_weight"] * row["market_fair"] + gg["model_weight"] * row["model_p"]
        if odds.ev(fin, shown["price"]) < gg["final_ev"] - EPS:
            return "guard_fails", row
    return None, row


# ---------------------------------------------------------------- THE live rule since v2.0: Pinnacle moves alone
def _fair_over(q, hold_max):
    if not q or not q.get("over") or not q.get("under"):
        return None
    h = odds.hold(q["over"], q["under"])
    return odds.fair_two_sided(q["over"], q["under"]) if 0 <= h <= hold_max else None


def solo_moves(a, b, ctx):
    """Pinnacle-solo-move sides between two consecutive reads a -> b of one game (config pin_solo, TEAM.md section 4).
    For each Hard Rock main line: Pinnacle quotes that same line on both reads and its de-vigged chance moves >= min_move toward
    a side, while the median move of the other books (same line, both reads, >= others_min of them) toward that side is under
    others_max. The pick is that side at Hard Rock's price on read b. Every row is returned with `why` (None = qualifies)."""
    cfg = ctx.cfg
    ps = cfg["pin_solo"]
    g = ctx.games.get(b["game_id"])
    if not g:
        return []
    rows = []
    for market in cfg["markets"]:
        hb = (b.get("markets") or {}).get(market)
        if not hb:
            continue

        def book(f, name):
            return odds.pairs(((((f.get("others") or {}).get(name)) or {}).get(market) or {}).get("outcomes"))
        pa, pb = book(a, "pinnacle"), book(b, "pinnacle")
        ha = odds.pairs(((a.get("markets") or {}).get(market) or {}).get("outcomes"))    # Hard Rock's line on the earlier read
        hr_stale = odds.is_stale(hb.get("last_update"), common.parse_iso(b["at"]), cfg["reads"]["stale_min"])
        for pid, (line, p) in main_lines(odds.pairs(hb.get("outcomes"))).items():
            k = (pid, line)
            if k not in ha:
                continue                                   # Hard Rock must quote this same line on both reads (QA 2026-10-28)
            fa, fb = _fair_over(pa.get(k), ps["hold_max"]), _fair_over(pb.get(k), ps["hold_max"])
            if fa is None or fb is None or abs(fb - fa) < ps["min_move"] - EPS:
                continue
            side = "over" if fb > fa else "under"
            sgn = 1.0 if side == "over" else -1.0
            mv = []
            for name in (b.get("others") or {}):
                if name == "pinnacle":
                    continue
                x, y = _fair_over(book(a, name).get(k), ps["hold_max"]), _fair_over(book(b, name).get(k), ps["hold_max"])
                if x is not None and y is not None:
                    mv.append(sgn * (y - x))
            team = p.get("team") or (ctx.people.get(pid) or {}).get("team")
            price = p[side]
            pin_a = fa if side == "over" else 1 - fa
            pin_b = fb if side == "over" else 1 - fb
            r = {"rule": "pin_solo", "pid": pid, "name": p["name"], "team": team, "opp": g["home"] if team == g["away"] else g["away"],
                 "home": team == g["home"], "game_id": g["id"], "market": market, "line": line, "side": side, "price": price,
                 "read": b["read"], "at": b["at"], "prev_at": a["at"], "prev_read": a["read"],
                 "window": window_label(a["read"], b["read"]), "link": p.get("link_" + side),
                 "pin_before": round(pin_a, 4), "pin_after": round(pin_b, 4),
                 "pin_price_before": (pa.get(k) or {}).get(side), "pin_price_after": (pb.get(k) or {}).get(side),
                 "others_move": round(statistics.median(mv), 4) if mv else None, "n_others": len(mv),
                 "ev_vs_pin": round(odds.ev(pin_b, price), 4)}
            if hr_stale:
                r["why"] = "Hard Rock price is stale"
            elif len(mv) < ps["others_min"]:
                r["why"] = "only %d other books on this line" % len(mv)
            elif statistics.median(mv) >= ps["others_max"] - EPS:
                r["why"] = "the other books moved too (%+.1f pts)" % (100 * statistics.median(mv))
            elif price < cfg["customer"]["worst_price"]:
                r["why"] = "price worse than %d" % cfg["customer"]["worst_price"]
            elif price > ps["max_price"]:
                r["why"] = "price above +%d" % ps["max_price"]
            else:
                r["why"] = ctx.eligible(pid, team, g)
            rows.append(r)
    return rows


READ_LABEL = {"A": "11 AM", "B": "90 min", "C": "45 min", "D": "20 min"}
WINDOW_ORDER = ["11 AM → 90 min", "90 → 45 min", "45 → 20 min"]


def window_label(prev_read, read):
    """'11 AM → 90 min', '90 → 45 min', '45 → 20 min' (the price checks a Pinnacle move was seen between)."""
    a, b = READ_LABEL.get(prev_read, prev_read), READ_LABEL.get(read, read)
    if a.endswith(" min") and b.endswith(" min"):
        a = a[:-4]
    return "%s → %s" % (a, b)


def solo_reason(r):
    pb, pa = r.get("pin_price_before"), r.get("pin_price_after")
    held = "held" if (r.get("others_move") or 0) < 0.01 else "moved %.0f pt" % (100 * r["others_move"])
    s = "Pinnacle moved the %s from %s to %s (%.0f%% to %.0f%%); %d other books %s." % (
        r["side"], common.fmt_price(pb) if pb is not None else "?", common.fmt_price(pa) if pa is not None else "?",
        100 * r["pin_before"], 100 * r["pin_after"], r["n_others"], held)
    s += " Hard Rock price: %s." % common.fmt_price(r["price"])
    return s


def solo_pairs(fs):
    """Consecutive read pairs of one game, oldest first."""
    fs = sorted(fs, key=lambda f: f["at"])
    return list(zip(fs, fs[1:]))


# ---------------------------------------------------------------- the step
def latest_fetches(odds_doc):
    """{game_id: [fetches with any Hard Rock market, oldest first]}"""
    out = {}
    for f in (odds_doc or {}).get("fetches", []):
        if f.get("markets"):
            out.setdefault(f["game_id"], []).append(f)
    return out


def started(g, now):
    return g.get("state") in ("in", "post") or common.parse_iso(g["start"]) <= now


def safety_paused(items, cfg):
    units = sum((it["graded"] or {}).get("units") or 0 for it in items.values()
                if it["kind"] == "single" and not it["pulled"] and it["graded"])
    return units <= cfg["safety_pause"]["units"] + EPS, round(units, 2)


def step(ctx, odds_doc):
    """Make picks, pull, re-state and lock. Appends Record events. Returns (evals, items, summary)."""
    cfg, now, slate = ctx.cfg, ctx.now, ctx.slate
    gg = common.gap_guard(cfg)
    events = record.read_events()
    items = record.fold(events)
    new = []
    by_game = latest_fetches(odds_doc)
    evals = {}
    for gid, fs in by_game.items():
        evals[gid] = [(f, evaluate(f, ctx)) for f in fs]
    mine = {i: it for i, it in items.items() if it["slate"] == slate and it["kind"] == "single"}
    open_any = {i: it for i, it in items.items() if it["kind"] == "single" and record.is_open(it)}   # any slate
    paused, _ = safety_paused(items, cfg)
    active = common.gap_guard_active(cfg, slate)
    ps = cfg.get("pin_solo") or {}
    solo_on = bool(ps.get("active")) and slate >= ps.get("live_from", "9999")
    solo_rows = {}
    for gid, fs in by_game.items():
        rows_ = []
        for a, b in solo_pairs(fs):
            rows_ += solo_moves(a, b, ctx)
        solo_rows[gid] = rows_

    # 1a. new picks, the live rule since v2.0: Pinnacle moved alone on the newest pair of reads of an unstarted game
    if solo_on and not paused:
        cands = []
        for gid, fs in by_game.items():
            g = ctx.games.get(gid)
            if not g or started(g, now) or len(fs) < 2:
                continue
            b = sorted(fs, key=lambda f: f["at"])[-1]
            if b["read"] not in ps["flag_reads"] or (now - common.parse_iso(b["at"])).total_seconds() > ps["max_age_min"] * 60:
                continue                                   # never a new pick from an old read
            cands += [r for r in solo_rows.get(gid, []) if r["at"] == b["at"] and r["why"] is None]
        cands.sort(key=lambda r: (-abs(r["pin_after"] - r["pin_before"]), r["pid"], r["market"]))
        taken = {(it["shown"]["pid"], it["shown"].get("market", "rebounds")) for it in mine.values()}
        for r in cands:
            if (r["pid"], r["market"]) in taken:
                continue                                   # one pick per player per market a night
            taken.add((r["pid"], r["market"]))
            g = ctx.games[r["game_id"]]
            be = odds.break_even(r["price"])
            body = {"rule": "pin_solo", "player": r["name"], "pid": r["pid"], "team": r["team"], "opp": r["opp"], "home": r["home"],
                    "game_id": r["game_id"], "start": g["start"], "market": r["market"], "line": r["line"], "side": r["side"],
                    "bet": bet_text(r["side"], r["line"], cfg["markets"][r["market"]]["noun"]), "price": r["price"],
                    "price_at": r["at"], "read": r["read"], "p": r["pin_after"], "p_pct": pct_round(r["pin_after"]),
                    "breakeven": round(be, 4), "breakeven_pct": pct_round(be), "pin_before": r["pin_before"],
                    "pin_after": r["pin_after"], "pin_price_before": r["pin_price_before"], "pin_price_after": r["pin_price_after"],
                    "others_move": r["others_move"], "n_others": r["n_others"], "n_books": r["n_others"],
                    "ev_vs_pin": r["ev_vs_pin"], "final_ev": round(abs(r["pin_after"] - r["pin_before"]), 4),
                    "reason": solo_reason(r), "state": ctx.settled(r["pid"], r["team"], g), "link": r.get("link"),
                    "window": r["window"]}
            pid_ = pick_id(slate, r["game_id"], r["pid"], r["line"], r["side"], r["market"])
            if pid_ in items:
                continue
            new.append({"t": "shown", "id": pid_, "at": common.iso(now), "slate": slate, "kind": "single", "pick": body})

    # 1b. Gap + Guard (v1.x), off since v2.0 (gap_guard.active false): kept for its research rows
    if active and not paused:
        cands = []
        for gid, pairs in evals.items():
            g = ctx.games.get(gid)
            if not g or started(g, now):
                continue
            f, rows = pairs[-1]
            if f["read"] not in gg["flag_pulls"]:
                continue
            if (now - common.parse_iso(f["at"])).total_seconds() > gg["flag_max_age_min"] * 60:
                continue                                   # never a new pick from an old read: the next read makes it
            for r in rows:
                if r["why"] is None:
                    cands.append(r)
        cands.sort(key=lambda r: (-round(r["final_ev"], 4), r["pid"], r["side"]))
        taken = {(it["shown"]["pid"], it["shown"].get("market", "rebounds")) for it in mine.values()}
        for r in cands:
            if (r["pid"], r["market"]) in taken:
                continue                                   # one side per player per market, never a second pick on it tonight
            taken.add((r["pid"], r["market"]))
            g = ctx.games[r["game_id"]]
            state = ctx.settled(r["pid"], r["team"], g)
            body = {"player": r["name"], "pid": r["pid"], "team": r["team"], "opp": r["opp"], "home": r["home"],
                    "game_id": r["game_id"], "start": g["start"], "market": r["market"], "line": r["line"], "side": r["side"],
                    "bet": bet_text(r["side"], r["line"], cfg["markets"][r["market"]]["noun"]), "price": r["price"], "price_at": r["at"], "read": r["read"],
                    "p": round(r["final"], 4), "p_pct": pct_floor(r["final"]),
                    "breakeven": round(odds.break_even(r["price"]), 4), "breakeven_pct": pct_round(odds.break_even(r["price"])),
                    "market_fair": round(r["market_fair"], 4), "n_books": r["n_books"], "pin_fair": round(r["pin_fair"], 4),
                    "model_p": round(r["model_p"], 4), "gap_ev": round(r["gap_ev"], 4), "final_ev": round(r["final_ev"], 4),
                    "reason": reason_text(r), "state": state, "link": r.get("link")}
            pid_ = pick_id(slate, r["game_id"], r["pid"], r["line"], r["side"], r["market"])
            if pid_ in items:
                continue
            new.append({"t": "shown", "id": pid_, "at": common.iso(now), "slate": slate, "kind": "single", "pick": body})

    # 2. open picks: pulls, settled level, lock
    for i, it in open_any.items():
        sh = it["shown"]
        g = ctx.games.get(sh["game_id"])
        if g is None:
            # not on today's scoreboard (an earlier slate, or ESPN dropped it): lock it at its tip time, never leave it open
            if common.parse_iso(sh["start"]) <= now:
                new.append({"t": "locked", "id": i, "at": common.iso(now), "state": "locked"})
            continue
        if started(g, now):
            new.append({"t": "locked", "id": i, "at": common.iso(now), "state": "locked"})
            continue
        st = ctx.status(sh["pid"])
        if st in cfg["eligibility"]["never_status"] or (st in cfg["eligibility"]["wait_status"]
                                                         and not ctx.confirmed_starter(sh["pid"], sh["team"])):
            new.append({"t": "pulled", "id": i, "at": common.iso(now), "code": "status",
                        "reason": "Now listed %s" % st, "if_bet": OUT_IF_BET})
            continue
        mk = sh.get("market", "rebounds")
        later = [(f, rows) for f, rows in evals.get(sh["game_id"], [])
                 if f["at"] > sh["price_at"] and mk in (f.get("markets") or {})]   # a read without this market says nothing
        if later and sh.get("rule") == "pin_solo":
            # a Pinnacle-solo pick is a signal, not a price gap: it is pulled only if Hard Rock takes the line down
            hp = odds.pairs(later[-1][0]["markets"][mk].get("outcomes"))
            q = hp.get((sh["pid"], sh["line"]))
            if not q or q.get(sh["side"]) is None:
                what, if_bet = advice("line_gone", None, sh["price"], cfg)
                new.append({"t": "pulled", "id": i, "at": common.iso(now), "code": "line_gone", "reason": what, "if_bet": if_bet})
                continue
        elif later:
            code, row = pull_check(sh, later[-1][1], cfg)
            if code:
                what, if_bet = advice(code, row, sh["price"], cfg)
                new.append({"t": "pulled", "id": i, "at": common.iso(now), "code": code, "reason": what, "if_bet": if_bet})
                continue
        level = ctx.settled(sh["pid"], sh["team"], g)
        if level != it["state"]:
            new.append({"t": "state", "id": i, "at": common.iso(now), "state": level})
    if new:
        record.append(new)
        events += new
        items = record.fold(events)
    return evals, items, {"new": [e for e in new if e["t"] == "shown"], "pulled": [e for e in new if e["t"] == "pulled"],
                          "paused": paused, "solo_rows": solo_rows}


def grade_one(it, box_rows, cfg):
    """(result, actual text, units) for one single from its game's final box rows."""
    sh = it["shown"]
    row = next((r for r in box_rows if r["pid"] == sh["pid"]), None)
    if row is None or row["dnp"] or not row["min"]:
        return "VOID", "did not play", 0.0
    m = cfg["markets"][sh.get("market", "rebounds")]
    if row.get(m["stat"]) is None:
        return None, None, None                            # the box score lacks this stat: wait, never guess
    x = row[m["stat"]]
    if abs(x - sh["line"]) < EPS:
        res = "PUSH"
    elif (x > sh["line"]) == (sh["side"] == "over"):
        res = "W"
    else:
        res = "L"
    noun = m["noun"] if x != 1 else {"threes": "three"}.get(m["noun"], m["noun"].rstrip("s"))
    return res, "%d %s" % (x, noun), record.single_units(res, sh["price"])
