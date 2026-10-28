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
