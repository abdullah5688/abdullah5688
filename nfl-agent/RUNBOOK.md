# NFL Prop Agent — Autonomous Runbook (v2.1)

This is the procedure the scheduled agent follows. The analysis rules are in
`ENGINE_PROMPT.md` and still apply in full. How the model works is in
`README_MODEL.md`. This file says **what to run, in what order, and how to deliver it**.

There is **one scheduled run: Sunday at 8:47 AM ET**. It covers that day's games.
Thursday, Saturday and Monday games aren't covered. There are no pre-kickoff refresh
runs, so the user rechecks inactives themselves, and the report must remind them when.

Setup for every run: `cd nfl-agent`. Every script uses only Python plus numpy and pandas.
nflverse data downloads into `cache/`, which is gitignored.

**Golden rules.**
- Never type in a probability, price, stat or FanDuel ID by hand.
- Numbers come from the scripts. Judgement goes into `context.json`, which is the only
  way to change what the model does, and every entry needs a reason.
- If a step fails, say so in section H. Never fill the gap with guesses.

---

## FULL run

### 0a. Grade last week first (always, even if there are no games today)
1. `python3 ledger.py grade`. This settles every finished pick and parlay and rewrites
   `ledger/summary.md`.
2. Refresh the calibration with the latest completed weeks:

   ```
   python3 backtest.py --raw --season <current> --weeks 4-<last completed week> \
     --season2 <previous> --weeks2 4-18 --out cache/bt_raw.json
   python3 fit_calibration.py cache/bt_raw.csv
   ```

   This takes about 3 minutes. Keep the new `engine/calibration.json` only if every
   market's `brier_fit_cal` is at or below its `brier_fit_raw`. Otherwise run
   `git checkout engine/calibration.json`.
3. Put last week's record, units, ROI and season totals from `ledger/summary.md` at the top
   of section A of today's report, and include them in the final message.

### 0. Is there anything to do?
1. Check the time: `TZ=America/New_York date`.
2. Check the ESPN scoreboard
   (`curl -s https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard`) for
   games today whose `status.type.state` is `pre`. If there are none, finish with
   "No pregame NFL games today — no run."

### 1. Odds
Run `python3 fetch_odds.py --out reports/`. It pulls FanDuel, DraftKings and BetMGM,
covers all six prop types plus every alt ladder, and includes betslip links.

The API key is a network secret, injected into the `x-api-key` header, so don't set a
variable. Each game costs roughly 12 credits.

If you get a 401 or 429, every candidate is **Research Only**. Still run the model, label
everything Research Only, and say so in section H.

### 2. News pass → `reports/YYYY-MM-DD-context.json`
`run_model.py` reads ESPN injury lists automatically. Add only what ESPN doesn't know, using
WebSearch and the official injury report at https://www.nfl.com/injuries/:

```json
{"qb": {"BAL": "Cooper Rush"},
 "out": {"LA": ["Puka Nacua"]},
 "questionable": {"SF": ["Trent Williams"]},
 "exclude": {"Brock Bowers": "weather: 25 mph wind forecast"},
 "notes": {"Jaylen Warren": "OC said Dowdle will start"}}
```

- **QB for every team** whose starter is in doubt:
  - nflverse's listed QB is on ESPN's out list;
  - news of a benching, injury or trade;
  - the model output shows `qb_unknown`.

  Use nflverse abbreviations (LA = Rams, LAC, LV, WAS, JAX...).
- **Weather.** For outdoor games, check https://api.weather.gov. With sustained wind of
  15 mph or more, or heavy rain or snow, `exclude` passing and receiving overs in that game
  and give the reason. The model has no weather input.
- Every `exclude` needs a reason. It will show in the report.

### 3. Run the model
`python3 run_model.py --odds reports/odds-<latest>.csv --context reports/YYYY-MM-DD-context.json --out reports/`

It writes `YYYY-MM-DD-candidates.csv` (every line and rung, both sides),
`YYYY-MM-DD-picks.json` and `YYYY-MM-DD-model-tables.md`. Look at the `games` block in
picks.json, and fix `context.json` before going on if any of these are wrong:
- a QB or spread looks wrong;
- `espn_injuries` is false;
- `qb_unknown` or `qb_debut` appears.

### 4. Deep dive on the shortlist (the analyst's job)
For each top-10 pick and each parlay leg, check:
1. **Role.** Pull the player's last 5 games from `candidates.csv` (last5_values) or nflverse.
   Check snap-share trend and any news about a role change or a returning teammate.
2. **Status.** Check whether the player is actually active and healthy. Questionable
   players are already blocked.
3. **Matchup context.** Read the defensive personnel news (CB or S injuries, a returning
   pass rusher). The model's `def_factor` is opponent-adjusted but knows nothing about
   this week's injuries.
4. **Sanity.** If the model's median is more than 30% away from FanDuel's line, find out why
   before trusting it, usually a role change the data hasn't caught yet.

If a check fails, add an `exclude` (with the reason) or an `out` to context.json and
re-run step 3. **Never hand-pick around the model.** Spend real time here. This step is
where judgement adds value.

### 5. Final price check
Re-pull only the games and markets you're betting:
`python3 fetch_odds.py --out reports/ --events <event_ids> --markets <player_x[,player_x_alternate]>`,
then re-run step 3 on the new odds file. Report any line or price that moved, and use
links only from this final pull.

### 6. Ledger
`python3 ledger.py add reports/YYYY-MM-DD-picks.json`

There are no pre-kickoff refresh runs, so closing prices aren't captured and the CLV
columns stay empty. Results are still graded next Sunday.

### 7. Write the report: `reports/YYYY-MM-DD-nfl-props.md`, sections A–H from ENGINE_PROMPT.md
- **B (Top 10).** Paste the model table from `model-tables.md`. Its columns are a superset of
  the required ones. Under it, give each pick its main reason, biggest risk, and any context
  entries that touched it.
- **C (Top 5 reviews).**
  - The game log: the last5_values column, plus nflverse for a full season if useful.
  - The alt-ladder comparison: rows for the same player and market from
    `candidates.csv`, showing the chosen rung and the rungs either side with
    model p, market p, blend p and EV.
  - The defensive factor, and the projected team pass attempts and carries from the
    `games` block.
- **Best over vs best under.** Use the `over_under` block. This is required for every
  top-10 player, so it's clear an under was considered.
- **D (Parlay C set — last-5 streak; the only parlays).** Parlays A and B were retired on
  2026-11-22 at the user's request; never build them. Use the `parlays_c` list (C1, C2, C3...),
  `streak` and `streak_leftover` blocks in picks.json. Every qualifying leg is used: more than
  five legs are split into separate parlays of up to five, never two legs from one game in the
  same parlay. Show every parlay, then any leftover single legs.
  - Rule (user request): every leg cleared its exact threshold in each of the player's last 5
    games; the hardest such rung is used; -350 cap; no status/role blocks; blend p >= 50%; no
    under while snaps rise or over while snaps fall; one leg per game within each parlay; split into C1, C2... of up to five legs. It is
    independent of the top 10.
  - Show each leg's last-5 values, L10 and season counts, FanDuel's approximate payout (product of
    leg prices), the model fair odds and the "bet only at" price.
  - Model joint probability, fair odds and **minimum acceptable odds**. Tell the user to
    place the bet only if FanDuel's quote is at or better than that.
  - Always state plainly whether the model rates it positive or negative value at FanDuel's price.
  - Because Parlay C can use any game, step 5's final re-pull must include Parlay C's games
    (re-pulling all games is simplest).
- **F (Alternatives and rejections).**
  - The `longshots` (positive EV but under 45% to hit, not this style).
  - The `avoid` list (popular props that are -EV).
  - Every `exclude` with its reason.
- **H (Limitations).** Copy the relevant ones from README_MODEL.md: for example rushing
  overs, weather, and that the market blend is 50/50.

### 8. Quick-read summary: `reports/YYYY-MM-DD-nfl-props-summary.md`
Use exactly this layout:
1. `# NFL Props — <Day Mon D, YYYY>`, then ONE line covering:
   - whether FanDuel odds were verified, with the final pull time;
   - the inactive recheck times (~90 min before each kickoff);
   - "Research only, not a guarantee."
2. `## Copy list (Top N)`: a fenced code block, one line per pick:
   `N. Player Selection (FanDuel odds) · Tier`. Alt rungs are written FanDuel-style, e.g. `Derrick Henry 60+ Rush Yds (-300)`.
3. `## Parlay C (last-5 streak)`:
   - Above them: "_Each link opens FanDuel with that parlay's legs already in your betslip.
     Check every leg and the price before placing the bet._"
   - For EVERY parlay in `parlays_c`, a `### Parlay C1` (C2, C3...) heading, then:
   - The legs in a code block, one per line, each with `· last 5: …`.
   - Then `FanDuel pays ≈X · model fair odds Y · bet only at Z or better`, plus a one-line
     value warning when the model rates it negative value.
   - Then `👉 **[Open Parlay C1 in FanDuel](betslip_url)**` (C2, C3... likewise).
   - After the last parlay, any `streak_leftover` legs as single bets with their own betslip links.
   - If fewer than 2 legs qualify: "No Parlay C today: not enough streak legs passed the checks."
4. `## Pick details`: for each pick:
   - a `### N. Player — Selection (odds)` heading;
   - `[➕ Add to FanDuel betslip](betslip_link)`;
   - an italic `matchup · kickoff ET` line;
   - a one-row table `| Blend p | EV | Season | Last 5 | Last 5 games |`;
   - exactly two bullets: `- ✅ **Why:** …` and `- ⚠️ **Risk:** …`.
5. `## Avoided`: at most 5 bullets.
6. Last line: `Full research: \`YYYY-MM-DD-nfl-props.md\``.

Every number must match picks.json. Links come only from the final pull. Never make up an ID.

### 8b. Phone page and PDF
1. Write `reports/YYYY-MM-DD-notes.json`: `{"Player": {"why": "...", "risk": "..."}}` for every top-10
   player, the same two sentences used in the summary.
2. `python3 make_report_html.py YYYY-MM-DD` writes `reports/YYYY-MM-DD-nfl-props.html` (every number
   comes from picks.json; the record line from ledger/picks.csv).
3. `node make_pdf.js reports/YYYY-MM-DD-nfl-props.html` writes the PDF with every pick expanded.
4. Publish the HTML with the Artifact tool (icon "football") and send the PDF with SendUserFile.
   Put the artifact link in the final message.

### 9. Commit and push
Commit to branch `claude/optimistic-shannon-1lv1ia` and push:
- the report and summary `.md` files;
- `picks.json`, `candidates.csv`, `model-tables.md`, `context.json`, `notes.json`, the `.html` and `.pdf`;
- `ledger/*`.

The raw `odds-*` files stay gitignored.

---

## Data sources reachable from this environment
| Need | Source |
|---|---|
| Player/team weekly stats, snaps, schedule, spreads, starting QBs | nflverse via `engine/data.py` (github.com release files) |
| Schedule, live status, injuries, box scores | ESPN site API (`scoreboard`, `summary?event=`) |
| Odds | The Odds API via `fetch_odds.py` |
| Official injury report | https://www.nfl.com/injuries/ |
| Weather | https://api.weather.gov/points/{lat},{lon} → forecastHourly |
| News | WebSearch |

Pro-Football-Reference blocks automated requests. Don't rely on it.
