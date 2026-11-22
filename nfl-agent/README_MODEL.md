# How the prop model works (v2.1)

The model is the quantitative core of the NFL Player Prop Intelligence Engine. It
replaces "hit X of the last N games" picking with projected probabilities that have
been calibrated against past results, compared with FanDuel's own prices. The analyst
(the scheduled Claude session) still handles news, injuries and the written report.

## Pipeline

| Step | Script | What it does |
|---|---|---|
| 1 | `fetch_odds.py` | FanDuel, DraftKings and BetMGM prices from The Odds API for all six prop types, including every alt-ladder rung, with betslip links |
| 2 | analyst | News pass. Writes `reports/DATE-context.json` with confirmed QB starters, players ruled out and exclusions |
| 3 | `run_model.py` | Simulates every game, prices every FanDuel line and rung on both sides, and outputs the top 10, Parlay C and the long shots |
| 4 | `ledger.py add` | Logs the picks. (`ledger.py snapshot` can record pre-kickoff prices for closing line value, but no scheduled run uses it.) |
| 5 | `ledger.py grade` | Run at the start of each Sunday run. Settles last week's picks from nflverse or ESPN box scores and updates `ledger/summary.md` |
| — | `backtest.py` + `fit_calibration.py` | Walk-forward calibration test, refit at the start of each Sunday run |

Data comes from nflverse (weekly player and team stats, snap counts, the schedule with
spreads, totals and starting QBs, updated nightly) and ESPN (injury lists, scoreboard,
box scores).

## The simulation (`engine/model.py`)

Each game is simulated 20,000 times:

1. **Game script.** The final margin is drawn from Normal(spread, 12.6), where 12.6 is
   the measured spread error over recent seasons. A shared pace shock moves both teams'
   play counts together.
2. **Team volume.** Expected plays combine the offense's recent pace with the plays the
   opponent allows, scaled by the game total. Pass rate is the team's neutral pass rate
   (game script removed) plus half the opponent's tendency, and it moves with the
   simulated margin: trailing teams throw more. The slope is fitted from data, and there is
   extra play-calling noise on top.
3. **Usage.** Each player's target share and carry share are recency-weighted with a
   4-game half-life. The **role-change gate** applies here: if the expected QB has
   started 3 or more games, shares come only from games he started. Otherwise the pick is
   flagged `qb_change`, plus `qb_debut` if he has thrown fewer than 50 career passes,
   which blocks every pass-game pick for that team. Shares of players who are out are
   **redistributed** to active teammates in proportion to their own shares. Per-game shares
   are drawn from a Dirichlet distribution, so teammates compete for the same targets.
4. **Efficiency.** Yards per target, catch rate and yards per carry are shrunk toward
   position averages, with last season counted at half weight. They are then multiplied by
   an **opponent-adjusted defensive factor** for that position group (WR, TE or RB
   receiving, and team rushing). Each game a defense plays is compared with what that
   offense gains against everyone else, so a defense isn't credited or blamed for the
   strength of its opponents. The expected QB's own yards per attempt scales his receivers.
5. **Outcomes.**
   - Targets and carries: multinomial split of the team's attempts.
   - Receptions: binomial.
   - Receiving yards: gamma-distributed per catch.
   - Rushing yards: shifted gamma per carry, so a carry can lose yards.
   - **QB passing yards** = the sum of his receivers' yards, so QB and WR props correlate.
6. **Calibration layer.** A per-market scale and spread fitted on walk-forward backtests
   (see below).

## Turning projections into picks (`run_model.py`)

- **Market probability.** Each line's own FanDuel price, with the bookmaker margin
  removed. The margin is measured on that player's two-sided main line.
- **Blended probability.** 50% model and 50% market (`--model-weight`). The market is
  treated as a strong prior. EV and edge are calculated from this blend.
- **Every rung, both sides.** The main over/under and every alt-ladder rung are priced.
  For each player and market, the best eligible rung is kept.
- **Tiers.**
  - **Bet:** EV of at least +4% and a blended probability at least 2 points above break-even.
  - **Lean:** EV of at least +1.5%.
  - **Research Only:** the pick hits a blocking flag:
    - `qb_debut` or `qb_unknown`;
    - the player is questionable;
    - the player has fewer than 4 games (`small_sample`);
    - the price is shorter than -350;
    - the projection is below the range the model was calibrated on
      (`outside_calibrated_range`, e.g. RB receiving or most QB rushing);
    - the analyst excluded the pick.
- **Balanced style.** Top-10 picks and parlay legs need a blended probability of at
  least 45%. Positive-EV long shots are listed separately.
- **Evidence score (0–100).** Your weights: consistency 20, workload 25, matchup 20,
  value 25, data quality 10. It ranks Bets ahead of Leans. **It is not a probability.**
- **Parlay C (the only parlay type).** Every qualifying leg is used. They are split into
  Parlay C1, C2, C3... of up to 5 legs each, never two legs from one game in the same parlay.
  Each leg cleared its exact
  line in all of the player's last 5 games, passes the status and role checks, has a blended
  probability of at least 50%, and is within the -350 cap. Different games are treated as
  independent, so its probability is the product of the leg probabilities. (Parlays A and B
  were retired on 2026-11-22.)
- **Minimum acceptable odds.** The parlay comes with fair odds and a minimum acceptable
  price (fair odds plus 5%). Only take FanDuel's quote if it is at or above that.

## Backtest evidence (walk-forward, no future data)

`backtest.py` refits the model each week using only earlier weeks, simulates every game,
and checks where the real result landed in the predicted distribution.
2025 weeks 4–18 plus 2026 weeks 4–10 give about 9,000 player-market results.

**Out-of-sample test.** Calibration was fitted on 2025 only and scored on 2026 games it
had never seen. The table shows the Brier score on half-point lines (lower is better) and
reliability: when the model said about 60–70%, how often the over actually hit.

| Market | 2026 results | Brier raw → calibrated | Says 60–70% → actually hit |
|---|---|---|---|
| Receptions | 778 | 0.1917 → 0.1904 | 64% → 70% |
| Receiving yards | 712 | 0.2014 → 0.2014 | 62% → 65% |
| Rushing attempts | 359 | 0.2054 → 0.2011 | 66% → 65% |
| Rushing yards | 333 | 0.2124 → 0.2077 | 62% → 57% |
| Passing yards | 171 | 0.2052 → 0.2063 | 61% → 63% |
| Passing attempts | 171 | 0.2125 → 0.2111 | 68% → 72% |

The production calibration is refitted on both seasons and refreshed weekly by the
grading run. The full reliability tables are in `engine/calibration.json`.

**What this does and doesn't show.** The model's probabilities are honest to within a
few points. It has **not** yet been shown to beat FanDuel's prices, because there are no
historical prop lines to test against. The ledger measures that from now on, using
results and a model-vs-market Brier comparison. Closing line value isn't captured,
because there are no pre-kickoff refresh runs.

## Known limitations (be honest about these in the report)

- In 2026, **rushing-yard overs still hit about 5–7 points less often than predicted**.
  Treat rushing-over edges with extra caution.
- There is no play-by-play detail: no routes, air yards by coverage, or red-zone roles.
  Snap counts are used only to flag trends.
- There is no weather adjustment yet. The analyst must read wind and precipitation for
  outdoor games and exclude passing or kicking-sensitive props by hand.
- Injury-shortened games are in the data, so their risk is priced in, but a player's
  *specific* injury risk isn't.
- Projections for teammates of a QB making his debut are deliberately blocked, not modeled.
- Parlay prices aren't in the odds feed. Compare the minimum acceptable odds with
  FanDuel's quote in the app.
- The 50/50 model–market blend is a judgement call. Change it only on ledger evidence:
  150+ graded picks where the model beats the market on Brier score and closing line value
  is positive.

## v2.2 changes (2026-11-22, walk-forward tested)

Tested on ~9,300 player-games (2025 wks 4-18, 2026 wks 4-10); a change is kept only if calibrated Brier improves.

| Change | Result | Status |
|---|---|---|
| Carry shares use a 1.5-game half-life when a player's snap share moves ≥15 pts (`role_reset=2`) | rush_attempts Brier 0.2065→0.2049, rush_yds 0.2068→0.2059, passing unchanged | **On** |
| Same fast re-weighting for target shares too (`role_reset=1`) | receiving slightly worse | Off |
| QB yards anchored to the QB's own shrunk YPA (`qb_anchor=1`) | pass_yds 0.2041→0.2054, reception_yds 0.1980→0.1991 (worse) | Off |
| `line_gap` flag: model median >30% from the main line → Research Only | automates RUNBOOK step 4.4 | **On** |
| Hit counts restricted to offensive skill positions | fixes same-name collisions | **On** |

Tier check (backtest grouped by each player's season-to-date median): after calibration, top-20% players beat the
projected median ~50-53% of the time in every market, so the model does **not** systematically under-project
stars. Players on hot streaks regress: top-20% receivers beat their own season median only 37% of the time.
Remaining known gap: newly acquired players are projected from very few games with their new team.
