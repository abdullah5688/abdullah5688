# NFL Prop Agent — Autonomous Runbook

This is the procedure the scheduled agent follows every Sunday. The analysis
rules themselves live in `ENGINE_PROMPT.md` and are not changed here; this
file only says where to get the data and how to deliver the report.

## 0. Is there anything to do?

1. Get the current time: `TZ=America/New_York date`.
2. Pull today's schedule:
   `curl -s https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`
   Keep only events whose `status.type.state` is `pre` (not started).
3. If there are no pregame NFL games today (offseason, bye, or all games
   started), finish with a one-line report: "No pregame NFL games — no run."

## 1. Odds (FanDuel first)

Run `python3 fetch_odds.py --out reports/` (stdlib only). The Odds API key is saved as a network secret on
this environment and injected by the proxy into the `x-api-key` header, so no
variable is needed. Each run costs about 12 credits per game, and each re-run costs the same again. It pulls FanDuel, DraftKings and BetMGM
prices for passing/rushing/receiving yards, receptions, rushing attempts and
passing attempts, plus alternates, for every game that has not kicked off.
It writes a CSV with the book, the market, the player, the side, the line, the
American odds and the book's own `last_update` time.

* If the script exits saying that the key was rejected (401), or that the quota was hit,
  **every candidate is Research Only**. Say so in section H. Never fill in
  prices from memory or from articles.
* Treat only rows with `book == fanduel` as FanDuel prices. DK/BetMGM rows are
  for comparison and must be labelled as such.
* Re-run the script right before writing the final report ("recheck prices")
  and flag any line that moved.
* The Odds API does not price parlays/SGPs, so combined quotes are always
  **Provisional / unverified**: state that.

### FanDuel "X+" alternate ladders (Alt Rushing / Alt Receiving / Alt Passing, etc.)

The `*_alternate` markets are FanDuel's "X+" ladders as the app shows them.
The API returns each rung as an `Over` at `X - 0.5` (Over 59.5 = "60+").
For every candidate player:

* Evaluate **every rung** of the ladder, not just the main O/U line, and
  compute the season / last-5 / last-10 hit counts at each rung.
* Write selections the way FanDuel shows them ("Derrick Henry 60+ rush yds, -300").
* The -350 price cap still applies. Rungs priced shorter than -350 (e.g. 40+ at
  -1100) are ineligible, but you can mention them as context.
* For each player, pick the rung with the best balance of hit rate and price, and show
  the rungs on either side of it in the alternate-line comparison.
* Ladders are overs only. Unders come only from the main O/U markets.

## 2. Stats, injuries, weather (sources reachable from this environment)

| Need | Source |
|---|---|
| Schedule, spreads/totals context | `https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard` |
| Game summary / injuries per game | `https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={id}` |
| Team roster | `https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{teamId}/roster` |
| Player game log (season) | `https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{athleteId}/gamelog` |
| Team/defense stats | `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{yyyy}/types/2/teams/{teamId}/statistics` |
| Snap counts, defense vs position, advanced | `https://www.pro-football-reference.com/` (often returns 403 to automated requests; if it does, use ESPN data + WebSearch) |
| Official injury report | `https://www.nfl.com/injuries/` |
| Weather (outdoor stadiums) | `https://api.weather.gov/points/{lat},{lon}` → forecastHourly, (primary); `https://api.open-meteo.com/v1/forecast` as backup (may rate-limit) |

WebSearch is also available for news (role changes, late scratches). If a source
fails, say which one in section H instead of guessing.

Compute hit counts, medians and standard deviations with Python from the raw
game logs, and show the raw game-by-game numbers. Do not do the arithmetic in your head.

## 3. Analysis

Apply `ENGINE_PROMPT.md` in full ("Run today's NFL builder"), with its saved
defaults. Produce sections A–H in that order.

## 4. Delivery

* Write the full report to `reports/YYYY-MM-DD-nfl-props.md`.
* End the session with a short summary as the final message: the number of games, the
  top 3 props with FanDuel odds, the Parlay A and B legs, and whether the odds were verified.
  That summary is what the push notification shows.

## 5. Quick-read summary file (required every run)

Besides the full report, write `reports/YYYY-MM-DD-nfl-props-summary.md`.
Keep it short and easy to copy. Use exactly this layout:

1. `# NFL Props — <Day Mon D, YYYY>`, then a single line saying whether FanDuel odds were
   verified (and the final pull time), the inactive-list recheck times (~90 min before each kickoff),
   and "Research only, not a guarantee."
2. `## Copy list (Top N)`: a fenced code block with one line per pick:
   `N. Player Over/Under LINE Market (FanDuel odds)`, or `N. Player 60+ Rush Yds (odds)` for alt
   ladders. Mark unverified picks `(Research Only)`.
3. `## Parlays`: Parlay A and Parlay B, each in its own fenced code block, with one leg per line.
   Put the multiplied price beside Parlay A and label it "not a FanDuel quote".
   For Parlay B, say to get the real price from FanDuel's SGP builder.
   Under each code block: `👉 **[Open Parlay X in FanDuel](URL)**` (see FanDuel links below).
4. `## Pick details`: for each pick, a `### N. Player — Selection (odds)` heading, then
   `[➕ Add to FanDuel betslip](<betslip_link>)`, then an italic `matchup · kickoff ET` line, then a
   one-row table `| Season | Last 5 | Median | Last 5 games |` (computed in Python from the ESPN logs;
   the last column lists the actual values), then exactly two bullets:
   `- ✅ **Why:** <one sentence with the key data>` and `- ⚠️ **Risk:** <one sentence>`.
5. `## Avoided`: at most 5 one-line bullets covering the notable props that were skipped and why.
6. Last line: `Full research: \`YYYY-MM-DD-nfl-props.md\``.

No other prose. Every number must match the full report. If the run has no pregame games,
skip this file.

**FanDuel links.** The odds CSV has a `betslip_link` column (FanDuel `addToBetslip`
URLs). Use only links from the **final** odds pull, and never make up an ID. A parlay link
joins its legs' IDs:
`https://sportsbook.fanduel.com/addToBetslip?marketId[0]=..&selectionId[0]=..&marketId[1]=..&selectionId[1]=..`
(one index per leg, with the values taken from each leg's own link). Put this line above the parlays:
"_The links open FanDuel with the legs already in your betslip. Check every leg and the price before
placing the bet. If a link only adds one leg, use the single-bet links under Pick details._"
If a leg has no link, leave that parlay's link out and say why.
