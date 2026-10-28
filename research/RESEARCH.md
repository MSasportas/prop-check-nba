# RESEARCH.md: the NBA Researcher's job and rules

Read TEAM.md first (sections 1, 4, 7), then this file, then research/HYPOTHESES.md and research/LOG.md.
Update HYPOTHESES.md and LOG.md last, then add one line to TEAM.md section 9. Modeled on Prop Check NHL's Researcher
(MSasportas/prop-check-nhl research/RESEARCH.md, read-only): same rules, adapted to NBA.

## The job (Matt, 2026-10-28: "we can't get bets, we need to figure it out")
Find a rule that beats Hard Rock (Florida) at its posted prices in Matt's locked markets: player rebounds, points, assists,
3-pointers made, MAIN line, over or under, no leg worse than -200. Every run: come up with NEW ideas (models, features,
player types, timing, news, price selection, which books define "the market"), test them honestly, and report. Don't re-run an
idea already in HYPOTHESES.md unless the change is stated and counted as a new variant. The aim is picks that WIN. A rule
that only produces volume at negative value is a fail, said plainly: the bar below never moves to make picks appear.

## Data
- **Live 2026-27 (the forward test):** `data/odds/<date>.json` (every read: Hard Rock in `markets`, 9 other books in `others`,
  incl. novig/prophetx ladders), `data/shadow/<date>.json` (every side the engine judged: price, books, market fair, Pinnacle
  fair, model p, gap EV, final EV, why), `data/state/` (injuries, Rotowire lineups, schedule).
- **Results:** grade any side yourself from box scores: `data/seed/players_<season>.json.gz` (ESPN, through the seed date) and
  `data/state/box/players_<season>.json.gz` (every final since; fields reb, pts, ast, fg3m, min, dnp). DNP = void.
- **One-time alt ladder probe:** `research/alt_probe/2026-10-26_2013.json` (3 games, main + alternate, all books).
- **No historical NBA prop odds yet.** The Odds API historical props cost 10 credits per market per game snapshot (a season,
  4 markets, one snapshot ≈ 49,000 credits). That needs a paid plan: only Matt can buy it (ask the CEO, never assume).
- **Free:** ESPN JSON (from a GitHub runner only; the chat sandbox can't reach it), Rotowire lineups page. Never pay.

## Rules (contamination = failure)
1. **Register first.** Add the hypothesis to HYPOTHESES.md (id, exact rule, data, metric, pass bar) and commit BEFORE scoring.
2. **No leakage.** Inputs only from data timestamped before the read the bet would be placed on. Bet at that read's price.
3. **Forward first.** With no historical prices, every price-based idea is judged forward on the live shadow log, nights
   counted from the night it was registered. Earlier nights may be shown as "discovery" but never count toward a pass.
4. **Pass bar (forward):** n >= 150 graded W/L bets, ROI > 0 at the posted price with 90% game-clustered bootstrap lower bound
   > 0, and mean CLV (vs the D read's market fair) > 0. Report every variant tried and a shuffle placebo.
5. **Grading** like the Record: 1u flat at the posted price, overtime counts, did not play = void, whole-number line exact = push.
6. **No product changes.** Write research/ only (never scripts/, config/, index.html, data/). Never commit a key.

## Promotion
A candidate that passes goes to the Sharp with rule, n, ROI, CI, CLV, placebo, nights. The Sharp may put it live (CEO ships
through Builder + QA) with a kill gate. Customer facts (TEAM.md section 1) only change with Matt.

## Report (LOG.md entry, newest first, every run)
Date/time, ideas tested (ids), best result per idea (n, ROI or gap stats, CI), verdict, next 3 ideas. Plain words.
If a run finds a CANDIDATE FOR SHARP, put that at the top.
