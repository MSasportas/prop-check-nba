# LOG.md (NBA research, newest first)

## 2026-10-29 ~8:10 AM, Run 7 (CEO as Researcher; Matt: fewer picks a day by a calculated method, no hard limits)
Code: research/code/run7_reduce.py; the 74 scored bets: research/run7_population.json. Discovery only (Oct 25-28), nothing can pass.
- Population: every Pinnacle 2+ pt move at B/C/D passing the v2.1 base, before the v2.2 gap gate: 74 bets, 44-30, +7.53u. Live-rule
  subset (gap >= 2 pts): 40 bets, 27-13, +10.80u. By night (all / live): Oct 26 26 / 11, Oct 27 3 / 2, Oct 28 45 / 27.
- Only one score separated winners from the rest: **S1, Hard Rock's price is at or better than Pinnacle's NEW fair price (EV vs
  Pinnacle >= 0%)**. All 74: kept 16 bets 12-4 +7.12u (+44.5%), cut 58 bets 32-26 +0.41u (+0.7%), random-cut placebo p = 0.05.
  Live subset: kept 16 12-4, cut 24 15-9 +3.68u (+15.3%), placebo p = 0.16. Kept by night: Oct 26 2 of 26, Oct 27 1 of 3, Oct 28
  13 of 45 (9-4). So a quiet night leaves 1-2 picks and a busy one ~13. The edge threshold is not a smooth gradient (>= -1%: +30.9%,
  >= 0%: +44.5%, >= +1%: +35.6% on 10 bets), and the picks it cuts still made money, so on units alone cutting costs ~3.7u of
  discovery profit; the case for it is per-pick quality and theory, not units.
- S2 (Pinnacle's new fair minus Hard Rock's break-even minus 1.5 pts of noise > 0): keeps NOTHING. In plain words: almost every
  live pick is priced worse than the sharp number says is fair. They win only if Pinnacle's move keeps running (the book is still
  catching up to news), not because the price is a bargain. The 16 in S1 are the exceptions.
- No selection power: S3 (move vs others) cut groups did as well or better; S4/S4b (cell track record) and S7 (composite) came out
  INVERSE (the picks they drop did better): noise at this n; S5 overlap discount cut nothing in the live subset (no pile-ups big
  enough); S6 model (cut model 5+ pts below Pinnacle) kept 23 bets 16-7 +31.5% vs cut 17 bets 11-6 +20.9% (placebo p 0.35): a lead
  at best, same as the earlier look at 43 bets.
- Caveat in one line: 11 rules x 2 populations = ~22 looks at 4 nights; one at p = 0.05 is what chance alone gives. 13 of the 16 kept
  bets are from one night. Treat S1 as the one lead worth a forward test, not as a finding.
- Verdict: NO CANDIDATE FOR SHARP. Nothing to change live. Forward test needs no code: the shadow `solo` rows already carry
  `ev_vs_pin` for every move, so F9 scores itself from Oct 29 on.
- Next 3: (1) F9 forward (below); (2) after ~60 live bets, check whether S1 >= 0 picks beat the rest on CLV (Pinnacle's D-read fair
  vs the frozen price), which tests "still +EV after the move stopped" directly; (3) separate quiet nights from busy ones: does the
  hit rate fall on nights with 20+ picks (more moves on thin news)? A calculated version of "bad nights" without a cap.

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
