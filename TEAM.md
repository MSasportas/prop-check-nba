# TEAM.md: Prop Check NBA operating doc

Read this first in every session. Update it last. Every chat in the NBA project starts by attaching
MSasportas/prop-check-nba (add_repo, push access), cloning it and reading this file.

Live page: https://msasportas.github.io/prop-check-nba/ · Repo: MSasportas/prop-check-nba (public)
Sister company of Prop Check NHL (MSasportas/prop-check-nhl): own CEO, team, repo, Record and odds key pool. The NHL repo is the
template and is READ ONLY from here. Never push to it.

## 1. The product
Every NBA game day: every rebounds, points, assists and 3-pointers-made leg that qualifies at a real Hard Rock (`hardrockbet`) price, ranked best first, each with
the price, our chance vs the price's break-even and a one-line plain reason. The page updates through the day; each pick shows how
settled it is (Early / Injury report clear / Starters confirmed, then Locked) and pulled picks stay visible with the reason and what it
means if Matt already bet. Dark, phone first (~380px). The Record is the scoreboard. Parlays are not offered (Matt, setup).

**Customer facts (fixed; locked in the setup interview 2026-10-25, Matt):**
| Fact | Locked value |
|---|---|
| Book | Hard Rock Florida only. A pick needs a real Hard Rock number |
| Markets | **Player rebounds, points, assists and 3-pointers made (points + assists added 2026-10-25 8:22 PM; threes 2026-10-26 11:21 PM, Matt). Main line only (no alt ladders). Over and under.** Everything else is out |
| Price | No single leg worse than -200. Plus money is fine |
| Parlays | **Off** |
| When Matt bets | **The last hour before tip** (the page must be sharpest then) |
| Games | Regular season only (NBA Cup games count as regular season; play-in and playoffs are not covered) |
| Alerts | Discord, a NEW NBA channel (secret `DISCORD_WEBHOOK`) |

**Fixed:** the Record. Every pick exactly as shown, graded after the game at the posted price, append-only, pulled picks kept and marked.
Nothing edited or dropped. It is the only reporting Matt wants.
**Come to Matt only for:** more odds keys, paying for something, a GitHub setting we can't reach. Exact taps, one short message.

## 2. How we are judged
1. Picks hit, at the price posted (a -200 leg must hit 66.7%+). An empty night beats picks that miss.
2. Always current; anything missing or stale is said plainly on the page.
3. A usable set of picks most nights.
4. Readable on a phone in seconds.

## 3. The team (subagents run by the CEO; any chat in the project is the CEO)
Sharp (betting method, final call) · Data Scientist (data, model, samples, judging the Record) · **Researcher (2026-10-28, Matt: find
an honest way to get winning bets; rules in research/RESEARCH.md; writes research/ only)** · UX (page) · Builder (all code) ·
QA (tests every change before it goes live, real browser at 380px, hasn't seen the build).
Rule changes: the Data Scientist names the sample first; the Sharp decides; log it in section 8. Customer facts (section 1) never change
without Matt.

## 4. Current rules (v1.0, 2026-10-25). Source of truth: `config/rules.json` (`gap_guard`)
ONE rule, copied from NHL v3.3: **Gap + Guard.** Hard Rock's price must beat the other books' middle price by a margin (the gap), and our
model must not disagree (the guard). The model can only veto, never create. All EV% = fair probability x Hard Rock decimal payout - 1, on
unrounded numbers; every threshold is inclusive. Why this and not a model-only rule: NHL's model-only rules failed a pre-registered
season backtest (NHL TEAM.md item 20); a single-player model does not beat a ~7% hold book. The gap is the only angle with a mechanism.

| Area | Rule |
|---|---|
| Markets | Hard Rock `player_rebounds`, `player_points`, `player_assists`, `player_threes`: the main line per player (the two-sided pair closest to even), over and under. Alt lines are never used |
| Step 1: the gap | All of: Hard Rock EV vs the market fair >= **+3.0%**; >= **4 other books** priced the same player, same line, both sides, fresh, hold 0-15%; **market fair = median** of the books' proportionally de-vigged chance (even count: mean of the middle two); **Pinnacle present** with both sides and Pinnacle-fair EV on Hard Rock's price >= 0.0%; Hard Rock price **-200 to +200** |
| Step 2: the guard | final = 0.8 x market fair + 0.2 x (model chance + offset). Passes iff final EV >= **+2.0%**. No model for the player = no pick. Offset frozen (section 7 item 3) |
| Which reads can pick | B (90 min), C (45 min) and D (20 min before tip) reads that carry other books. The morning A read is a baseline only |
| The pick | The first passing read makes the pick and **freezes its price**. That price is shown, sent to Discord and graded: flat 1 unit. Later prices never change it |
| Eligibility | >= 10 games of history (2025-26 + 2026-27 box scores); listed **Out or Doubtful -> never**; **Questionable / Day-to-day / GTD -> no new pick** until he drops off the report or is in a confirmed starting five; missed his team's last game -> waits for confirmed starters (and must start); minutes last 3 games < 60% of his recent average -> no pick (role or restriction changed) |
| Settled chip | **Early** (he or someone in his team's top 7 by recent minutes is Doubtful / Questionable / GTD) -> **Injury report clear** (none of them is; Out and Probable are settled) -> **Starters confirmed** (Rotowire shows both teams' starting fives as confirmed) -> **Locked** at tip |
| Pulls | Later reads only PULL: Hard Rock's price changed and step-1 EV < **+1.5%**; fewer than 4 books; Pinnacle gone or sign flipped; step 2 fails; line removed; player listed Out, Doubtful, Questionable or GTD after the pick, unless he is in a confirmed starting five (every run). Teammate news does not pull by itself: the next read re-prices it. Pulled picks stay on the page and in the Record, graded at the frozen price, counted under "Pulled". **Every pull says what happened and what it means if Matt already bet.** No pulls after tip. Once the D read is done only an injury pull can happen ("Price final") |
| Caps | **None per game or per night (Matt, 2026-10-25: "no limit per game or anything")**: every qualifying leg is shown, ranked by final EV. Only 1 side per player per market (both sides of one line can't both be bets); one player can have a rebounds, a points, an assists and a threes pick |
| Parlays | Off (customer fact) |
| Grading | When ESPN marks the game final. Overtime counts. Did not play = void. Graded at the frozen price, flat 1 unit |
| Odds reads | A 11 AM (or 3h before the first tip), B 90 min, C 45 min, D 20 min before each game. 4 markets = 4 credits a read (`ops.cost_per_read`). Reads a game = allowance / 4, at most 4; priority when credits are short: C, B, D, A |
| Safety | New picks stop by themselves if the Record reaches **-10 units** (`safety_pause`), with the reason on the page. Never silent |

## 5. How it runs
- **Data (all free, no keys):** ESPN public JSON (`site.api.espn.com`): scoreboard (games, tip times, finals), summary (box scores for
  grading and the stats store), league injuries (status per player). Starting lineups: see section 7 item 2. The build sandbox cannot reach
  ESPN; only the GitHub runner can (checked 2026-10-20 and by the setup probe). cdn.nba.com and stats.nba.com block GitHub runners.
  **Game-day status and starters: Rotowire's NBA lineups page** (`scripts/lineups.py`, free HTML, one read per cycle from 3h before a
  tip): per team Expected/Confirmed starting five and tags Out / Doubt / Ques / Prob / GTD. Rotowire decides statuses for a team it
  covers today; ESPN's list adds only Out there (its Day-To-Day lags). Without Rotowire, ESPN decides. The official NBA injury report
  PDF (ak-static.cms.nba.com) is reachable from the runner but not parsed yet (gap 7). Probe samples: `probe/` (also the test fixtures).
- **Stats store:** `data/seed/players_<season>.json.gz` + `teams_<season>.json.gz` (2025-26 full season and 2026-27 so far, from the
  one-time `setup` workflow), then every final game is added from its box score.
- `scripts/run.py` is the only entry point; each run decides what is due: schedule, injuries, lineups, odds reads, evaluate, lock at tip,
  grade finals, rebuild `data/record.json`, write `data/slate.json` and `data/status.json`. Safe to run twice; writes are atomic. Stdlib
  Python 3.12.
- **Timer (copied from NHL):** GitHub cron barely fires, so `.github/workflows/run.yml` is a self-dispatching chain: each run loops
  `scripts/loop.sh` ~50 min (`scripts/cycle.sh` every 10 min 10 AM-2 AM ET, every 30 min otherwise) then starts the next run via
  workflow_dispatch. Hourly cron and any push to scripts/, config/ or .github/workflows/ (re)start it. Off switch: commit `config/stop_timer`.
- **Is it alive?** `git pull` and read `data/status.json`: `finished_at` < 30 min old in the day window; `runner.chain_link` increments.
  Actions page: https://github.com/MSasportas/prop-check-nba/actions (readable with WebFetch or `gh api .../actions/runs`).
- **Record guard (copied from NHL):** every cycle runs `scripts/guard_record.py --history` before and after: every committed version of
  `data/record/events.jsonl` must be a byte-exact prefix of the next; otherwise the cycle pushes nothing. Only the timer writes
  `data/record/`. No chat ever edits it. A reset needs Matt's explicit order and a byte-exact archive (`data/record/resets.json`).
- **Odds keys:** GitHub secret `ODDS_API_KEYS` (comma-separated), optional `ODDS_API_KEYS_2` (added after the first set). NBA-only pool,
  never shared with NHL. Never in the repo, page or logs. A used-up or refused key is skipped; the ledger (`data/state/credits.json`) knows
  keys only by number. Page warns when the pool is low (fewer than 2 reads a game affordable) or when every key is refused.
- **Feed limits (checked 2026-10-25):** The Odds API free Starter plan = 500 credits a month per key. Event odds cost markets x regions;
  up to 10 bookmakers in `bookmakers=` bill as one region, so Hard Rock + 9 other books = 1 credit per MARKET a read (4 markets = 4). The events list is
  free. Need: 4 reads x 4 credits x ~225 games a month ≈ 3,600; 6 keys (3,000) = 3 reads (B, C, D). **6 keys (3,000 a month): Matt added 3 on 2026-10-25 7:44 PM and 3 more
  at 8:22 PM.** With fewer than ~16 credits a game the plan drops reads in the order A, D, B (C last).
- **Other books asked (9, same credit):** draftkings, fanduel, betmgm, espnbet, pinnacle, betonlineag, betrivers, novig, prophetx.
  Verified 2026-10-25/26: all 9 return rebounds, points and assists (10-26 A read: 7 books on 9/9 games; BetRivers 8/9; Pinnacle
  9/9 games but misses some lines). A silent book costs nothing; swap per NHL item 24 (quality sharp books).
  2026-10-27 A read: all 9 also return threes (BetMGM 3/4 games, the rest 4/4). **Hard Rock returned nothing** at the 11 AM A read
  (all 4 games; it had all markets at 11 AM on 10-26): its NBA props can post after 11 AM. B/C/D retry by design; the page now says so.
- **Discord:** `scripts/notify.py`, secret `DISCORD_WEBHOOK`. Sends NEW PICKS (batched), PULLED (only picks already sent, before tip, with
  the if-bet line), PRICE FINAL, ACTION NEEDED (keys refused / pool low, once a day each), a one-time hello. Never no-pick nights,
  heartbeats, grading or errors. Quiet 12:30-9:00 AM ET. Max 12 messages a day.
- **Debug:** `python scripts/run.py --explain` lists every line (all markets) on the latest reads and the first reason it did not pass.
  Tests: `python -m unittest discover -s tests` (50; `tests/world.py` = fake day from the real probe payloads; `tests/test_qa_failures.py` = QA's regressions). Env: `PC_NOW`, `PC_DATA_DIR`, `PC_ODDS_FIXTURE_DIR`, `PC_ESPN_FIXTURE_DIR`.

## 6. Reviews (scheduled tasks; each reads this file first and updates it last)
- **Daily check, 2:07 PM ET** (scheduled task "Prop Check NBA daily check"): chain alive, A read ran, failed steps, unmatched names, grading done for last night; fix what's broken; no
  rule changes.
- **Weekly team review, Mondays 11:13 AM ET** (scheduled task "Prop Check NBA weekly team review"): Sharp, Data Scientist, UX, Builder, QA on the Record and the odds log; first one ran 2026-10-26.

- **Researcher, daily 8:23 AM ET:** NOT scheduled yet (2026-10-28: creating the scheduled task was blocked by a permission check;
  Matt asked to approve). Until then the CEO runs research when asked.

## 7. Known gaps and risks
1. **Edge vs the book is unproven.** Gap + Guard is a hypothesis carried over from NHL (live there since 2026-10-20, no verdict yet). NBA
   rebounds props have more books and sharper pricing than NHL shots, so expect thin nights. Checkpoint 2026-11-16 (3 weeks): the DS reads
   CLV on every flagged gap and the graded Record. Stop rule: mean CLV <= 0 at >= 25 measured gaps, or units <= -8 -> the Sharp pauses
   new picks and logs it in section 8.
   **All markets are ONE test (Matt, 2026-10-25 9:33 PM):** the checkpoint, stop rule and safety pause use every market
   combined (threes joined 2026-10-26). The Record also shows a bucket per market (Rebounds / Points / Assists / 3-pointers made rows under the headline) so Matt can see
   if one does better; a bucket never switches a market off by itself. Dropping or keeping a market is Matt's call (customer fact).
2. **Starting lineups source = Rotowire** (scraped HTML; layout change or block = the chip stops at Injury report clear and the page
   says so). "Confirmed" verified live 2026-10-25 evening: 12 of 14 teams showed confirmed by 7:40 PM (MEM/SAC, 9 PM tip, still expected).
3. **Model (guard only), one per stat:** fitted by the DS 2026-10-25 on 2025-26 box scores, walk-forward (`research/calibrate.py
   reb|pts|ast [grid]`): 18,841 player-games Dec-Apr each, test line = his last-10 average as an x.5 line. Rebounds: disp 1.15, rpm
   half-life 20, log loss 0.6686 vs base 0.6877. Points: disp 1.6, half-life 10, 0.6771 vs 0.6908, bias +0.9 pt -> **offset +0.009**.
   Assists: Poisson (disp 1.0), half-life 10, 0.6660 vs 0.6844. Threes (fit 2026-10-26): disp 1.15, half-life 20, 0.6113 vs 0.6569, bias
   +0.4 pt -> offset 0. Opponent factor exp 1.0, no back-to-back cut for all four. 16-20 variants
   tried per stat. Offsets in `gap_guard.offsets`. Not tested against book lines (no historical Hard Rock prices); refit only with a
   named sample.
4. Name matching: accents, Jr./III and dots are normalized; within the two teams playing only. Unmatched names are listed in
   status.json and skipped, never guessed.
5. The ESPN tip time is used for lock (games often tip ~10 min later): conservative.
6. Keys refill on the 1st (assumed, as NHL). With 4 markets, 6 keys (3,000) over ~225 games = 13.3 credits a game = 3 reads (B, C, D);
   the 11 AM A read (never picks) drops in a full month. All 4 reads would need ~3,600 a month (8 keys).
7. Official NBA injury report PDF not parsed (Rotowire mirrors it). Build only if Rotowire proves unreliable.
8. **Verified live 2026-10-25 7:50 PM (first keyed read, MEM@SAC B):** Hard Rock posts rebounds (8 players, ~+105/-135, hold ~8%);
   1 credit per read; **all 9 other books returned rebounds** (DK, FD, MGM, ESPN Bet, BetRivers, BetOnline 18 outcomes each; novig and
   prophetx ~110 incl. alt lines; Pinnacle only 10 = 5 players); Hard Rock outcome links are real bet-slip deep links
   (`app.hardrock.bet/?deep_link_value=betslip/<id>`). Discord hello delivered. **Pinnacle coverage is the volume limit**: 5 of 8 players
   failed "Pinnacle not on this line". Do not loosen without a sample (DS names it at the first weekly review).

## 8. Rule-change log
| Date | Change | Why | Sample |
|---|---|---|---|
| 2026-10-26 11:40 PM (CEO, Matt's order; Builder, QA) | **v1.2: 3-pointers made added** (customer fact), same Gap + Guard, own model (section 7 item 3), reads cost 4 credits; in a full month the morning A read drops (C, B, D kept) | Matt: "include 3 pointers, those odds are typically a little better"; NBA main lines showed 0 gaps on Oct 26 | None yet; judged with the other markets |
| 2026-10-25 8:45 PM (CEO, Matt's order; Builder, QA) | **v1.1: points and assists added** (customer fact), same Gap + Guard thresholds, own model per stat (section 7 item 3), 1 side per player per market, no game or night caps (confirmed with Matt), reads cost 3 credits | Matt: "If we expand to points and assists..." then added 3 more keys (6 total) | None yet; all three judged TOGETHER at the 2026-11-16 checkpoint (Matt, 9:33 PM: "group all 3 together"); per-market buckets are for viewing only |
| 2026-10-25 (CEO, setup interview with Matt) | **v1.0.** Customer facts locked (section 1). Gap + Guard copied from NHL v3.3 for rebounds main lines; D read (20 min) added because Matt bets in the last hour; Questionable/GTD rule; parlays off | Setup interview; NHL template | None yet: first slate after the keys arrive |

## 9. Session log (newest first, one line each)
- 2026-10-28 10:30 AM (CEO, Matt: 0 bets in 2+ nights, does NBA have a Researcher?): Researcher role created (research/RESEARCH.md,
  HYPOTHESES.md, LOG.md). Run 1 on Oct 25-27: 3,318 sides, median -6.2% vs market, best +2.9%, 0 qualify; Hard Rock re-prices with
  the market (1 stale event in 2,198). F1-F5 registered forward. Paid historical props option sized for Matt (100K plan $59/mo).
- 2026-10-27 2:15 PM (CEO, daily check): alive (chain link 73, status 1:50 PM, all steps ok, Actions green, pool 2,855). A read ran 11 AM (4 games x 4 credits) but Hard Rock had not posted any NBA props (other 9 books had all 4 markets incl. threes); B read 6 PM. 10-26: 0 picks, nothing to grade (no events.jsonl yet). Rotowire showed confirmed starters last night (18 confirmed states). No unmatched, no unknown teams. Fix: empty state said "No prices read yet" after a read with no Hard Rock; now says Hard Rock hasn't posted yet (Builder). QA (fresh, 380px Chromium): SHIP, 1 low fix applied; regression test added, 50 tests pass.
- 2026-10-26 11:40 PM (CEO): v1.2 threes (Matt). Re-seeded with fg3m, DS fit, engine/page/Discord, box cache cleared. QA (fresh): SHIP WITH
  FIXES, all low (market field to Discord, 'threes' instead of '3PM' which read like a clock time, doc numbers); fixed, 49 tests pass.
- 2026-10-26 8:45 PM (CEO, Matt strongly concerned Hard Rock prices NBA far more carefully than NHL): measured. NBA Oct 26: 695 main
  lines with >= 4 books, median |HR fair - market fair| 0.7 pts, 0 lines off by >= 3 pts, 0 of 1,412 sides at +3%. NHL shots same rule:
  1-9 gaps >= 3% a night (Oct 20-26), HR off the market ~1-2.5 pts median. Concern supported by data. Plan told to Matt: run to the
  Nov 2 review unchanged; the DS reports the nightly gap distribution; if still ~0 gaps, the honest call (Matt's) is that main-line
  Gap + Guard has no NBA edge at Hard Rock. Only untested angle: injury-news lag (HR slow after late scratches), needs faster reads.
- 2026-10-26 8:15 PM (CEO, Matt: check alt ladders at Hard Rock and every book): one-time `research/alt_probe.py` (workflow alt-probe,
  18 credits) on ATL@HOU, MEM@UTA, GSW@DEN, main + alternate pts/reb/ast, HR + 9 books. Alt ladders are OVER-ONLY at every sportsbook
  (HR 966 rungs); two-sided prices at ladder lines come only from novig/prophetx (Pinnacle posts no alts). HR rung lines: 76-80% quoted
  by >= 1 other sportsbook, 53% by >= 4. vs two-sided fair (-200..+200): main median -7.9% best -0.3%; ALT median -11.4% best -2.6%; 0
  >= 0. vs other sportsbooks same rung: HR cheaper than the median on 94 of 222, best of all on 15. Longshots > +200: median -21%, 1-3
  'positive' rungs are thin exchange quotes on 6-10% chances (noise). Conclusion: alt ladders carry more vig than main lines; no change.
- 2026-10-26 8:10 PM (CEO, Matt asked why no picks on a 9-game night; his idea: books post different main lines): 30 reads, 1,412
  sides on B/C/D, 0 passed. Best gap all day +0.9% (needs +3.0%); median -6.2%; 0.3% of sides >= 0. Lines: other books quote Hard Rock's
  exact line for 87% of player-books (others are +/-1 off), Pinnacle only 59% (160 of 272) -> 460 sides failed "Pinnacle not on this line".
  Mismatched lines are skipped, never compared across lines, and none of them was close either (best +0.6%). Hard Rock hold ~6.8%, same
  as DK/MGM/ESPN. No change: one night. Weekly review to watch the gap distribution; Pinnacle-required is the volume limit if gaps appear.
- 2026-10-26 2:10 PM (CEO, daily check): alive (chain link 37, status 1:50 PM, all steps ok, Actions all green, pool 2,970). A read ran 11 AM (9 games x 3 credits); 594 lines, 0 passing; next read 5:30 PM. 10-25: 0 picks, so nothing to grade (no events.jsonl yet, expected); all 7 finals added to the box store (196 rows). Rotowire showed all 14 teams **confirmed** by the 9 PM read on 10-25. Unmatched Rotowire: Khalifa Diop, Nae'Qwan Tomlin (CLE, Out, deep bench; harmless). No unknown teams, no odds errors. Tests pass. No code changes.
- 2026-10-26 11:30 AM (CEO, weekly review #1): alive (chain link 34, status 11:20 AM, all steps ok, pool 2,970). DS: 0 graded legs, 0 flagged gaps, so no CLV, calibration or units yet; 12 reads (3 B/C/D on 10-25 MEM@SAC rebounds-only, 9 A today), 30 credits = 1 a market a read as planned. All 9 other books return all 3 markets (BetRivers 8/9 games, Pinnacle 8/9 games); Pinnacle has the player's line on 56% of today's A rows (334/594), 35% on 10-25. Gap failures dominate (334), then no-Pinnacle (208). Best near-misses: 10-25 SAC reb 13.5 u +105 gap -1.7% (B/C, passed the guard); today's A: two +2.8-2.9% gaps blocked by no Pinnacle / 2 books (A is baseline only). Samples far too small: Sharp makes no rule change; 11-16 checkpoint not due. UX: odds line said "about 6 days left" (read as the pool running out); now "refills in 6 days". QA (fresh, Chromium 380px, 8 states): SHIP; 40 tests pass.
- 2026-10-25 9:35 PM (CEO): Matt: judge all 3 markets together, bucket them on the Record. Rule text updated (section 7 item 1);
  the Record already shows the combined headline plus a row per market. No code change.
- 2026-10-25 ~8:50 PM (CEO): v1.1 points + assists (Matt added 3 more keys, 6 total). Re-seeded box scores with pts/ast, DS fit two
  models, engine/grading/page/Discord made multi-market, live box cache cleared to rebuild with pts/ast. QA (fresh): SHIP WITH
  FIXES, no blockers; low-pool warning now counts reads, reason says when the model is lower; 40 tests pass.
- 2026-10-25 7:55 PM (CEO): chain restarted with the keys (pool 1,499, allowance 28.8, all 4 reads on). First read: 16 sides, 0 passed
  (gaps -1.7% to -9.4%; 5 players lacked Pinnacle). See section 7 item 8.
- 2026-10-25 7:45 PM (CEO): Matt added `ODDS_API_KEYS` and `DISCORD_WEBHOOK`. Secrets load only when a run starts, so a push to
  scripts/ restarted the chain. Rotowire "confirmed" verified live. Watch: first reads on MEM@SAC (9 PM tip).
- 2026-10-25 2:10 PM (CEO, daily check): alive (chain run 33 in progress, last status 1:50 PM, all steps ok, ESPN ok, Rotowire read started 2 PM for the 5 PM tip, 7 games). Still no `ODDS_API_KEYS` and no `DISCORD_WEBHOOK` (no notified.json): no A read, no picks, nothing to grade, no `others` books seen yet. Rotowire all Expected so far (confirmed check moves to tomorrow's check). Unmatched Rotowire: Richie Saunders (MEM rookie, Out, not on the ESPN roster; harmless). 30 tests pass. No code changes. Reminded Matt once about keys + webhook.
- 2026-10-25 ~12:20 PM (CEO): v1.0 shipped. Built from the NHL template (timer chain, Record + guard, key pool, Discord, page look copied;
  engine rewritten for rebounds). DS fit the model guard (section 7 item 3). UX/Builder subagent built the page (checked at 380px in
  Chromium, 8 states). QA (fresh): SHIP WITH FIXES, 8 findings (A-read retries could drain the pool; no pick from a read > 15 min old;
  open picks of earlier slates / vanished / postponed games now lock and void; Rotowire layout change now said on the page; unmatched
  Rotowire tags no longer read as healthy; empty-state wording; team codes on the Record; days left) all fixed, 30 tests pass. First live
  run 12:12 PM: ESPN 23/23, Rotowire ok, 7 games, all steps ok; page says no keys yet. Daily check + weekly review scheduled.
  Waiting on Matt: 3 odds keys (`ODDS_API_KEYS`) and `DISCORD_WEBHOOK`.
- 2026-10-25 ~10:30 AM setup (CEO): interview done (rebounds only, main line, over+under, -200, parlays off, last hour before tip,
  regular season, new Discord channel). Old NBA build wiped (repo, secrets and Pages kept). Seed + source probe workflow pushed.
  Asked Matt for 3 new free odds keys and the Discord webhook.
