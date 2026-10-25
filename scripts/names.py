"""names.py: match a name from the odds feed or Rotowire to an ESPN player id, within the two teams of one game only.

Rules (never guessed): exact normalized full name; else the same last name + first initial when exactly one player on those teams
fits. Normalizing drops accents, dots, apostrophes, hyphens-as-spaces, and suffixes Jr / Sr / II / III / IV.
"""
import re
import unicodedata

_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
_FIRST_ALIAS = {"nicolas": "nic", "cameron": "cam", "kenyon": "kenyon", "herbert": "herb", "moe": "moritz"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace(".", "").replace("'", "").replace("-", " ")
    s = _SUFFIX.sub(" ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return " ".join(s.split())


class Matcher:
    """people: [{"pid", "name", "team"}] for the two teams of a game."""

    def __init__(self, people):
        self.people = people
        self.full = {}
        self.initial = {}
        for p in people:
            n = norm(p["name"])
            self.full.setdefault(n, []).append(p)
            parts = n.split()
            if len(parts) >= 2:
                self.initial.setdefault((parts[0][0], parts[-1]), []).append(p)

    def find(self, name):
        n = norm(name)
        hits = self.full.get(n, [])
        if len(hits) == 1:
            return hits[0]
        parts = n.split()
        if len(parts) >= 2:
            first = _FIRST_ALIAS.get(parts[0], parts[0])
            hits = self.full.get(" ".join([first] + parts[1:]), [])
            if len(hits) == 1:
                return hits[0]
            hits = self.initial.get((parts[0][0], parts[-1]), [])
            if len(hits) == 1:
                return hits[0]
        return None

    __call__ = find
