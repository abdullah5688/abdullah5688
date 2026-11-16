# NFL Prop Agent — Autonomous Runbook (v2.1)

This is the procedure the scheduled agent follows. The analysis rules are in
`ENGINE_PROMPT.md` and still apply in full. How the model works is in
`README_MODEL.md`. This file says **what to run, in what order, and how to deliver it**.

There are three kinds of run, and the scheduled task tells you which one this is:

| Run | When (ET) | Purpose |
|---|---|---|
| **FULL** | Sun 8:47 AM · Thu & Mon 6:50 PM · Sat 12:10 PM (Dec–Jan) | Research, model, picks, report |
| **REFRESH** | Sun 12:05, 3:05, 7:05 PM | Inactives and news check, closing prices, update picks if something changed |
| **GRADE** | Tue 1:23 PM | Settle last week's picks, update the ledger, refresh the calibration |

Setup for every run: `cd nfl-agent`. Every script uses only Python plus numpy and pandas.
nflverse data downloads into `cache/`, which is gitignored.

**Golden rules.**
- Never type in a probability, price, stat or FanDuel ID by hand.
- Numbers come from the scripts. Judgement goes into `context.json`, which is the only
  way to change what the model does, and every entry needs a reason.
- If a step fails, say so in section H. Never fill the gap with guesses.

---

## FULL run

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
```
python3 ledger.py add reports/YYYY-MM-DD-picks.json
python3 ledger.py snapshot --date YYYY-MM-DD
```

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
- **D/E (Parlays).**
  - The legs.
  - Model joint probability, fair odds and **minimum acceptable odds**. Tell the user to
    place the bet only if FanDuel's quote is at or better than that.
  - For the SGP: the correlation factor and what sinks several legs at once.
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
3. `## Parlays`:
   - Above the parlays: "_The links open FanDuel with the legs already in your betslip.
     Check every leg and the price before placing the bet. If a link only adds one leg, use
     the single-bet links under Pick details._"
   - Each parlay in its own code block, one leg per line.
   - Then `Fair odds X · bet only at Y or better`.
   - Then `👉 **[Open Parlay X in FanDuel](betslip_url)**`.
4. `## Pick details`: for each pick:
   - a `### N. Player — Selection (odds)` heading;
   - `[➕ Add to FanDuel betslip](betslip_link)`;
   - an italic `matchup · kickoff ET` line;
   - a one-row table `| Blend p | EV | Season | Last 5 | Last 5 games |`;
   - exactly two bullets: `- ✅ **Why:** …` and `- ⚠️ **Risk:** …`.
5. `## Avoided`: at most 5 bullets.
6. Last line: `Full research: \`YYYY-MM-DD-nfl-props.md\``.

Every number must match picks.json. Links come only from the final pull. Never make up an ID.

### 9. Commit and push
Commit to branch `claude/optimistic-shannon-1lv1ia` and push:
- the report and summary `.md` files;
- `picks.json`, `candidates.csv`, `model-tables.md` and `context.json`;
- `ledger/*`.

The raw `odds-*` files stay gitignored.

---

## REFRESH run (Sunday 12:05 / 3:05 / 7:05 PM)
1. Load today's `reports/YYYY-MM-DD-picks.json` from the repo. If it doesn't exist (no full
   run today), finish with "No picks to refresh."
2. Inactives and news: for every game that **hasn't kicked off** and has a pick or parlay leg,
   check the ESPN injury list (`summary?event=`), the NFL inactives news on WebSearch, and the
   QB status.
3. `python3 ledger.py snapshot --date YYYY-MM-DD`. This records the closing prices.
4. **If anything changed** for a pick (a player inactive or limited, a QB change, the line
   moved past the model's fair price):
   1. Update `context.json`.
   2. Re-pull only those games:
      `fetch_odds.py --events ... --markets ...`.
   3. Re-run `run_model.py` on that odds file with `--out reports/refresh-HHMM/`.
   4. Append a `## Refresh HH:MM ET` section to the summary file, listing dropped picks,
      replacements and new prices. A replacement must come from the new model output.
   5. `ledger.py add` the new picks.json.

   Then commit and push, and send a final message listing the changes.
5. If nothing changed, commit the snapshot data. Final message: "Refresh HH:MM — no changes."

## GRADE run (Tuesday 1:23 PM)
1. `python3 ledger.py grade`. This settles all finished picks and rewrites
   `ledger/summary.md`. Picks not yet available stay open and are retried next week.
2. Refresh the calibration with the latest completed weeks:

   ```
   python3 backtest.py --raw --season <current> --weeks 4-<last completed week> \
     --season2 <previous> --weeks2 4-18 --out cache/bt_raw.json
   python3 fit_calibration.py cache/bt_raw.csv
   ```

   This takes about 3 minutes. Commit `engine/calibration.json` only if every market's
   `brier_fit_cal` is at or below its `brier_fit_raw`.
3. Commit and push `ledger/*` and the calibration.
4. Final message:
   - last week's record, units and ROI;
   - average CLV;
   - season totals;
   - the model-vs-market Brier line from `summary.md`;
   - one sentence on what the numbers say, cautious about small samples.

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
