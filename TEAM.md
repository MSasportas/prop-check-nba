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
means if Matt already bet. **Page (2026-11-04 redesign, copied from NHL): Ballpark theme, light only, phone first (~380px), six rail tabs Picks · Live · Games · Record · Lab · Info; Hard Rock only on the page (no DraftKings).** The Record is the scoreboard. Parlays are not offered (Matt, setup).
**Tap-to-bet (Matt, 2026-11-02 8:43 PM; since 2026-11-04 the PAGE shows the Hard Rock button only, Discord still sends both):** every OPEN pick (not pulled, started, graded or stale) has a "Hard Rock +115" button that
fills the Hard Rock slip and a "DraftKings -110" button (DK's own price), on the page and in Discord as masked links. Links come from
the NEWEST odds read (`includeLinks=true` on B/C/D reads, same credits; links kept for Hard Rock and DraftKings only). Hard Rock: the
feed's `app.hardrock.bet/?deep_link_value=betslip/<id>` only opens the app, so we build `share.hardrock.bet/Pt0T/bet?deep_link_value=hardrock://betslip/<id>`
(NHL, tested on Matt's phone). No link from the feed = no button; a full URL is never shown. Code: `odds.bet_links`, `run.publish`
(`links`), `notify.bet_buttons`, `index.html` `betRow`. DraftKings is untested on a phone: Matt taps the first one.

**Customer facts (fixed; locked in the setup interview 2026-10-25, Matt):**
| Fact | Locked value |
|---|---|
| Book | **Hard Rock** Florida. A pick needs a real Hard Rock number. DraftKings adds a second button when it passes the same check (Matt, 2026-11-03 9:46 AM) |
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

## 4. Current rules (v2.5, 2026-11-03). Source of truth: `config/rules.json` (`pin_solo`, `watch.pin_judge`)
**LIVE v2.6 (Matt, 2026-11-03 9:46 AM): Hard Rock only makes picks; the other books don't matter; DraftKings adds a button when it
agrees.** Rule: between back-to-back checks, Pinnacle moves 2+ pts on a line; Hard Rock quotes that same line on both checks at a
price at or better than Pinnacle's fair price (-200..+200, B/C/D reads, <= 15 min old, eligible, one pick per player per market a
night, price frozen, graded at the Hard Rock price). If DraftKings passes the same check on the same bet (same line both checks, price
at or better than Pinnacle's fair), the pick also lists DraftKings' price and gets a DraftKings button (`pin_solo.link_books`). Pulled
on injury or if Hard Rock takes the line down. Replay Oct 26-Nov 2: 29 picks (3.6 a night) 23-6 +15.74u 79%, +54% a bet; 20 of the 29
would have had a DraftKings button. Why DraftKings is not a pick book: its own picks Hard Rock did not also make went 29-27 -0.99u.
History below (v2.5 / v2.5b were built 11-03 6:49-9:46 AM, no picks made under them):
**v2.5 (Matt, 2026-11-03 6:49 AM): the other books no longer matter, and a pick can be at Hard Rock OR DraftKings.** For each main
line of a pick book (Hard Rock, DraftKings; that book quotes the same line on both reads), Pinnacle quotes that same line on both reads
and moves >= 2 pts toward a side; the side qualifies at each pick book whose price is at or better than Pinnacle's FAIR price (and
-200..+200, not stale). The pick lists every passing book (`books`), with a tap-to-bet button only for those; headline and GRADED price =
the best passing price (ties: Hard Rock), `book` = that book. Pulled only if EVERY book it was shown at removes the line (or injury). The
Record adds a row per book once a DraftKings pick is graded. **v2.5b (Matt, 2026-11-03 7:40 AM): the two books run INDEPENDENTLY
under the same rule** (supersedes "best passing price"): each book is checked on its own (its main line the same on both back-to-back
checks, Pinnacle the same line, its own price at or better than Pinnacle's fair), and each passing book is ITS OWN pick: own card,
own Discord line, own button, own Record entry graded at its own price; one pick per player per market per BOOK a night; a DraftKings
pick id ends in ":draftkings". If both qualify on the same bet, there are two picks (the Record counts both; per-book rows split them).
Replay Oct 26-Nov 2: Hard Rock 29 23-6 +15.74u 79%; DraftKings 76 45-31 +9.80u 59%; together 105 (13 a night) 68-37 +25.54u 65%. Same bet
at both books 20 bets x 2 = 32-8; DraftKings picks Hard Rock did not also make: 56 29-27 -0.99u (flat). The text below is v2.4 history (others gate now `others_max` null).
Replay Oct 26-Nov 2 (consecutive reads, one pick per player/market): v2.4 23 picks 18-5 +12.34u 78%; HR only without the others gate
29 23-6 +15.74u 79%; **v2.5 (HR or DK, no others gate) 84 picks 52-32 +16.16u 62%, +19% a bet**; DK alone 76 45-31 +9.80u 59%.
CEO flagged to Matt (11-03): dropping the others gate is free; adding DraftKings triples volume but costs hit rate (78% -> 62%).
**Previous live rule (v2.4): Pinnacle moves, the other books move less than 2 pts, and Hard Rock is at or better than Pinnacle's FAIR price** (Matt, 2026-10-28; widened from "alone" < 1 pt at 11:52 AM, after research runs 1-6: Hard Rock's NBA main lines sit ~6% under the market
and Gap + Guard found 0 bets in 3,318 sides). `engine.solo_moves`: between two consecutive reads of a game, on Hard Rock's main line
(Hard Rock quotes that same line on BOTH reads), Pinnacle quotes the same line on both reads and its de-vigged chance moves >= 2 pts
(`min_move` 0.02) toward a side, while the median move toward that side of the other books (same line, both reads, >= 4 books,
hold 0-15%) is < 2 pts (`others_max` 0.02; was < 1 pt in v2.0). **AND (v2.3, Matt 2026-10-29) Hard Rock's price on that side is at or better than Pinnacle's FAIR price** (`min_ev_vs_pin` 0.0: Pinnacle's new de-vigged chance x Hard Rock's payout - 1 >= 0; Pinnacle's own margin is taken out, so this is stricter than v2.2's "2 pts better than Pinnacle's posted price", which only got near fair; e.g. Pinnacle -140 is fair about -120, Hard Rock must be -120 or better). Pick = that side at Hard Rock's price on the later read: B/C/D reads only, read <= 15 min old,
price -200..+200, eligibility as below, one pick per player per market a night, price frozen, graded like before. It is a SIGNAL that now also
has to clear fair price (Run 7: the picks priced under Pinnacle's fair win only if the move keeps running). Pulls: injury status (as below) or Hard Rock removes the line;
no price-based pulls. Discovery Oct 25-27 (research F7): others < 2 pts = 31 bets 22-9 +9.74u (alone 16 11-5, 1-2 pts 15 11-4); engine
replay with one pick per player/market a night = 29 picks 22-7 +11.75u, 26 of them on Oct 26.
Checkpoint 2026-11-25 (~150 bets). Stop rule: units <= -8, or after 75 bets ROI <= 0 -> the Sharp pauses new picks, logs it in section 8.
**Health metric (Sharp, weekly review 2026-11-02):** CLV vs Pinnacle's fair at the last read before tip, on v2.3 picks. Re-judge at 25 measured v2.3 picks (D-read picks have no later read, so they can't be measured). Through 11-01: 2 measured.
**Behind the scenes: Pinnacle as the price judge** (`watch.pin_judge`, `scripts/watch.py`): newest B/C/D read, Hard Rock EV >= +2% vs
Pinnacle's fair on the same line, -200..+200, eligible; first flag per player/market/night; graded; `data/watch/pin_judge/` and the
page's Lab tab only (was Backstage until 2026-11-04), never the Record or Discord. Discovery: 6 bets 5-1 +3.18u. Promotion needs Matt.
Also logged for research (shadow `solo` rows): every Pinnacle 2+ pt move with the other books' move, so "any Pinnacle move" (46 bets
31-15 +10.88u in discovery) can be scored forward without a product change.
**Gap + Guard (v1.x) is OFF** (`gap_guard.active` false); its rows are still computed into the shadow log. Its rules, for history:

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
| Odds reads | A 11 AM (or 3h before the first tip), B 90 min, C 45 min, D 20 min before each game. 4 markets = 4 credits a read (`ops.cost_per_read`). Reads a game = allowance / 4, at most 4; priority when credits are short: C, B, D, A. **No daily cap (Matt, 2026-11-03)**: every planned read runs while credits last. **v2.4: the A read runs from spare credits** (`reads.spare`) when the allowance only pays for B/C/D, and only while the pool still covers B/C/D for every game left in the month; then it pauses and the page says so |
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
  2026-10-28 A read: all 9 other books returned all 4 markets on 12/12 games; Hard Rock posted all 4 at 11 AM this time.
  2026-10-29 A read: all 9 other books returned all 4 markets on 3/3 games; Hard Rock posted all 4 at 11 AM.
  2026-10-30 A read: all 9 other books returned all 4 markets on 10/10 games except BetMGM (3 markets on 1 game, absent on 2 games); Hard Rock posted all 4 at 11 AM.
  2026-10-31 A read: all 9 other books returned all 4 markets on 7/7 games except BetMGM (absent PHI@CHA, 2 markets ATL@NO); Hard Rock posted all 4 at 11 AM.
  2026-11-01: no A read (keys refilled, full-month plan = B, C, D; section 7 item 6). First B read 2 PM (BOS@ORL): Hard Rock all 4 markets, all 9 other books all 4 markets.
  2026-11-01 all 12 reads (4 games x B/C/D): Hard Rock all 4 markets, all 9 other books all 4 markets on every read (BetMGM complete).
  2026-11-02 all 45 reads (15 games x B/C/D): Hard Rock all 4 markets, all 9 other books all 4 markets on every read.
  2026-11-04 A read (first under v2.4 spare credits, 14 games x 4 = 56 credits): Hard Rock all 4 markets on 14/14; all 9 other books all 4 markets except BetMGM (absent MIL@BOS).
  2026-11-04 all 56 reads (14 games x A/B/C/D): all 9 other books all 4 markets (BetMGM absent on 1 read). 2026-11-05 A read (2 games, 8 credits): Hard Rock all 4 markets on 2/2; 8 other books all 4 markets, **novig returned nothing** on both games (first miss; a silent book costs nothing, watch).
- **Page (2026-11-04):** `index.html` (Ballpark, fonts bundled in fonts/, no outside font calls). Extra data it reads:
  `data/headshots.json` (ESPN pid -> a.espncdn.com photo, merged on each fresh roster read), `record.json` `summary.cuts`/`summary.days`
  (views only), `config/lab.json` (Lab entries). Slate adds `pulled.code/status` (status Out = scratch, hidden), `added_at` (NEW label),
  `games[].injury_clear`, `next_check_read`, `status.feeds`. Fixtures: `fixtures/make_fixtures.py`, open `?fixture=<name>`.
- **Live tab = in-browser polling (Matt, 2026-11-04 11:12 PM; replaced the timer's `live` step / data/live.json, which fed nothing else).**
  While Live is the open tab and the page is visible, the phone itself reads every 10 s: ESPN scoreboard
  (`site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=YYYYMMDD`) + one `summary?event=<id>` per started game with an
  ungraded pick. Stats are read exactly as grading reads them (PTS / REB / AST / made part of 3PT, same feed, same columns), so the live
  number is the graded number. Backup when ESPN fails (6 s timeout, error, bad JSON): NBA.com `cdn.nba.com/static/json/liveData/
  scoreboard/todaysScoreboard_00.json` + `boxscore/boxscore_<gameId>.json` (teams by tricode map, players by normalized name). Both fail ->
  "Live scores unavailable", scores/clocks/stats hidden (never old scores as live). Pauses when hidden or on another tab, polls at once on
  return, stops when no game with a pick is in progress (one wake-up at the next tip). "Updated Xs ago" on the tab. No relay needed:
  ESPN answers browsers directly (CORS check below). Fixtures `liveon`, `liveespnfail`, `liveallfail`, `livedone`, `livepre` read
  `fixtures/<name>/feeds/`; `?feed=espnfail|allfail` forces the backup / failure. `data/live.json` is a leftover: nothing writes or reads it.
  **CORS check (2026-11-04, from GitHub's servers, Origin https://msasportas.github.io):** ESPN scoreboard + summary GET ->
  `access-control-allow-origin: *`, cache max-age 7-10 s; OPTIONS preflight -> 403 (so the page sends simple GETs only, no custom
  headers). cdn.nba.com -> 403 to GitHub's servers (browser CORS unknown). **Live-game browser check (11:55 PM, `probe/qa_live.py`, workflow
  qa-live, push to it to re-run):** WebKit (iPhone 13 profile) and normal Chrome loading the PUBLIC site read ESPN every 10 s (scoreboard +
  summaries, 200), Live showed Q3 clocks/scores, "7 / 9.5 pts, 2 to spare", Derrick Jones O4.5 reb HIT mid-game, "Updated 2s ago", no
  console errors. HEADLESS Chrome is refused by ESPN (response without the CORS header): bot filtering, so QA must use WebKit or non-headless
  Chrome, never conclude from headless or curl alone. ESPN live box = grading source; NBA's official box could not
  be reached from any of our machines to cross-check player by player.
- **Discord:** `scripts/notify.py`, secret `DISCORD_WEBHOOK`. Sends NEW PICKS (batched), PULLED (only picks already sent, before tip, with
  the if-bet line), PRICE FINAL, ACTION NEEDED (keys refused / pool low, once a day each), a one-time hello. Never no-pick nights,
  heartbeats, grading or errors. Quiet 12:30-9:00 AM ET. Max 12 messages a day.
- **Debug:** `python scripts/run.py --explain` lists every line (all markets) on the latest reads and the first reason it did not pass.
  Tests: `python -m unittest discover -s tests` (90 on 2026-11-04; `tests/world.py` = fake day from the real probe payloads; `tests/test_qa_failures.py` = QA's regressions). Env: `PC_NOW`, `PC_DATA_DIR`, `PC_ODDS_FIXTURE_DIR`, `PC_ESPN_FIXTURE_DIR`.

## 6. Reviews (scheduled tasks; each reads this file first and updates it last)
- **Daily check, 2:07 PM ET** (scheduled task "Prop Check NBA daily check"): chain alive, A read ran, failed steps, unmatched names, grading done for last night; fix what's broken; no
  rule changes.
- **Weekly team review, Mondays 11:13 AM ET** (scheduled task "Prop Check NBA weekly team review"): Sharp, Data Scientist, UX, Builder, QA on the Record and the odds log; first one ran 2026-10-26.

- **Researcher: PAUSED (Matt, 2026-10-28 12:21 PM: "keep the research paused"); one run on Matt's ask 2026-10-29 (Run 7, cutting pick counts).** No scheduled task. Forward ideas in
  research/HYPOTHESES.md stay registered; the shadow log keeps collecting. Resume only when Matt asks.

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
   the 11 AM A read is not paid for in a full month. v2.4 (Matt, 2026-11-02): it runs from spare credits until the pool only covers
   B/C/D for the rest of the month. November forecast (pool 2,768 on 11-02, 196 games left): A runs 11-04 to ~11-17, then pauses
   unless keys are added (1 more key covers the rest of November; a full month at 4 reads needs ~3,600 = 8 keys). Matt adds keys
   before they run out.
7. Official NBA injury report PDF not parsed (Rotowire mirrors it). Build only if Rotowire proves unreliable.
8. **Verified live 2026-10-25 7:50 PM (first keyed read, MEM@SAC B):** Hard Rock posts rebounds (8 players, ~+105/-135, hold ~8%);
   1 credit per read; **all 9 other books returned rebounds** (DK, FD, MGM, ESPN Bet, BetRivers, BetOnline 18 outcomes each; novig and
   prophetx ~110 incl. alt lines; Pinnacle only 10 = 5 players); Hard Rock outcome links are real bet-slip deep links
   (`app.hardrock.bet/?deep_link_value=betslip/<id>`). Discord hello delivered. **Pinnacle coverage is the volume limit**: 5 of 8 players
   failed "Pinnacle not on this line". Do not loosen without a sample (DS names it at the first weekly review).

9. **Headshots are ESPN's, not NBA's (2026-11-04).** Runner probe (probe/live_probe.py): cdn.nba.com JSON and nba.com 403,
   stats.nba.com times out, so no free reachable source maps ESPN ids to NBA person ids. ESPN's roster JSON carries an official
   a.espncdn.com photo keyed by the same ESPN id we use. Live box scores use ESPN for the same reason.
10. **DraftKings is hidden on the page by a text filter** (`noDK` in index.html): the slate still carries DraftKings links/clauses for
   Discord. If the engine's reason wording changes, re-check the page.
11. **Lab's only entry (Pinnacle judge) is 13-16 -2.94u live** (passed its Oct 25-27 discovery). Shown honestly; remove it if the
   Sharp drops the track.
12. **The live feeds are not official APIs.** ESPN's site.api is an undocumented public feed that could change shape or add
   restrictions (it also grades the picks, so a change would show in grading too). The NBA.com backup is untested against the real feed
   (403 to GitHub's servers; field names from its public format, parsed defensively; a surprise = "Live scores unavailable"). If ESPN
   stops answering browsers, the fix is a free relay. ESPN already refuses headless Chrome, so it filters bots; if that ever widens to
   phones, the page says "Live scores unavailable" and the relay; Cloudflare Workers would need Matt to create a free account.
13. Leftovers: branch `probe-box` (one-off ESPN box dump; deleting branches is blocked from the build sandbox, harmless) and
   `data/live.json` (unused since 2026-11-04 11 PM).

## 8. Rule-change log
| Date | Change | Why | Sample |
|---|---|---|---|
| 2026-11-04 ~11:50 PM (CEO, Matt's order; Builder) | **Too-late picks count like any other pick.** A pick Hard Rock moved or took down after it was shown is TOO LATE on Picks, then shows on Live and counts on the Record (headline, rows, cuts, calendar) at its posted price. Still out: under-fair picks (Matt, 10-30) and the Oct 28 `rule_change` withdrawals; scratches grade VOID. The -10u safety stop now reads the same set as the headline (it read 11.15u vs the headline's 12.34u before) | Matt: Miles Bridges was pulled after he had bet it; "we still treat it like any other pick... don't differentiate in the record" | Headline unchanged on the log at the time (23-8 +14.82u): the only graded line_gone pull (10-28) was under fair. Bridges U16.5 pts (line_gone 8:20 PM) counts when graded |
| 2026-11-04 ~11:50 PM (CEO, Matt's order; Builder) | **Live tab polls from the browser every 10 s** (ESPN, NBA.com backup) instead of the timer's data/live.json; timer `live` step removed. Display only | Matt: replace the slow live updates | CORS check + live-game check, section 5 / 9 |
| 2026-11-03 9:50 AM (CEO, Matt's order; Builder) | **v2.6: DraftKings is a button, not a pick book.** Hard Rock picks only (other books still don't matter); when DraftKings passes the same check on the same bet, the pick lists its price and gets a DraftKings button. Graded at Hard Rock's price | Matt, after seeing DraftKings-only picks were flat: "remove the draftkings check itself. However when they both agree provide the link for both books" | Replay Oct 26-Nov 2: 29 picks 23-6 +15.74u 79%; 20 with a DK button |
| 2026-11-03 7:55 AM (CEO, Matt's order) | **v2.5b: books independent** (each its own pick). Superseded by v2.6 before any pick | Matt | Replay: HR 29 23-6; DK 76 45-31 (DK-only 56 29-27 -0.99u) |
| 2026-11-03 7:30 AM (CEO, Matt's order; Builder, QA) | **v2.5: other books dropped from the rule; DraftKings added as a pick book** (customer fact: Hard Rock or DraftKings). Same line at the pick book and Pinnacle on both reads, Pinnacle 2+ pts, book price at or better than Pinnacle's fair; buttons only for passing books; graded at the best passing price; per-book Record rows. First picks Wed 11-04 (no games 11-03) | Matt: "As long as hard rock and pinnacle are showing the same lines I don't care about the other books... add draftkings... If hard rock's price is better than fair provide hard rock link, if draftkings provide draftkings, if both both" | Replay Oct 26-Nov 2: v2.4 23 18-5 +12.34u 78%; HR no others gate 29 23-6 +15.74u 79%; v2.5 84 52-32 +16.16u 62% (10.5 a night); DK-only picks ~59%. Flagged the hit-rate cost to Matt |
| 2026-11-02 11:45 PM (CEO, Matt's order; Builder) | **v2.4: the 11 AM read is back** from 11-04 (no games 11-03), paid from spare credits (`reads.spare` ["A"]); it never takes credits the B/C/D reads need this month, pauses with a page banner when spare runs out. Rules text updated. No pick-rule change | Matt: volume too low since the A read dropped on 11-01; "let's add the 11am back", he adds keys before they run out | Replay Oct 26-31 (2+, fair price): with 11 AM 3.7 picks a night 17-5 +11.09u 77% vs without 2.2 a night 9-4 +4.23u 69% |
| 2026-10-29 8:00 AM (CEO, Matt's order; Builder) | **v2.3: fair-price gate REPLACES the v2.2 gap gate** (`pin_solo.min_ev_vs_pin` 0.0; `min_gap_vs_pin` removed). Hard Rock's price must be at or better than Pinnacle's fair price on the side (EV vs Pinnacle >= 0%). Reason text, Discord and rules text now say "better than Pinnacle's fair price". Nothing was open to pull (no picks yet today); Oct 28's picks stay on the Record as shown | Matt: Run 7 showed v2.2 only reaches about fair; "integrate the fair price instead, I like the volume" (about 13 picks a busy night, 1-2 a quiet one) | Research Run 7 discovery Oct 25-28: at-or-better-than-fair 16 bets 12-4 +7.12u vs the rest 28 bets 16-12 +1.33u (Oct 28 alone 13 bets 9-4 +4.51u vs 17 bets 9-8 -0.93u). One lead, ~22 looks at 4 nights: judged forward on the live Record |
| 2026-10-28 6:15 PM (CEO, Matt's order) | **v2.2: Hard Rock must be 2+ pts better than Pinnacle's new price** (`pin_solo.min_gap_vs_pin` 0.02). Reason text shows the gap. Picks already shown tonight stay | Matt: Bane O2.5 threes was sent at HR -140 while Pinnacle was -134 (Pinnacle was catching up to the other books, not leading); "Hard Rock needs to still be better than Pinnacle" with a required gap | Replay Oct 25-27 by gap: 0+ 26 bets 19-7; 1+ 21 15-6; 2+ 13 10-3; engine replay v2.2 14 bets 10-4 +4.87u. Tonight 7 of 11 picks would pass |
| 2026-10-28 11:55 AM (CEO, Matt's order) | **v2.1: `pin_solo.others_max` 0.01 -> 0.02** (other books may move up to 2 pts the same way). Reason text says how far they moved | Matt: "pinnacle moves 2+ points and the other books move 2 or less" | Discovery: 31 bets 22-9 +9.74u (engine replay 29, 22-7 +11.75u); 26 of 29 on Oct 26 |
| 2026-10-28 11:30 AM (CEO, Matt's order; Builder, UX, QA) | **v2.0: live rule = Pinnacle moves alone (`pin_solo`); Gap + Guard off; Pinnacle as the price judge behind the scenes (Backstage tab)** | Matt: "shift the main process to pinnacle moves the odds alone... a behind the scenes tracking pinnacle as the price judge". Gap + Guard: 0 bets in 3 nights; Hard Rock NBA ~6% under market | Discovery only (Oct 25-27): F7 16 bets 11-5 +4.45u; F2b 6 bets 5-1 +3.18u. Book-by-book judges: only Pinnacle positive (research run 6) |
| 2026-10-26 11:40 PM (CEO, Matt's order; Builder, QA) | **v1.2: 3-pointers made added** (customer fact), same Gap + Guard, own model (section 7 item 3), reads cost 4 credits; in a full month the morning A read drops (C, B, D kept) | Matt: "include 3 pointers, those odds are typically a little better"; NBA main lines showed 0 gaps on Oct 26 | None yet; judged with the other markets |
| 2026-10-25 8:45 PM (CEO, Matt's order; Builder, QA) | **v1.1: points and assists added** (customer fact), same Gap + Guard thresholds, own model per stat (section 7 item 3), 1 side per player per market, no game or night caps (confirmed with Matt), reads cost 3 credits | Matt: "If we expand to points and assists..." then added 3 more keys (6 total) | None yet; all three judged TOGETHER at the 2026-11-16 checkpoint (Matt, 9:33 PM: "group all 3 together"); per-market buckets are for viewing only |
| 2026-10-25 (CEO, setup interview with Matt) | **v1.0.** Customer facts locked (section 1). Gap + Guard copied from NHL v3.3 for rebounds main lines; D read (20 min) added because Matt bets in the last hour; Questionable/GTD rule; parlays off | Setup interview; NHL template | None yet: first slate after the keys arrive |

## 9. Session log (newest first, one line each)
- 2026-11-05 2:10 PM (CEO, daily check): alive (chain link 219, status 1:50 PM, all steps ok, Actions green, pool 2,536, plan A/B/C/D for 2 games: ORL@PHX 9 PM, MIA@GSW 10 PM). Spare A read ran 11 AM (8 credits, Hard Rock all 4 markets); novig silent on it. 11-04: all 12 shown picks graded (8-4); all 49 shown picks on the Record graded. Rotowire showed confirmed starters last night. No unmatched names (odds or Rotowire), no unknown teams. 94 tests pass. No code changes.
- 2026-11-05 (Matt: Record page still too long): Record tab now one breakdown table at a time behind a chip switcher (market, over/under, edge, settled, price), Latest picks cut to 5. Display only.
- 2026-11-05 ~10 AM (CEO, Matt: tap a Record row to see its picks; no endless pick list): every cut row (market, over/under, edge, settled, price) carries `ids` in record.json and opens on tap to its picks, newest first, grouped by night (older month files load on demand). "Every pick" + "Show older" replaced by "Latest picks" (last 10, dated); older picks are reached by calendar day or a cut row. View only. Tests pass; checked at 360/380/414 + iPhone 13, no sideways scroll or errors.
- 2026-11-05 8 AM (CEO, Matt: over/under slice on the Record): new cut `side` ("Over vs under") in record.json summary.cuts, after By market; view only, same counted set as the headline. At the time: Over 8-1 +7.88u, Under 18-8 +9.29u. Tests pass.
- 2026-11-04 ~11:50 PM (CEO, Matt: live polling from the page every 10 s; then too-late picks count): checks first, as NHL did: CORS from GitHub's servers (ESPN pass, cdn.nba.com 403), ESPN full box dump on 3 finished games (PTS sums match team scores; same columns grading uses); official NBA box unreachable from every machine we have. Builder: timer `live` step, scripts/live.py and probe workflows removed; Live tab polls ESPN scoreboard + summaries every 10 s while open and visible, NBA.com backup, "Live scores unavailable" when both fail, "Updated Xs ago", pauses hidden, stops when nothing is live. Too-late picks shown on Live and counted on the Record; safety stop reads the headline set. 92 tests; local sweep 18 fixture sets x 6 tabs x 4 sizes, 0 sideways scroll / page errors. Live-game check on the public site: first run in headless Chrome failed (ESPN blocks headless; the page correctly said "Live scores unavailable"); WebKit + normal Chrome passed on LAL@SAC and MIA@LAC in Q3 (section 5).
- 2026-11-04 ~9:20 PM (CEO, Matt: bring NHL's 11/4 redesign over; Builder, QA): page rebuilt on NHL's 11/4 page. Rail tabs Picks · Live · Games · Record · Lab · Info; Ballpark light theme, bundled Graduate / IBM Plex Sans / Plex Mono; dark mode and Backstage gone. Picks = unstarted picks in 2-column tiles (photo, bet, Hard Rock price, chance vs needed; tap: reason, Early > Injury report clear > Starters confirmed > Locked stepper, Hard Rock button), NEW corner label + "Added HH:MM", TOO LATE navy stamp for status and line_gone pulls ("Got X earlier? Keep it. Don't bet it now."), Out scratches hidden from Picks and Live. Live = started picks, "Tonight W-L · ±u", in-game first, finals sink with WON/LOST/VOID, stat-vs-line tracker with HIT/LOST mid-game, quarter/clock/score, old data said plainly. Games = checks only. Record = calendar (red up, slate down) + cuts (market, edge vs Pinnacle fair, settled when shown, price band; small-sample labels) + full list. Lab = Pinnacle judge track. Info = status rows, rules, 21+ / 1-800-GAMBLER. No pick, grade, Record-counting or Discord change; events.jsonl untouched. Source probe on the runner: ESPN summary live fields verified on PHI@DET / ATL@WSH in progress; NBA official sources blocked (section 7 item 9). QA (fresh): SHIP, 336 views (all fixtures + real data x 6 tabs at 360/380/414 + iPhone 13), no sideways scroll, no JS errors; 3 lows fixed (malformed box block, skeleton gradient), 2 noted (section 7 items 10-11). 90 tests.
- 2026-11-04 2:10 PM (CEO, daily check): alive (chain link 182, status 2:00 PM, all steps ok, Actions green, pool 2,712, plan A/B/C/D for 14 games). v2.4 spare A read ran 11 AM (56 credits; Hard Rock all 4 markets on every game). No games 11-03, so nothing to grade and no Rotowire confirms expected; all 37 shown picks on the Record graded. Unmatched Rotowire: Diop, Tomlin (harmless); no unmatched odds names, no unknown teams. Tests pass. No code changes.
- 2026-11-03 ~5:15 PM (CEO, Matt: "There should not be a daily budget"): removed the per-day credit cap (`budget_today`) from the
  plan and the read loop. Found while checking v2.4: on a big slate the spare 11 AM reads counted against the day's cap and could
  block the 90-min read of the latest games (C/D were exempt, B was not). Now every planned read runs while credits last; spare reads
  keep their month reserve check. Game lines (spreads/totals, ~2 credits a check for all games) quoted to Matt, not built: awaiting
  his pick (every check vs 11 AM + 45 min). 74 tests pass.
- 2026-11-03 2:10 PM (CEO, daily check): alive (chain link 148, status 2:00 PM, all steps ok, Actions green, pool 2,768). No games today (Election Day), so no reads and no A read by design; v2.4 A read resumes 11-04. 11-02: 15 games, all 45 B/C/D reads ran; 1 shown pick graded (W +1.25u); all 37 shown picks on the Record graded. Rotowire showed confirmed starters last night (30 confirmed states). No unmatched names (odds or Rotowire), no unknown teams. 74 tests pass. No code changes.
- 2026-11-03 ~9:55 AM (CEO, Matt: drop DraftKings as a pick book, keep its button when both agree): v2.6 (`customer.books`
  ["hardrock"], `pin_solo.link_books` ["draftkings"], `engine.pick_books`, DK row merged into the HR pick's `books`, line_gone on Hard
  Rock only, replay pick books only, rules text + page line). 74 tests pass. First picks Wed 11-04.
- 2026-11-03 ~7:55 AM (CEO, Matt: Hard Rock and DraftKings operate independently): v2.5b built (`solo_moves` one row per book,
  `pick_id` book suffix, per-book one-per-player/market, replay keyed per book). 75 tests pass. Told Matt the DK-only stream is flat.
- 2026-11-03 ~7:30 AM (CEO, Matt: drop the other books, add DraftKings): built v2.5 (`engine.solo_moves` per pick book, `customer.books`,
  `pin_solo.others_max/min` null, `latest_fetches` counts DK-only reads, line_gone only when every shown book drops it, publish/Discord
  buttons only for passing books at their frozen price, page "Bet at DraftKings -105 / Hard Rock -110 or better", per-book Record rows).
  Replay data/replay/pin_solo.json NOT regenerated (still the v2.3/2.4 rule on Oct 25-27). 75 tests pass; 380px render checked.
- 2026-11-02 ~10 PM-11:45 PM (CEO, Matt's volume questions; research only unless noted): replays (Oct 26-Nov 2, no injury replay)
  of the Pinnacle-alone signal by move size (1+..7+) x Hard Rock check (fair / posted / none): 2+ fair 23 18-5 +12.34u; 2+ posted
  160 90-57 +19.68u 61%; 2+ none 179 98-65 +18.66u; 4+ posted 35 21-9 +9.02u 70%. Rebounds held up without the fair check at 2-3 pt
  moves (25-13) but not at 3+. DraftKings at/better than Pinnacle posted on 87% of Hard Rock's posted-pass bets; same bets DK +13.17u
  vs HR +12.16u. Non-consecutive windows (Oct 26-31): all pairs at 2+ fair 26 19-6 +12.14u vs consecutive 22 17-5; 11 AM is the
  volume lever. CEO + team recommendation (not live): step 1 bring back 11 AM (DONE, v2.4); step 2 a "big move" lane (4+ pts, Hard
  Rock at or better than Pinnacle's posted price, own Record bucket): Oct 26-31 6.0 picks a night 26-10 +13.56u 72%, to be tested on
  past seasons with Matt's one-time historical key first (never stored; 5M plan ~$119 covers 3 seasons, ~445-590K credits). Matt
  also asked whether 11 AM is the best first time: untestable on live data; test 9 AM-1 PM and 3h-before with the historical key.
  Built v2.4 (`reads.spare`, `odds.spare_ok`, pause banner, rules text); 73 tests pass.
- 2026-11-02 ~9:00 PM (CEO, Matt: tap-to-bet buttons for Hard Rock and DraftKings): ported NHL's `hardrock_slip`/`bet_links`/`betRow`.
  `normalize` keeps DraftKings outcome links on non-A reads; publish adds `links` to open picks from the newest read (raw `link` no
  longer published); Discord pick blocks end with `[Hard Rock +115](<url>) · [DraftKings -110](<url>)`. Fake world uses real link
  shapes; new tests/test_bet_links.py (6). 70 tests pass. Rendered at 380px dark: two buttons, one-button and no-button cards OK, no
  horizontal scroll, no console errors. Asked Matt to tap the first DraftKings button.
- 2026-11-02 ~7:05 PM (CEO, Matt: show when a game was checked and when it is settled with 0 picks): slate games now carry
  `checks` (flag reads that came back), `last_check_at`, `final` (started, last planned check done, or inside latest_min) and
  `next_check_at`; the Games list shows a small muted line ("✓ Checked 6:30, 7:15, 7:40 PM · done, no picks" / "Checked 6:30 PM ·
  next 7:15 PM"), right side "none yet" until settled. 64 tests pass; checked at 380px.
- 2026-11-02 2:15 PM (CEO, daily check): alive (chain link 113, status 2:10 PM, all steps ok, Actions green, pool 2,948, plan B/C/D for 15 games; no A read by design in a full month). Commit gaps in the log are the heartbeat (slate unchanged -> push every 20 min), not failures. 11-01: 0 picks, nothing to grade; all 36 shown picks on the Record graded. Rotowire showed confirmed starters last night (16 confirmed states). Unmatched Rotowire: Tomlin (harmless); no unmatched odds names, no unknown teams. 63 tests pass. No code changes.
- 2026-11-02 ~12:20 PM (CEO, weekly review #2): alive (chain link 109, status 11:40 AM, all steps ok, pool 2,948, plan B/C/D for 15 games tonight). DS: 36 live picks shown, all graded, 23-13 +7.55u (BE 54.3%, p 0.16); at/above fair 19 14-5 +8.48u; under fair (all Oct 28) 17 9-8 -0.93u; v2.3 6 picks 5-1 +3.97u. CLV at the last read (30 measured, 28 pre-v2.3): vs Pinnacle fair -0.98 pts (ev>=0 picks -0.17, 12/14 beat; ev<0 -1.69, 0/16), vs consensus -2.95 (0/30: the other books never follow). Near-misses since v2.3 that failed only the fair gate: 78, 44-32 +4.73u, but those within -2% went 9-12 -4.47u, so no loosening. pin_judge watch 8-11 -3.19u (discovery not holding; no promotion). Coverage: all 9 books all 4 markets (BetMGM patchy); Pinnacle has Hard Rock's line ~60% (assists ~48%): still the volume limit. Credits: 12 a game (B/C/D), November ~2,584 of 3,000; 4 credits on key 2 have no ledger entry (watch). Calibration buckets n 2-15: noise. Sharp: no rule change (no slice big enough; Matt kept v2.3 this morning); stop rule not triggered; checkpoint stays 11-25. UX/Builder: fixed stale v2.2 rule text ('signal, not a price gap'), reads line (11 AM look only when credits allow), Backstage 'Pinnacle's fair price', Record tile font clamp. Not done: headline replay split / under-fair picks on the page (Matt's own Oct 30 call), Games list collapse, jargon (low). QA (fresh, Chromium 380+320): SHIP; 63 tests pass.
- 2026-11-02 ~10:50 AM (CEO, Matt: why no bets Sunday 11-01): diagnosed, no change. 4 games, all 12 reads ran (B/C/D, Hard Rock all 4 markets, pool fine). 15 Pinnacle 2+ pt moves found; 13 failed the v2.3 fair-price gate (Hard Rock worse than Pinnacle's fair; closest -0.3% and -0.4%), 2 failed because the other books moved too. 0 picks. Volume since v2.3: 10-29 1, 10-30 3, 10-31 2, 11-01 0. The 11 AM A read was dropped for the full-month plan, so each game has 2 comparisons (B to C, C to D) instead of 3. Matt chose to KEEP the rules unchanged (11-02 11:03 AM): fair-price gate stays at 0.0, no A read, no new keys. Revisit only if he asks or at the 11-25 checkpoint.
- 2026-11-01 2:10 PM (CEO, daily check): alive (chain link 78, status 2:00 PM, all steps ok, Actions green, keys refilled Nov 1: pool 2,992, plan B/C/D for 4 games, A read dropped by design in a full month). 10-31: both shown picks graded (2-0); all 36 shown picks on the Record graded. Rotowire showed confirmed starters last night (28 confirmed states). No unmatched names (odds or Rotowire), no unknown teams. 63 tests pass. No code changes.
- 2026-10-31 2:10 PM (CEO, daily check): alive (chain link 43, status 1:50 PM, all steps ok, Actions green, pool 2,375 (key 1 at 3 credits, too few for a 4-credit read, harmless; refill expected Nov 1), all 4 reads planned for 7 games). A read ran 11 AM (7 games x 4 credits, Hard Rock all 4 markets on every game); first B read 1:30 PM. 10-30: all 3 shown picks graded (2-1); every shown pick on the Record graded. Rotowire showed confirmed starters last night (20 confirmed states). Unmatched Rotowire: Tomlin (CLE bench, harmless); no unmatched odds names, no unknown teams. 63 tests pass. No code changes.
- 2026-10-30 2:10 PM (CEO, daily check): alive (chain link 9 since the 7 AM restart, status 1:50 PM, all steps ok, Actions green, pool 2,527 (key 1 down to 27, keys 2-6 full), all 4 reads planned for 10 games). A read ran 11 AM (10 games x 4 credits, Hard Rock all 4 markets on every game). 10-29: the 1 shown pick graded (W +1.35u); all 31 shown picks on the Record graded. Rotowire showed confirmed starters last night (6 confirmed states, 3 games). No unmatched names (odds or Rotowire), no unknown teams. 63 tests pass. No code changes.
- 2026-10-30 ~7:15 AM (CEO, Matt: remove everything except the strategy's record, include the replay): the page's Record is now the STRATEGY record: picks at or better than Pinnacle's fair price, live plus the Oct 25-27 replay (entries tagged REPLAY, read from data/replay/pin_solo.json by `record.py`). Pulled and under-fair picks are no longer on the page or in its totals; they remain only in data/record/events.jsonl (byte-identical, nothing purged; a true purge needs Matt's explicit ask + archive per section 5). Headline 13-4 +8.47u (Oct 26 2-0, Oct 27 1-0 replay; Oct 28 9-4, Oct 29 1-0 live). Combined strip and separate replay section removed from the page (no double count). Also FIXED a page-breaking JS error (unescaped apostrophe in the Record note) from the 11:30 PM Oct 29 push: the page script did not load from then until this fix. Tests 63 pass, page rendered in Chromium at 380px, no script errors.
- 2026-10-29 ~11:30 PM (CEO, Matt: Record should show only the better-than-fair picks): `record.py` no longer counts a pin_solo pick shown with ev_vs_pin < 0 (headline, nights, per-market and window rows); they stay listed, tagged NOT COUNTED, with their own row "Under fair price (not counted above)". Display only: data/record/events.jsonl is byte-identical, every pick still exactly as shown. Live Record now 10-4 +5.86u (Oct 28: 9-4, Oct 29: 1-0); with the Oct 25-27 replay (3-0) the combined card reads 13-4. 63 tests pass.
- 2026-10-29 ~5:35 PM (CEO, Matt: Home Screen still showed the old icon): iOS caches the icon by URL, so the page now points at a new file name `icons/apple-touch-icon-v2.png` (root `apple-touch-icon.png` kept for iOS default lookup). To bust the cache again, bump the -vN name. Matt must delete the old Home Screen shortcut, clear Safari website data for the site, then re-add.
- 2026-10-29 ~5:20 PM (CEO, Matt: use his hooded-flame basketball image as the Home Screen icon): added `apple-touch-icon.png` (180), `icons/` (favicon 32, 192, 512) and `manifest.webmanifest`, linked in index.html `<head>`. Black background, no transparency, so iOS shows it clean. Page code unchanged; 63 tests pass. If Matt already added the site to his Home Screen, he must delete and re-add it to pick up the icon.
- 2026-10-29 2:15 PM (CEO, daily check): alive (chain link 145, status 2:00 PM, all steps ok, Actions green, pool 2,603, all 4 reads planned for 3 games). A read ran 11 AM (3 games x 4 credits, Hard Rock + all 9 books on every game). 10-28: all 30 shown picks graded (26 counted 17-9 +5.93u; 4 pulled 1-3). Rotowire showed confirmed starters last night (48 confirmed states). Unmatched Rotowire: Tomlin (CLE bench, harmless); no unmatched odds names, no unknown teams. 63 tests pass. No code changes.
- 2026-10-29 ~8:30 AM (CEO, Matt: replace the gap gate with the fair price): v2.3 shipped. engine `solo_moves` gate `min_ev_vs_pin`, reason/Discord/page-rules text, tests (63 pass, new test: better than Pinnacle's posted price but under fair -> no pick), replay regenerated (Oct 25-27: 3 bets 3-0 +2.61u; the Oct 28 live picks stay as shown under v2.2). The mid-night rule-change pull still exists for `min_gap_vs_pin` only; it was not needed (no picks open today).
- 2026-10-29 ~8:10 AM (CEO as Researcher, Matt: cut the daily pick count by a calculated method, no hard limits like max per night/game/player): Run 7, discovery Oct 25-28 (74 bets, 40 on the live rule). No candidate, no product change. One lead: only keep picks where Hard Rock's price is at or better than Pinnacle's NEW fair (EV vs Pinnacle >= 0): 16 bets 12-4 +44.5% vs the rest +0.7% (p 0.05, ~22 looks, 13 of 16 on one night); leaves 1-2 picks on quiet nights, ~13 on busy ones. Scores on move strength, track record, overlap and a composite did not select. Registered forward as F9 (no code needed). Matt declined a model tag (earlier today: model gate cut winners as often as losers). research/LOG.md, HYPOTHESES.md, code/run7_reduce.py.
- 2026-10-28 ~6:25 PM (CEO, Matt: re-send the new list, take the old one off the site): open pin_solo picks that fail the v2.2 gap
  at their own shown prices are pulled by the timer (code rule_change; on the Record as pulled, hidden from Tonight and Discord).
  Tonight's Discord sent-list reset in data/state/notified.json so the next run sends one NEW PICKS message with the v2.2 list.
- 2026-10-28 ~6:15 PM (CEO): v2.2 gap gate (Matt). Replay regenerated: 14 bets 10-4 +4.87u. Tests 61 pass.
- 2026-10-28 ~6:15 PM (CEO, Matt): every Pinnacle pick tagged with its window (11 AM → 90 / 90 → 45 / 45 → 20 min); Record rows per
  window + combined card table per window (live, replay, all). Picks shown before the tag get it from their flag read (log untouched).
  First live night: 10 picks at the 90-min checks by 5:50 PM. Replay by window: 15-6 / 4-0 / 3-1. Single 11 AM→20 min comparison
  (asked by Matt): 19 bets 14-5 +7.56u; 11 AM→45: 23 bets 19-4 (more slices = more luck; not adopted).
- 2026-10-28 ~5:45 PM (CEO, Matt: the bet link doesn't add the bet to the slip, remove it): removed the "Bet on Hard Rock" button from the page and the "Bet slip" line from Discord picks. Slate data still carries `link` (unused). Section 7 item 8's note on deep links no longer applies to the UI. 60 tests pass.
- 2026-10-28 2:10 PM (CEO, daily check): alive (chain link 108, status 2:00 PM, all steps ok, Actions green, pool 2,759, all 4 reads planned for 12 games). A read ran 11 AM (12 games x 4 credits, Hard Rock + all 9 books on every game). 10-27: 0 live picks (Gap + Guard), nothing to grade (no events.jsonl yet); v2.1 Pinnacle rule's first live B/C/D reads are tonight. Rotowire showed confirmed starters last night (8 confirmed states). Unmatched Rotowire: Diop, Tomlin (CLE bench, harmless); no unmatched odds names, no unknown teams. 60 tests pass. No code changes.
- 2026-10-28 ~12:50 PM (CEO, Matt: show the new strategy's history together): `scripts/replay.py` -> data/replay/pin_solo.json (same
  code path, Oct 25-27, injuries not replayed): 29 bets 22-7 +11.75u. Record tab: combined card (live Record + replay, live marked
  official) and a Replay section. The Record itself is untouched (append-only, live picks only). Checked at 380px.
- 2026-10-28 12:21 PM (Matt): research paused. No Researcher schedule; data keeps collecting for later.
- 2026-10-28 ~11:55 AM (CEO): v2.1 (Matt): others may move < 2 pts. Engine replay Oct 25-27: 29 picks 22-7 +11.75u. Tests pass.
- 2026-10-28 ~11:30 AM (CEO): v2.0 shipped. Research runs 1-6 (research/LOG.md), each book as judge (only Pinnacle +), Matt chose
  Pinnacle-moves-alone live + Pinnacle price judge behind the scenes. UX: pin_solo card + Backstage tab (380px checked). QA (fresh): SHIP
  WITH FIXES, blocker fixed (Hard Rock must quote the same line on both reads, replay now = the 16 research bets), reason wording, watch
  errors soft. 59 tests pass. Matt offered: switch to any-Pinnacle-move (46 bets 31-15 in discovery); tracked in shadow meanwhile.
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
