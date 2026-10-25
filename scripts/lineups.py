"""lineups.py: Rotowire's NBA lineups page (free, one read per cycle inside the lineup window).

Per team: whether the starting five is "expected" or "confirmed", the five starters, and the "may not play" list with each player's
tag (Out, Doubt, Ques, Prob, GTD, OFS). Rotowire tags are mapped to our words: out, doubtful, questionable, probable, gtd, out.
Players are named by the full name in the link title (the visible text is abbreviated). Matching to ESPN ids happens in run.py.
With PC_ESPN_FIXTURE_DIR set the page is read from rotowire_lineups.html.
"""
import html
import os
import re

import common
import teams

URL = "https://www.rotowire.com/basketball/nba-lineups.php"
SOURCE = {"ok": 0, "failed": 0}
TAG = {"out": "out", "ofs": "out", "doubt": "doubtful", "ques": "questionable", "prob": "probable", "gtd": "gtd"}


def fetch():
    fx = os.environ.get("PC_ESPN_FIXTURE_DIR")
    if fx:
        try:
            with open(os.path.join(fx, "rotowire_lineups.html"), "r", encoding="utf-8", errors="replace") as f:
                SOURCE["ok"] += 1
                return f.read()
        except OSError:
            SOURCE["failed"] += 1
            return None
    r = common.http_get(URL, timeout=20)
    if r.ok:
        SOURCE["ok"] += 1
        return r.text()
    SOURCE["failed"] += 1
    return None


_GAME = re.compile(r'<div class="lineup is-nba"')
_ABBR = re.compile(r'lineup__abbr">([A-Z]+)<')
_LIST = re.compile(r'<ul class="lineup__list is-(visit|home)">(.*?)</ul>', re.S)
_PLAYER = re.compile(r'<li class="lineup__player[^"]*"[^>]*>.*?<a title="([^"]+)"[^>]*>.*?</a>(.*?)</li>', re.S)
_INJ = re.compile(r'lineup__inj">([^<]+)<')


def parse(page):
    """-> {team code: {"state": "confirmed" | "expected" | None, "starters": [full names], "status": {full name: our word}}}"""
    out = {}
    if not page:
        return out
    parts = _GAME.split(page)[1:]
    for blk in parts:
        abbrs = _ABBR.findall(blk)[:2]
        if len(abbrs) != 2:
            continue
        codes = {"visit": teams.code(abbrs[0]), "home": teams.code(abbrs[1])}
        for side, body in _LIST.findall(blk):
            code = codes.get(side)
            if not code:
                continue
            m = re.search(r'lineup__status is-(\w+)', body)
            state = m.group(1) if m else None
            state = state if state in ("confirmed", "expected") else None
            mid = body.find("lineup__title is-middle")
            top, bottom = (body[:mid], body[mid:]) if mid >= 0 else (body, "")
            starters = [html.unescape(n) for n, _ in _PLAYER.findall(top)][:5]
            status = {}
            for n, rest in _PLAYER.findall(top) + _PLAYER.findall(bottom):
                tag = _INJ.search(rest)
                if tag:
                    w = TAG.get(tag.group(1).strip().lower())
                    if w:
                        status[html.unescape(n)] = w
            out[code] = {"state": state, "starters": starters, "status": status}
    return out
