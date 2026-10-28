# LOG.md (NBA research, newest first)

## 2026-10-28 ~10:55 AM, Run 5 (CEO; Matt: Pinnacle as judge on alt lines)
- Pinnacle posts NO alt lines, so each HR alt rung was judged against Pinnacle's main line converted with our stat distributions (an
  estimate). One snapshot, 3 games (Oct 26 alt probe). HR alt overs -200..+200: n 102, median -10.8%, 5 >= +3% (all points), graded
  42-60 -16.9u. HR overs on Pinnacle's exact line: median -7.0%, 0 >= +3%. All 35 alt rungs >= +3% vs converted Pinnacle: 24-11 but
  -3.8u (mostly -200 to -550 favorites, outside Matt's -200 limit; low points rungs are where the conversion is least reliable).
  Verdict: no case for alt lines. Testing more needs nightly alt pulls (+4 credits a game per read), not in the November budget.

## 2026-10-28 ~10:45 AM, Run 4 (CEO)
- F8 (bet toward other books' line move when HR keeps its line): 19-31, -14.6u on 50 in discovery. Price check agrees: HR's price at its
  old line was already ~5.5% worse than the fair price at that line (HR re-juices instead of moving the line). F8b fade: 31-19, +6.5u,
  post-hoc. Today's runs tried ~20 slices on 3 nights; expect 1-2 to look good by chance. Forward nights decide.

## 2026-10-28 ~10:30 AM, Run 3 (CEO)
- Pinnacle moved >= 2 pts between reads 46 times in 3 nights; 16 of those the other books didn't follow (median < 1 pt). Betting the
  side Pinnacle moved toward, at Hard Rock: 11-5, +4.45u. 16 bets = could easily be luck (11-5 vs ~50% is p ~0.1). Registered F7 forward.

## 2026-10-28 ~10:20 AM, Run 2 (CEO; Matt: find it by comparing books before any model)
- Pinnacle alone: 6 distinct sides >= +2% in 3 nights (only 1 >= +3%, Reaves U23.5 pts -120, lost), all unders, graded 5-1.
  Against the 8-9 book median the same sides were -0.6% to -4.4%: Pinnacle was the outlier, not Hard Rock.
- Each book alone as the judge: <= 0.9% of sides clear +3%, every book's median -6.1 to -6.5%. No single book is a better judge.
- Pinnacle moves, Hard Rock doesn't: 9 of 1,360 read pairs; 1 cleared +2% (Collins U15.5, W).
Verdict: book comparison finds nothing bettable yet; F2b and F6 tracked forward. Code: research/code/run2_books.py.

## 2026-10-28 ~10:30 AM, Run 1 (CEO as Researcher, set up the role)
Matt: 0 picks in 2+ full nights, "figure it out". Data: shadow log Oct 25-27 (3,318 sides with >= 4 books on Hard Rock's line).
- R1: Hard Rock sits a steady ~6% below the market on every market, read, band and side. Best side +2.9% (bar +3%). Zero
  qualifying. Threes are not softer (median -5.8%).
- R2: vs Pinnacle alone, 2 points sides cleared +3% in 3 nights (median still -6.2%).
- R3: Hard Rock re-prices with the market (1 stale event in 2,198 pairs): no "slow book" edge at 20-45 min spacing.
Verdict: the main-line Gap + Guard rule has nothing to bet at Hard Rock NBA. Not a bug: Hard Rock's NBA props are priced at
market with ~6-7% hold. Next: F1 model disagreement, F2 Pinnacle-only, F3 injury-news reaction (all forward from tonight).
Blocker for anything faster than weeks: no historical NBA prop prices (paid; Matt's call).
