# TEAM.md: Prop Check NBA operating doc

Read this first in every session. Update it last. Every chat in the NBA project starts by attaching
MSasportas/prop-check-nba (add_repo, push access), cloning it and reading this file.

Live page: https://msasportas.github.io/prop-check-nba/ · Repo: MSasportas/prop-check-nba (public)
Sister company of Prop Check NHL (MSasportas/prop-check-nhl): own CEO, team, repo, Record and odds key pool. The NHL repo is the
template and is READ ONLY from here. Never push to it.

## 1. The product
Every NBA game day: every rebounds leg that qualifies at a real Hard Rock (`hardrockbet`) price, ranked best first, each with
the price, our chance vs the price's break-even and a one-line plain reason. The page updates through the day; each pick shows how
settled it is (Early / Injury report clear / Starters confirmed, then Locked) and pulled picks stay visible with the reason and what it
means if Matt already bet. Dark, phone first (~380px). The Record is the scoreboard. Parlays are not offered (Matt, setup).

**Customer facts (fixed; locked in the setup interview 2026-10-25, Matt):**
| Fact | Locked value |
|---|---|
| Book | Hard Rock Florida only. A pick needs a real Hard Rock number |
| Market | **Player rebounds only. Main line only (no alt ladders). Over and under.** Everything else is out |
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
| Market | Hard Rock `player_rebounds` (the main line the feed lists, one per player), over and under. Alt lines are never read |
| Step 1: the gap | All of: Hard Rock EV vs the market fair >= **+3.0%**; >= **4 other books** priced the same player, same line, both sides, fresh, hold 0-15%; **market fair = median** of the books' proportionally de-vigged chance (even count: mean of the middle two); **Pinnacle present** with both sides and Pinnacle-fair EV on Hard Rock's price >= 0.0%; Hard Rock price **-200 to +200** |
| Step 2: the guard | final = 0.8 x market fair + 0.2 x (model chance + offset). Passes iff final EV >= **+2.0%**. No model for the player = no pick. Offset frozen (section 7 item 3) |
| Which reads can pick | B (90 min), C (45 min) and D (20 min before tip) reads that carry other books. The morning A read is a baseline only |
| The pick | The first passing read makes the pick and **freezes its price**. That price is shown, sent to Discord and graded: flat 1 unit. Later prices never change it |
| Eligibility | >= 10 games of history (2025-26 + 2026-27 box scores); listed **Out or Doubtful -> never**; **Questionable / Day-to-day / GTD -> no new pick** until he drops off the report or is in a confirmed starting five; missed his team's last game -> waits for confirmed starters (and must start); minutes last 3 games < 60% of his recent average -> no pick (role or restriction changed) |
| Settled chip | **Early** (he or someone in his team's top 7 by recent minutes is Doubtful / Questionable / GTD) -> **Injury report clear** (none of them is; Out and Probable are settled) -> **Starters confirmed** (Rotowire shows both teams' starting fives as confirmed) -> **Locked** at tip |
| Pulls | Later reads only PULL: Hard Rock's price changed and step-1 EV < **+1.5%**; fewer than 4 books; Pinnacle gone or sign flipped; step 2 fails; line removed; player listed Out, Doubtful, Questionable or GTD after the pick, unless he is in a confirmed starting five (every run). Teammate news does not pull by itself: the next read re-prices it. Pulled picks stay on the page and in the Record, graded at the frozen price, counted under "Pulled". **Every pull says what happened and what it means if Matt already bet.** No pulls after tip. Once the D read is done only an injury pull can happen ("Price final") |
| Caps | 1 side per player. No per-game or nightly cap (NHL v3.1 rule, Matt's preference: every qualifying leg is shown, ranked by final EV) |
| Parlays | Off (customer fact) |
| Grading | When ESPN marks the game final. Overtime counts. Did not play = void. Graded at the frozen price, flat 1 unit |
| Odds reads | A 11 AM (or 3h before the first tip), B 90 min, C 45 min, D 20 min before each game. Rebounds only = 1 credit a read. Priority when credits are short: C, B, D, A |
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
  keys only by number. Page warns when the pool is low (allowance < 2 credits a game) or when every key is refused.
- **Feed limits (checked 2026-10-25):** The Odds API free Starter plan = 500 credits a month per key. Event odds cost markets x regions;
  up to 10 bookmakers in `bookmakers=` bill as one region, so Hard Rock + 9 other books for rebounds = 1 credit a read. The events list is
  free. Need: ~4 reads x ~225 games a month ≈ 900, plus menu and retries ≈ 1,000. **Matt was asked for 3 keys (1,500 a month).**
- **Other books asked (9, same credit):** draftkings, fanduel, betmgm, espnbet, pinnacle, betonlineag, betrivers, novig, prophetx.
  Which return NBA rebounds is unverified until the first read; a silent book costs nothing; swap per NHL item 24 (quality sharp books).
- **Discord:** `scripts/notify.py`, secret `DISCORD_WEBHOOK`. Sends NEW PICKS (batched), PULLED (only picks already sent, before tip, with
  the if-bet line), PRICE FINAL, ACTION NEEDED (keys refused / pool low, once a day each), a one-time hello. Never no-pick nights,
  heartbeats, grading or errors. Quiet 12:30-9:00 AM ET. Max 12 messages a day.
- **Debug:** `python scripts/run.py --explain` lists every rebounds line on the latest reads and the first reason it did not pass.
  Tests: `python -m unittest discover -s tests`. Env: `PC_NOW`, `PC_DATA_DIR`, `PC_ODDS_FIXTURE_DIR`, `PC_ESPN_FIXTURE_DIR`.

## 6. Reviews (scheduled tasks; each reads this file first and updates it last)
- **Daily check, 2:07 PM ET:** chain alive, A read ran, failed steps, unmatched names, grading done for last night; fix what's broken; no
  rule changes.
- **Weekly team review, Mondays 11:13 AM ET:** Sharp, Data Scientist, UX, Builder, QA on the Record and the odds log; first one 2026-11-02.

## 7. Known gaps and risks
1. **Edge vs the book is unproven.** Gap + Guard is a hypothesis carried over from NHL (live there since 2026-10-20, no verdict yet). NBA
   rebounds props have more books and sharper pricing than NHL shots, so expect thin nights. Checkpoint 2026-11-16 (3 weeks): the DS reads
   CLV on every flagged gap and the graded Record. Stop rule: mean CLV <= 0 at >= 25 measured gaps, or units <= -8 -> the Sharp pauses
   new picks and logs it in section 8.
2. **Starting lineups source = Rotowire** (scraped HTML; layout change or block = the chip stops at Injury report clear and the page
   says so). "Confirmed" was not seen live yet (the probe ran at 10:49 AM, all Expected): verify `lineup__status is-confirmed` on the
   first evening run.
3. **Model (guard only):** fitted by the DS 2026-10-25 on 2025-26 box scores, walk-forward (`research/calibrate.py`): 18,841
   player-games Dec-Apr, test line = his last-10 average as an x.5 line. 16 variants tried; chosen disp 1.15, opponent factor exp 1.0,
   no back-to-back cut, rpm half-life 20: log loss 0.6686 vs base 0.6877, bias -0.05 pt, calibrated in every 10-pt bucket. **Offset =
   0.0** (bias ~0). Not tested against book lines (no historical Hard Rock rebounds prices); refit only with a named sample.
7. Official NBA injury report PDF not parsed (Rotowire mirrors it). Build only if Rotowire proves unreliable.
4. Name matching: accents, Jr./III and dots are normalized; within the two teams playing only. Unmatched names are listed in
   status.json and skipped, never guessed.
5. The ESPN tip time is used for lock (games often tip ~10 min later): conservative.
6. Keys refill on the 1st (assumed, as NHL). The pool covers ~4 reads a game with 3 keys.

## 8. Rule-change log
| Date | Change | Why | Sample |
|---|---|---|---|
| 2026-10-25 (CEO, setup interview with Matt) | **v1.0.** Customer facts locked (section 1). Gap + Guard copied from NHL v3.3 for rebounds main lines; D read (20 min) added because Matt bets in the last hour; Questionable/GTD rule; parlays off | Setup interview; NHL template | None yet: first slate after the keys arrive |

## 9. Session log (newest first, one line each)
- 2026-10-25 ~10:30 AM setup (CEO): interview done (rebounds only, main line, over+under, -200, parlays off, last hour before tip,
  regular season, new Discord channel). Old NBA build wiped (repo, secrets and Pages kept). Seed + source probe workflow pushed.
  Asked Matt for 3 new free odds keys and the Discord webhook.
