# HYPOTHESES.md (NBA). Register before scoring. Status: open / forward / failed / candidate / live.

## Run 1 (2026-10-28, CEO as Researcher; descriptive, discovery nights Oct 25-27, nothing here can pass)
- R1 Gap distribution: Hard Rock main-line EV vs the median de-vigged fair of >= 4 books on the same line, by market, read,
  price band, side. Result: 3,318 sides, median -6.2%, 90th pct -3.8%, best +2.9%, 0 at >= +3%, 1 at >= +2%. Threes -5.8%
  median (no better). Unders -5.5% vs overs -6.9%; plus-money -100..+120 best band (median -5.7%, 6 of 612 >= 0). STATUS: done.
- R2 Market = Pinnacle alone (same line): 2,024 sides, median -6.2%, 27 >= 0, 10 >= +2%, 2 >= +3% (both points). STATUS: forward (F2).
- R3 Hard Rock stale prices (market moved >= 3 pts between consecutive reads, HR price unchanged): 1 event in 2,198 pairs; HR
  re-priced 29% of pairs. Hard Rock tracks the market on NBA props. STATUS: done (no lag edge at our read spacing).

## Forward ideas (registered 2026-10-28, scored from the night of 2026-10-28 on; discovery nights don't count)
- F1 Model disagreement: bet the side where our stat model's chance exceeds the market fair by >= X pts (X = 4, 6, 8), price
  -200..+200, at the C read. Metric: ROI at HR price, CLV. Prior from NHL: model-only rules lost (NHL TEAM.md item 20).
- F2 Pinnacle-only market: R2 rule (HR EV >= +3% vs Pinnacle fair, same line), C or D read. Metric: ROI, CLV vs D-read median.
  F2b same at >= +2% (Run 2 discovery: 6 distinct sides Oct 25-27, all unders, 5 points + 1 assists, graded 5-1; noise-size).
- F3 Injury-news reaction: when a top-7 rotation player is newly listed Out between two reads, teammates' lines on Hard Rock vs
  the other books at the next read (does HR move later than the median?). Metric: gap EV at the first read after news.
- F4 Opening read: the 11 AM A read vs the market (Run 1's best side was at A). Metric: gap distribution at A, forward.
- F5 Plus-money unders, -100..+120, best gap side per player (Run 1's least-bad band). Metric: ROI, CLV.

## Run 2 (2026-10-28 ~10:20 AM, CEO; Matt: compare books before any model)
- R4 Each single book as the only judge (latest B/C/D read, same line, -200..+200): every book median -6.1% to -6.5%; sides >= +3%:
  DraftKings 7 (0.8%), BetRivers 7, Novig 6, BetMGM 4, ProphetX 3, BetOnline 2, FanDuel 0, ESPN Bet 0, Pinnacle 0 (at the latest
  read). STATUS: done (one book's own errors, not Hard Rock's).
- F6 Pinnacle-move lag: between consecutive reads Pinnacle's fair moves >= 2 pts toward a side and Hard Rock's price does not move;
  bet that side at Hard Rock if EV vs the new Pinnacle fair >= +2%. Discovery: 9 of 1,360 pairs moved this way, 1 >= +2% (W).
  STATUS: forward from 2026-10-28.

## Run 3 (2026-10-28 ~10:30 AM, CEO; Matt: how many 'Pinnacle moves alone' examples?)
- F7 Follow Pinnacle's solo move: between two consecutive reads Pinnacle's fair moves >= 2 pts toward a side while the other books'
  median moves < 1 pt that way; bet that side at Hard Rock's price on the later read (no EV filter). Discovery Oct 25-27: 46 Pinnacle
  moves >= 2 pts, 16 alone, graded 11-5, +4.45u at HR prices; 0 of 16 were +2% vs Pinnacle's new number at HR's price.
  STATUS: forward from 2026-10-28 (discovery nights don't count). Code: research/code/run3_pin_alone.py.
- F7b Follow Pinnacle's solo LINE move (its main line changes, <= 1/3 of the other books' lines change): bet the direction it moved at
  Hard Rock's main line. Discovery: Pinnacle moved its line on only 1.7% of checks (19 times; HR 6.9%, DraftKings 12.9%); 7 solo,
  graded 3-4, -1.66u. F7 (price-only moves, same line) is the main idea. STATUS: forward from 2026-10-28.

## Run 4 (2026-10-28 ~10:45 AM, CEO; Matt: other books move the line, Hard Rock keeps its line - bet that direction?)
- F8 Follow a line move Hard Rock didn't make: between consecutive reads >= 2 of the 7 sportsbooks move their main line the same way,
  none the other way, Hard Rock keeps its line; bet the move's direction (over if lines went up) at HR's line and later price, first
  time per player/market/night. Discovery Oct 25-27: 50 bets, 19-31, -14.63u; HR odds unchanged 8-19, HR odds juiced 11-12; EV vs the
  fair at HR's line median -5.5%, 0 of 49 >= +3%. STATUS: failed in discovery (kept forward only as the mirror of F8b).
- F8b FADE that move (the opposite side at HR's line and price, same moments): discovery 31-19, +6.51u on 50. Post-hoc (found by
  flipping a loser after ~20 slices tried today), so treat as a lead only. STATUS: forward from 2026-10-28.

## Run 7 (2026-10-29 ~7:45 AM, CEO as Researcher; Matt: fewer picks a day by a CALCULATED method, no hard caps)
Matt's constraint: NO fixed limits (no max per night, per game or per player). A pick is cut only because a computed score says it
is a worse bet over the long run; a big night stays big if every pick scores well, a thin night stays thin. The goal is the same
as the judging rule: picks that hit at the posted price. Fewer is fine, worse is not.
Population: every Pinnacle >= 2 pt move at a B/C/D flag read that passed the live v2.1 base (Hard Rock same line both reads, others
< 2 pts, >= 4 other books, price -200..+200), one per player/market/night, BEFORE the v2.2 gap gate, nights Oct 25-28 (discovery
only: nothing here can pass). The live picks are the subset that also passed the v2.2 gap. Result = W/L at Hard Rock's frozen price.
Each score below is a number computed from data available at the read; the cut is "score >= bar" where the bar comes from a formula
or from the OTHER nights (leave-one-night-out), never from looking at the night being judged.
- S1 Price edge vs Pinnacle: EV of Hard Rock's price at Pinnacle's NEW fair chance (`ev_vs_pin`). Bar: >= 0%, then >= +2% (the
  break-even bars), plus the leave-night-out best bar.
- S2 Net Pinnacle edge after noise: Pinnacle's new fair minus Hard Rock's break-even, minus one standard error of a de-vigged
  two-sided price (1.5 pts, set from how much Pinnacle's fair jumps between consecutive reads when nothing happens). Keep if > 0.
- S3 Move strength: Pinnacle's move size in pts divided by the move size the other books made (bigger lead over the crowd, same
  direction). Bar by leave-night-out.
- S4 Cell track record: hit rate minus break-even of the pick's cell (market x side) on the OTHER nights, shrunk to zero with
  k = 20 bets (Bayesian shrinkage). Keep if the shrunk edge > 0. Also tested: price band (plus money / -100..-130 / -131..-200).
- S5 Overlap discount: picks in one game that ride the same game script (same team's players all overs, or both teams' unders) are one
  bet, not many. Score = S1 divided by sqrt(number of overlapping picks in that game and direction). A calculated discount, not a cap:
  a lone strong pick is untouched.
- S6 Model agreement (research only, NOT a product change; Matt said no live tag): our stat model's chance for the side is not
  below Pinnacle's new fair by more than 5 pts. Registered because the 5-pt version looked good in discovery on 43 bets; it is a lead.
- S7 Composite = the sum of the standardized S1, S3 and S4 (equal weights, no fitting). Keep the top group above the bar.
Metric per score and bar: kept n, W-L, ROI at the posted price, share of picks cut, ROI of the CUT group (must be lower than the kept
group or the score is not selecting). Plus a shuffle placebo (same count cut at random, 2,000 draws) and the leave-night-out result.
Forward: scored from the night of 2026-10-29. Pass bar as RESEARCH.md rule 4 (n >= 150 graded, kept-group ROI > 0, 90% game-clustered
bootstrap lower bound > 0, and kept ROI above the cut-group ROI).

### Run 7 results (2026-10-29 ~8:10 AM, discovery Oct 25-28, 74 bets; full write-up in LOG.md)
- S1 >= 0%: kept 16 12-4 +44.5%, cut 58 32-26 +0.7% (placebo p 0.05; live subset 0.16). STATUS: forward (F9). S1 >= +2%: 4 bets, too few.
- S2: keeps 0 of 74 (Hard Rock's price is worse than Pinnacle's new fair on nearly every pick). STATUS: done, informative only.
- S3, S5: no selection (cut groups as good or better). STATUS: failed in discovery. S4/S4b/S7: inverse. STATUS: failed.
- S6: kept 47 14.0% vs cut 3.5% on all, 31.5% vs 20.9% on live (p 0.35). STATUS: open lead, research only (no live tag, Matt 10-29).
- F9 (forward from 2026-10-29): the picks the live rule makes with ev_vs_pin >= 0 vs the rest, from the shadow `solo` rows
  (`ev_vs_pin`, graded from box scores). Metric: ROI at the posted price for each group, CLV (frozen price vs the D-read Pinnacle
  fair), games-clustered 90% bootstrap, shuffle placebo. Pass bar: RESEARCH.md rule 4 on the S1 >= 0 group AND its ROI above the
  rest. At ~4 bets a night that group reaches 150 bets in about 5 weeks (early Dec); the 2026-11-25 checkpoint gets a first read.
