"""teams.py: the 30 teams. Internal code = ESPN abbreviation; `show` = the tricode printed on the page; names cover the odds feed
and Rotowire spellings."""

TEAMS = [
    ("ATL", "ATL", "Atlanta Hawks"), ("BOS", "BOS", "Boston Celtics"), ("BKN", "BKN", "Brooklyn Nets"),
    ("CHA", "CHA", "Charlotte Hornets"), ("CHI", "CHI", "Chicago Bulls"), ("CLE", "CLE", "Cleveland Cavaliers"),
    ("DAL", "DAL", "Dallas Mavericks"), ("DEN", "DEN", "Denver Nuggets"), ("DET", "DET", "Detroit Pistons"),
    ("GS", "GSW", "Golden State Warriors"), ("HOU", "HOU", "Houston Rockets"), ("IND", "IND", "Indiana Pacers"),
    ("LAC", "LAC", "Los Angeles Clippers"), ("LAL", "LAL", "Los Angeles Lakers"), ("MEM", "MEM", "Memphis Grizzlies"),
    ("MIA", "MIA", "Miami Heat"), ("MIL", "MIL", "Milwaukee Bucks"), ("MIN", "MIN", "Minnesota Timberwolves"),
    ("NO", "NOP", "New Orleans Pelicans"), ("NY", "NYK", "New York Knicks"), ("OKC", "OKC", "Oklahoma City Thunder"),
    ("ORL", "ORL", "Orlando Magic"), ("PHI", "PHI", "Philadelphia 76ers"), ("PHX", "PHX", "Phoenix Suns"),
    ("POR", "POR", "Portland Trail Blazers"), ("SAC", "SAC", "Sacramento Kings"), ("SA", "SAS", "San Antonio Spurs"),
    ("TOR", "TOR", "Toronto Raptors"), ("UTAH", "UTA", "Utah Jazz"), ("WSH", "WAS", "Washington Wizards"),
]
CODES = [c for c, _, _ in TEAMS]
SHOW = {c: s for c, s, _ in TEAMS}
FULL = {c: f for c, _, f in TEAMS}
_ALIASES = {"LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "GSW": "GS", "NYK": "NY", "NOP": "NO", "NOR": "NO",
            "SAS": "SA", "UTA": "UTAH", "WAS": "WSH", "PHO": "PHX", "BRK": "BKN", "CHO": "CHA"}
_BY = {}
for c, s, f in TEAMS:
    for k in (c, s, f, f.lower()):
        _BY[k] = c
for k, c in _ALIASES.items():
    _BY[k] = c
    _BY[k.lower()] = c


def code(x):
    """Any spelling (ESPN code, tricode, full name) -> ESPN code, or None."""
    if not x:
        return None
    return _BY.get(x) or _BY.get(str(x).strip()) or _BY.get(str(x).strip().lower())


def show(c):
    return SHOW.get(c, c)
