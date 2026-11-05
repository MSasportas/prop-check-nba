# Prop Check NBA: project brief for Claude Code

Read this first. It is a handoff from the Claude.ai NBA project. The repo's TEAM.md is the source of truth once the repo is connected. This file was written from the project notes as of 2026-11-05 and could not be checked against TEAM.md, so treat anything marked (verify) as unconfirmed.

## What this is

- Prop Check NBA: NBA picks and small parlays for Matt (the customer). Sister product to Prop Check NHL, built on the NHL template.
- Repo: MSasportas/prop-check-nba (public, static site on GitHub Pages, free cloud timer for data, odds, lineup checks, freezing and grading). Eastern time.
- Template to copy, read only, never change or break: MSasportas/prop-check-nhl (its TEAM.md, Record rules, page layout, key-pool setup, gap and gate strategy).
- Matt is a casual bettor on his phone. Not an engineer. He doesn't run or approve anything. Keep his messages short, direct, tables first.

## Who runs it

A CEO agent owns the product end to end and runs subagents: Sharp (betting standard), Data Scientist (data, samples, judging results), UX, Builder, QA. They decide and ship without asking Matt. Every rule is theirs to change, except the fixed items below.

## How the CEO is judged

1. The picks hit. Fewer picks beats picks that miss.
2. Always current when Matt opens it. Anything missing or stale is stated plainly.
3. A usable set of picks most nights.
4. Readable on a phone in seconds.

## Fixed (team cannot change)

- Matt's betting facts and locked markets.
- The Record: every pick and parlay exactly as shown to Matt, graded after the game at the posted price. Append-only. Nothing edited or dropped later. Pulled picks stay in the Record. The Record is the only reporting Matt wants.

## Betting rules (as of Nov 2026)

- Books: Hard Rock (Florida) and DraftKings. Live rule: Hard Rock or DraftKings must show the same line as Pinnacle. A link goes to whichever book's price beats Pinnacle's fair price (both if both). No link to Hard Rock's bet slip.
- Pinnacle is the price judge (fair price, margin removed). Hard Rock's or DraftKings' price must be at or better than Pinnacle's fair price to be a live pick.
- Live pick trigger (current): Pinnacle moves the line, and the book's price is still at or better than fair. The old 2-point gap gate was replaced by the fair-price rule. Other books no longer matter.
- No hard caps on picks per game, per night, or per player. Volume is controlled by a calculated score of which picks are better over the long run.
- Parlays: 2-3 legs (NHL default). Matt can't combine two players from the same game on Hard Rock. Round robins of picks are under consideration (not decided).
- Leg price floor: no single leg worse than -200. Plus money is fine. (NHL default; confirm for NBA.)
- Stake: $5 a unit on straight picks.
- Timing: Matt bets in the last hour before tip-off (regular season only). A 11 AM odds check exists to raise daily volume.

## Markets (locked)

- Player props: rebounds, points, assists, 3-pointers made (added Oct 26).
- Main lines only (no alt ladders; alt-ladder prices were too poor).
- Over and under both count.
- Record must show over vs under split, and bucket by market to see which performs better.

## Page

- Dark mode is not the current spec. Match NHL's Nov 4 redesign: Ballpark light theme, side-rail tabs Picks / Live / Games / Record / Lab / Info. (Earlier notes said dark mode; the Nov 4 note supersedes. Verify.)
- Phone width. Readable in seconds.
- No DraftKings link on the page. No Hard Rock bet link on the page or in Discord picks.
- Picks tab: each pick shows its Hard Rock or DraftKings number, a short plain reason, and how settled it is (early, lineup or availability confirmed, as the NBA equivalent of goalie confirmed).
- Pulled picks (book moved the odds after Matt bet, e.g. Miles Bridges): show TOO LATE on Picks, then appear on Live and count on the Record like any other pick.
- Live tab: refreshes every 10 seconds from the page itself.
- Record tab: rows expand to show their picks. No long doom-scroll pick list.
- Pick count and suggested 2-3 leg parlays come from the top legs.
- Page warns when the odds key pool is low. Anything missing or stale is stated plainly.

## Discord

- Alerts go to a separate NBA Discord channel, not the NHL one. No model tags on picks (declined).

## Odds and data

- Feed: hardrockbet (Hard Rock). DraftKings and Pinnacle are price references.
- Keys live only in GitHub Secrets as an NBA-only pool that rotates. Never in the repo, the page, or a log.
- Free data sources only. A paid source is the one thing to bring to Matt.
- Before building, check the feed's limits and state exactly how many keys NBA needs (not yet confirmed).
- Matt will add more keys before credits run out late in the month (Nov 2026).

## Season and research

- Regular season only.
- An NBA research agent (like NHL's) was requested Oct 28 and paused once the live rule was running. Resume only if the CEO decides.
- Prefer finding an edge by comparing books before any model-based approach.

## Open items (not yet locked)

- Whether NHL's -200 leg floor and 2-3 leg parlay limit stay for NBA (verify).
- Whether parlays are on or off for NBA (Oct 25 note said off; later notes don't say; verify).
- Round robins: considering, not decided.
- NBA-specific lineup and injury timing details (the "goalie confirmed" equivalent) to lock.
- Hard Rock-only vs Hard Rock or DraftKings: current rule is Hard Rock or DraftKings. Verify this is final.

## Change log (summary of Matt's rule changes)

- Oct 25: restart on NHL template. Rebounds only, main line, over and under, no leg worse than -200, parlays off, regular season only.
- Oct 25: markets widened to rebounds, points, assists. No limit on picks.
- Oct 26: 3-pointers made added.
- Oct 28: live rule "Pinnacle moves the odds alone," later widened to Pinnacle moves 2+ points while others move 2 or less. No Hard Rock bet link.
- Oct 29: picks reduced by a calculated score, never hard limits. No model tag. Live rule switched to Hard Rock price at or better than Pinnacle fair price (replacing the 2-point gate).
- Oct 30: Record is the strategy's track record only: picks at or better than fair price, replays included. Under-fair removed.
- Nov 2: 11 AM odds check restored.
- Nov 3: Hard Rock or DraftKings only, with link to the book that beats fair price.
- Nov 4: $5 units. Round robins considered. Page redesign to NHL's Nov 4 layout. Pulled picks show TOO LATE, then appear on Live and the Record. Live tab refresh every 10 seconds.
- Nov 5: over vs under split on Record. Record rows expand to picks. No long pick list.
