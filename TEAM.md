# TEAM.md: Prop Check NBA operating doc

Read this first in every session. Update it last. Every chat in the NBA project starts by attaching
MSasportas/prop-check-nba (add_repo, push access), cloning it and reading this file.

Live page: https://msasportas.github.io/prop-check-nba/ · Repo: MSasportas/prop-check-nba (public)
Sister company of Prop Check NHL (MSasportas/prop-check-nhl): own CEO, team, repo, Record and odds key pool. The NHL repo is the
template and is READ ONLY from here. Never push to it.

## 1. The product
Every NBA game day: every rebounds, points and assists leg that qualifies at a real Hard Rock (`hardrockbet`) price, ranked best first, each with
the price, our chance vs the price's break-even and a one-line plain reason. The page updates through the day; each pick shows how
settled it is (Early / Injury report clear / Starters confirmed, then Locked) and pulled picks stay visible with the reason and what it
means if Matt already bet. Dark, phone first (~380px). The Record is the scoreboard. Parlays are not offered (Matt, setup).

**Customer facts (fixed; locked in the setup interview 2026-10-25, Matt):**
| Fact | Locked value |
|---|---|
| Book | Hard Rock Florida only. A pick needs a real Hard Rock number |
| Markets | **Player rebounds, points and assists (points + assists added 2026-10-25 8:22 PM, Matt). Main line only (no alt ladders). Over and under.** Everything else is out |
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
Sharp (betting method, final call) · Data Scientist (data, model, samples, judging the Record) · UX (page) · Builder (all code) ·
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
| Markets | Hard Rock `player_rebounds`, `player_points`, `player_assists`: the main line per player (the two-sided pair closest to even), over and under. Alt lines are never used |
| Step 1: the gap | All of: Hard Rock EV vs the market fair >= **+3.0%**; >= **4 other books** priced the same player, same line, both sides, fresh, hold 0-15%; **market fair = median** of the books' proportionally de-vigged chance (even count: mean of the middle two); **Pinnacle present** with both sides and Pinnacle-fair EV on Hard Rock's price >= 0.0%; Hard Rock price **-200 to +200** |
| Step 2: the guard | final = 0.8 x market fair + 0.2 x (model chance + offset). Passes iff final EV >= **+2.0%**. No model for the player = no pick. Offset frozen (section 7 item 3) |
| Which reads can pick | B (90 min), C (45 min) and D (20 min before tip) reads that carry other books. The morning A read is a baseline only |
| The pick | The first passing read makes the pick and **freezes its price**. That price is shown, sent to Discord and graded: flat 1 unit. Later prices never change it |
| Eligibility | >= 10 games of history (2025-26 + 2026-27 box scores); listed **Out or Doubtful -> never**; **Questionable / Day-to-day / GTD -> no new pick** until he drops off the report or is in a confirmed starting five; missed his team's last game -> waits for confirmed starters (and must start); minutes last 3 games < 60% of his recent average -> no pick (role or restriction changed) |
| Settled chip | **Early** (he or someone in his team's top 7 by recent minutes is Doubtful / Questionable / GTD) -> **Injury report clear** (none of them is; Out and Probable are settled) -> **Starters confirmed** (Rotowire shows both teams' starting fives as confirmed) -> **Locked** at tip |
| Pulls | Later reads only PULL: Hard Rock's price changed and step-1 EV < **+1.5%**; fewer than 4 books; Pinnacle gone or sign flipped; step 2 fails; line removed; player listed Out, Doubtful, Questionable or GTD after the pick, unless he is in a confirmed starting five (every run). Teammate news does not pull by itself: the next read re-prices it. Pulled picks stay on the page and in the Record, graded at the frozen price, counted under "Pulled". **Every pull says what happened and what it means if Matt already bet.** No pulls after tip. Once the D read is done only an injury pull can happen ("Price final") |
| Caps | **None per game or per night (Matt, 2026-10-25: "no limit per game or anything")**: every qualifying leg is shown, ranked by final EV. Only 1 side per player per market (both sides of one line can't both be bets); one player can have a rebounds, a points and an assists pick |
| Parlays | Off (customer fact) |
| Grading | When ESPN marks the game final. Overtime counts. Did not play = void. Graded at the frozen price, flat 1 unit |
| Odds reads | A 11 AM (or 3h before the first tip), B 90 min, C 45 min, D 20 min before each game. 3 markets = 3 credits a read (`ops.cost_per_read`). Reads a game = allowance / 3, at most 4; priority when credits are short: C, B, D, A |
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
  up to 10 bookmakers in `bookmakers=` bill as one region, so Hard Rock + 9 other books = 1 credit per MARKET a read (3 markets = 3). The events list is
  free. Need: 4 reads x 3 credits x ~225 games a month ≈ 2,700. **6 keys (3,000 a month): Matt added 3 on 2026-10-25 7:44 PM and 3 more
  at 8:22 PM.** With fewer than ~12 credits a game the plan drops reads in the order A, D, B (C last).
- **Other books asked (9, same credit):** draftkings, fanduel, betmgm, espnbet, pinnacle, betonlineag, betrivers, novig, prophetx.
  Which return NBA rebounds is unverified until the first read; a silent book costs nothing; swap per NHL item 24 (quality sharp books).
- **Discord:** `scripts/notify.py`, secret `DISCORD_WEBHOOK`. Sends NEW PICKS (batched), PULLED (only picks already sent, before tip, with
  the if-bet line), PRICE FINAL, ACTION NEEDED (keys refused / pool low, once a day each), a one-time hello. Never no-pick nights,
  heartbeats, grading or errors. Quiet 12:30-9:00 AM ET. Max 12 messages a day.
- **Debug:** `python scripts/run.py --explain` lists every line (all markets) on the latest reads and the first reason it did not pass.
  Tests: `python -m unittest discover -s tests` (30; `tests/world.py` = fake day from the real probe payloads; `tests/test_qa_failures.py` = QA's regressions). Env: `PC_NOW`, `PC_DATA_DIR`, `PC_ODDS_FIXTURE_DIR`, `PC_ESPN_FIXTURE_DIR`.

## 6. Reviews (scheduled tasks; each reads this file first and updates it last)
- **Daily check, 2:07 PM ET** (scheduled task "Prop Check NBA daily check"): chain alive, A read ran, failed steps, unmatched names, grading done for last night; fix what's broken; no
  rule changes.
- **Weekly team review, Mondays 11:13 AM ET** (scheduled task "Prop Check NBA weekly team review"): Sharp, Data Scientist, UX, Builder, QA on the Record and the odds log; first one 2026-11-02.

## 7. Known gaps and risks
1. **Edge vs the book is unproven.** Gap + Guard is a hypothesis carried over from NHL (live there since 2026-10-20, no verdict yet). NBA
   rebounds props have more books and sharper pricing than NHL shots, so expect thin nights. Checkpoint 2026-11-16 (3 weeks): the DS reads
   CLV on every flagged gap and the graded Record. Stop rule: mean CLV <= 0 at >= 25 measured gaps, or units <= -8 -> the Sharp pauses
   new picks and logs it in section 8.
   **All three markets are ONE test (Matt, 2026-10-25 9:33 PM):** the checkpoint, stop rule and safety pause use rebounds + points +
   assists combined. The Record also shows a bucket per market (Rebounds / Points / Assists rows under the headline) so Matt can see
   if one does better; a bucket never switches a market off by itself. Dropping or keeping a market is Matt's call (customer fact).
2. **Starting lineups source = Rotowire** (scraped HTML; layout change or block = the chip stops at Injury report clear and the page
   says so). "Confirmed" verified live 2026-10-25 evening: 12 of 14 teams showed confirmed by 7:40 PM (MEM/SAC, 9 PM tip, still expected).
3. **Model (guard only), one per stat:** fitted by the DS 2026-10-25 on 2025-26 box scores, walk-forward (`research/calibrate.py
   reb|pts|ast [grid]`): 18,841 player-games Dec-Apr each, test line = his last-10 average as an x.5 line. Rebounds: disp 1.15, rpm
   half-life 20, log loss 0.6686 vs base 0.6877. Points: disp 1.6, half-life 10, 0.6771 vs 0.6908, bias +0.9 pt -> **offset +0.009**.
   Assists: Poisson (disp 1.0), half-life 10, 0.6660 vs 0.6844. Opponent factor exp 1.0, no back-to-back cut for all three. 16-20 variants
   tried per stat. Offsets in `gap_guard.offsets`. Not tested against book lines (no historical Hard Rock prices); refit only with a
   named sample.
4. Name matching: accents, Jr./III and dots are normalized; within the two teams playing only. Unmatched names are listed in
   status.json and skipped, never guessed.
5. The ESPN tip time is used for lock (games often tip ~10 min later): conservative.
6. Keys refill on the 1st (assumed, as NHL). 6 keys cover 4 reads x 3 markets a game (~2,700 of 3,000 a month).
7. Official NBA injury report PDF not parsed (Rotowire mirrors it). Build only if Rotowire proves unreliable.
8. **Verified live 2026-10-25 7:50 PM (first keyed read, MEM@SAC B):** Hard Rock posts rebounds (8 players, ~+105/-135, hold ~8%);
   1 credit per read; **all 9 other books returned rebounds** (DK, FD, MGM, ESPN Bet, BetRivers, BetOnline 18 outcomes each; novig and
   prophetx ~110 incl. alt lines; Pinnacle only 10 = 5 players); Hard Rock outcome links are real bet-slip deep links
   (`app.hardrock.bet/?deep_link_value=betslip/<id>`). Discord hello delivered. **Pinnacle coverage is the volume limit**: 5 of 8 players
   failed "Pinnacle not on this line". Do not loosen without a sample (DS names it at the first weekly review).

## 8. Rule-change log
| Date | Change | Why | Sample |
|---|---|---|---|
| 2026-10-25 8:45 PM (CEO, Matt's order; Builder, QA) | **v1.1: points and assists added** (customer fact), same Gap + Guard thresholds, own model per stat (section 7 item 3), 1 side per player per market, no game or night caps (confirmed with Matt), reads cost 3 credits | Matt: "If we expand to points and assists..." then added 3 more keys (6 total) | None yet; all three judged TOGETHER at the 2026-11-16 checkpoint (Matt, 9:33 PM: "group all 3 together"); per-market buckets are for viewing only |
| 2026-10-25 (CEO, setup interview with Matt) | **v1.0.** Customer facts locked (section 1). Gap + Guard copied from NHL v3.3 for rebounds main lines; D read (20 min) added because Matt bets in the last hour; Questionable/GTD rule; parlays off | Setup interview; NHL template | None yet: first slate after the keys arrive |

## 9. Session log (newest first, one line each)
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
