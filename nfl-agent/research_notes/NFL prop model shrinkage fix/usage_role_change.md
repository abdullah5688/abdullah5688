# NFL Player Usage Projection & Role-Change Adaptation

> Method note: WebFetch was blocked for every host tried (bengretch.substack.com, pff.com, theanalyst.com all returned ENOTFOUND, meaning they are outside the session's allowed network domains). All citations below come from search-result summaries, not full-page reads. Treat exact figures as needing verification. Most sources are fantasy-media and blog analyses, not peer-reviewed work. Items marked "Inference" are reasoning, not sourced facts.

## 1. Which usage metrics are most predictive and stabilize fastest?

### Takeaway
Rate-of-opportunity metrics (route participation, TPRR, target share, snap share) are more stable and predictive than production. The only published stabilization numbers I found are old: about 7 games for TPRR and 14 games for YPRR. Few public studies give stability numbers for route participation or snap share specifically.

### Cited Findings
- TPRR stabilized in about 7 games, and receptions per route run also took about 7 games; YPRR needed about 14 games (~350 routes). The article is about 12 years old. — [Intentional Rounding](https://intentionalrounding.com/when-do-receptions-and-touchdowns-per-route-run-stabilize/)
- One analyst tested year-over-year stability and found TPRR "much more stable" than its components. — [Fantasy Footballers TPRR 2025 preview](https://www.thefantasyfootballers.com/analysis/targets-per-route-run-report-2025-season-preview-fantasy-football/)
- SportsLine found TPRR correlated with fantasy scoring more than any other opportunity stat it tested over five seasons. — [SportsLine 2022](https://sportsline.com/insiders/fantasy-football-2022-how-targets-per-route-run-can-help-identify-potential-breakouts-in-the-passing-game)
- TPRR benchmarks: about 20% is baseline, 25–30% excellent, over 30% elite. — [Fantasy Footballers](https://www.thefantasyfootballers.com/analysis/targets-per-route-run-report-2025-season-preview-fantasy-football/)
- The Fantasy Footballers' weekly TPRR qualification minimums are WR 15 routes, TE 10, RB 5. — [Fantasy Footballers TPRR Week 5](https://www.thefantasyfootballers.com/analysis/targets-per-route-run-week-5-fantasy-football-2/)
- One analyst argues first-read target rate is stickier than TPRR. — [Legendary Upside](https://www.legendaryupside.com/week-2-walkthrough-stefon-diggs-target-funnel/)
- PFF says Share of Predicted Targets and Share of Predicted Air Yards are more stable than actual target share and air-yards share. — [PFF, players trending toward more targets](https://www.pff.com/news/week-14-fantasy-football-players-trending-toward-more-targets)
- In 3,222 WR stretches, target share was the strongest forward predictor of fantasy scoring (+0.217). Short-term rising trends (last 3 games vs last 5 in targets, target share, WOPR) also predicted positively, including for RBs. Methodology is unverified. — [GWTTKB](https://www.gwttkb.com/research/what-actually-predicts-fantasy-football.html)
- WOPR = 1.5 × target share + 0.7 × air-yards share (Josh Hermsmeyer). It was built to predict PPR and standard points, but I found no published stability figures for it. — [Action Network](https://www.actionnetwork.com/education/weighted-opportunity-rating-definition-how-find-boosted-receiver-production-with-this-stat); [FTN guide](https://ftnfantasy.com/nfl/guide-to-football-analytics)
- Snap share, route participation, and target or touch share are "inputs": more stable and more predictive than last week's production. — [NFL Analytic explainer](https://nflanalytic.com/explainer-snap-counts-usage.html)
- RBs split work the most, so RB snap share swings more week to week than any other position's. — [Statz](https://statz.ai/nfl/news/nfl-snap-counts-explained)
- Separating routes run from TPRR matters. Example: Chris Olave had 37.5% TPRR and Rashid Shaheed 23.5%, but their route totals were a concern. — [Fantasy Footballers](https://www.thefantasyfootballers.com/analysis/targets-per-route-run-week-5-fantasy-football-2/)
- One third-party guide sets a route-participation baseline over at least 8 games, then scales by team pass volume. — [FantasyProjectionLab TE](https://fantasyprojectionlab.com/fantasy-football-tight-end-projections/)
- A QB's target-distribution profile takes about 600 pass attempts to stabilize. — [RotoWire Stats Room](https://www.rotowire.com/football/article/the-stats-room-are-qb-targets-predictable-41122)

### Inferences
- Breaking targets into routes × TPRR lets each piece be weighted on its own clock. Route participation is a coaching decision that shifts abruptly when the depth chart changes. TPRR is closer to a player trait that stabilizes in about 7 games and should be shrunk toward a prior. The current model projects target share directly and mixes the two. That likely explains the TE case: his route participation probably jumped, but the blended share lagged.
- Air-yards share and "predicted targets" add signal beyond raw target share at the same sample size, and should be used as features or co-observations.

### Gaps
- No modern published split-half or week-to-week reliability numbers for route participation, snap share, carry share, or red-zone share. These need to be computed in-house from nflfastR plus participation data (e.g., Cronbach/split-half by games played).
- No source found on red-zone share stability.

## 2. Weighting schemes: half-lives, Bayesian/Kalman/state-space, changepoints, reaction speed

### Takeaway
Practitioners use exponential decay. One open-source backtest settled on roughly a 7-week half-life with light shrinkage toward a prior, and found heavy regression underweighted recent form. I found no published NFL usage model built on Kalman filters or changepoint detection. The closest analog is Glickman and Stern's Bayesian state-space model for NFL team strength. Practical guidance says to trust sustained 3–5 game shifts, not one-game spikes.

### Cited Findings
- The open-source fantasyfb project backtested time decay and moved it to a range of 0.04–0.10 per week. A game 7 weeks old then counts about half as much as last week's. It also reduced shrinkage for QB/RB/WR/TE to a prior worth about 2 games, because heavier regression "over-regress[ed] established players and under-weight[ed] recent form." This is the project's own backtest and is unverified. — [GitHub tefirman/fantasyfb PR #160](https://github.com/tefirman/fantasyfb/pull/160)
- Soccer rating research: a half-life that is too long overweights old matches, and one that is too short makes ratings unstable. The optimum was 60 days in one paper and 107 days in another model. These are analogies only. — [arXiv 2411.09085](https://arxiv.org/pdf/2411.09085) (via search summary)
- Glickman & Stern, "A State-Space Model for NFL Scores": team strength follows a Kalman/Bayesian state-space process with within-season drift (injuries) and between-season drift (personnel, strategy). — [glicko.net](https://glicko.net/research/nfl.pdf)
- Online changepoint detection can be computed via Kalman filter evaluations (a sports health-monitoring application). — [arXiv 2206.11578](https://arxiv.org/pdf/2206.11578)
- A patent application uses changepoint detection on tracking data to separate deliberate role changes from brief swaps. — [USPTO 12236681](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12236681)
- Practitioner heuristic: act on sustained rolling increases in snap share, target share, or carries over a 3–5 game window, not on single-game spikes. — [kickoff.news](https://kickoff.news/fantasy-insights-player-performances-to-monitor-mid-season) (via search summary)
- A model update that adds weekly snap data "restores predictive power." This source also cites some unverified statistics. — [marketkit.live](https://marketkit.live/rookie-rb-td-model-run-first-schemes/)

### Inferences
- A 4-game half-life is already fairly fast. The failures this week look like regime-change problems, not a decay-rate problem. A fixed half-life cannot both resist noise and react to a real role change. Options:
  - A local-level Kalman filter per player per share. Raise the process variance (Q) on known events (QB change, trade, teammate injury or return, depth-chart news) so the filter re-weights toward recent games automatically.
  - Bayesian online changepoint detection (Adams & MacKay style) on route participation and snap share. When the changepoint posterior is high, reset the window to post-change games and blend with a role-based prior.
  - A hard reset: when route participation or snap share in the last 2 games departs from the EWMA by more than a threshold (e.g., about 15 percentage points), use post-change games only, plus shrinkage. The threshold is not from any source.
- Shrink rates such as TPRR and YPRR toward position or draft priors. Treat participation such as routes, snaps, and carry share as a state that can jump.

### Gaps
- No published NFL player-usage Kalman or changepoint implementation found. No practitioner-published half-lives found from 4for4, ETR, FantasyPoints, PFF, numberFire, or Mike Clay.

## 3. QB changes, trades/new teammates, injured-teammate redistribution, rookies

### Takeaway
Evidence is mostly descriptive. Backup QBs often check down to RBs more. Expected pass rate is a team and game-script trait, while QB efficiency moves with the QB. Vacated targets do not go out proportionally: they flow to newcomers and high draft picks, sometimes shift to RBs, or go to the next player on the depth chart. Newly traded WRs ramp up over 1–3 weeks. Draft capital is the strongest single prior for rookies.

### Cited Findings
- QB changes:
  - Backup QBs target RBs more. Tyson Bagent threw 23% of his attempts to RBs, versus 15% for Caleb Williams. This is descriptive and not controlled for game state. — [FantasyPoints 2025 QB positional target tendencies](https://www.fantasypoints.com/nfl/articles/2025/qb-positional-target-tendencies)
  - The "backup connection": Robby Anderson's share of attempts went from 9.7% with Fitzpatrick to 25.6% with Petty. This is anecdotal. — [PFF](https://www.pff.com/news/fantasy-football-metrics-that-matter-is-there-a-backup-connection)
  - Team pass volume moves target totals away from target shares, so backup-led offenses can cut raw targets even if shares hold. — [Pitcher List](https://football.pitcherlist.com/are-running-back-targets-inherited-from-quarterbacks/)
  - For QBs who stay on the same team, expected pass rate is sticky year to year (r ≈ 0.45). The rate "belongs to the team and the scoreboard," while EPA in expected-pass situations follows the QB (0.32 if he stays, 0.30 if he moves). High expected-pass-rate QBs "get there by losing." — [Patton Analytics](https://pattonanalytics365.substack.com/p/putting-yourself-in-a-hole)
  - A QB's target-distribution profile takes about 600 attempts to stabilize. — [RotoWire](https://www.rotowire.com/football/article/the-stats-room-are-qb-targets-predictable-41122)
  - Starter ruled out before kickoff: the average spread moved 4.2 points across 247 cases. — [Betting Data Lab](https://betting-data-lab.com/nfl-quarterback-injury-impact-how-backup-qbs-change-spread-and-total-lines/)
  - A backup playing the whole game cuts win probability by about 8 percentage points (2009, dated). — [Advanced NFL Stats community](http://community.advancednflstats.com/2009/01/quarterbacks-starters-verses-backups.html)
- Vacated targets and injuries:
  - Some vacated targets go to the next player on the depth chart, but most go to newly signed players and, in some cases, highly drafted rookies. — [Fantasy Footballers](https://www.thefantasyfootballers.com/articles/vacated-targets-predicting-the-future-in-fantasy-football/)
  - Several top vacated-target teams shifted targets toward the RB position. — [PlayerProfiler](https://www.playerprofiler.com/article/vacated-targets-why-they-matter-and-whos-eating/)
  - Top-24 WRs tend to get a production bump when their team has many vacated targets. — [PFF](https://www.pff.com/news/fantasy-football-analyzing-vacated-targets-to-find-2020-breakout-receivers)
  - When a player is out, targets move by position, not proportionally. Example: Lions TEs absorbed Nate Burleson's targets. — [PFF target distribution trends](https://www.pff.com/news/fantasy-target-distribution-trends)
  - Players listed questionable or doubtful lose production: RB/WR/TE drop 8–10%, and WRs with knee tags lose 12.5% of targets. — [4for4](https://www.4for4.com/how-injury-affects-nfl-fantasy)
- Trades and new teammates:
  - Tank Dell's debut was a 20.4% snap share and 13.3% route share. The next week jumped to 47% snaps and 55% routes, and the team said it would keep ramping him up. — search summary of [FantasyPoints / FantasyPros 2026 articles](https://www.fantasypoints.com/nfl/articles/2026/week-10-fantasy-football-trade-targets-buy-low-sell-high)
  - Keenan Allen's first 49ers games: 50% snaps, 60% routes, 25% target share. — [FantasyPros Week 11 2026 WR start/sit](https://www.fantasypros.com/2026/11/fantasy-football-start-sit-lineup-advice-wide-receivers-week-11-2026/)
  - Josh Downs scored a TD on 10 snaps in his KC debut. — [FantasyPros Week 11 Primer](https://fantasypros.com/2026/11/the-primer-week-11-edition-2026-fantasy-football/3)
- Rookies:
  - Draft capital carries the most weight in rookie models. RB correlation with future fantasy production is 0.69 for draft capital alone and 0.73 for the full model. Draft value is nonlinear, with the steepest drop in rounds 1–2. — [Fantasy Life Rookie Super Model 2026](https://www.fantasylife.com/articles/nfl-draft/2026-rookie-super-model-a-data-centric-approach-to-grading-rooki); [2024 version](https://www.fantasylife.com/articles/redraft/2024-rb-rookie-super-model-tier-2-rookie-running-backs)
  - Capital is "a floor for role, not a promise of touches." Incumbent contracts can block the path. — [FantasyFootballBlueprint](https://www.fantasyfootballblueprint.com/2026/08/03/rookie-rb-workload-signals/)
  - Fantasy Life assigned a top-10-pick rookie RB 63% of team rush attempts, based on historical top-10 pick trends. — [Fantasy Life](https://www.fantasylife.com/articles/fantasy/fantasy-football-rookie-rankings-for-2026)

### Inferences
- QB change (the Ravens case): split team volume from distribution.
  - Re-project team dropbacks from the new QB's own pass-rate history, the spread and total, and coach PROE. Do not keep stale team-attempt priors. The Patton result suggests the team or coach sets PROE, but a QB change also moves the spread and total, and that feeds expected pass rate.
  - For distribution, keep within-team shares from all games. Apply QB-specific adjustments only as shrunk deviations, since QB profiles take about 600 attempts to stabilize. Add a backup-QB RB-target bump. The 3-start rule throws away information early and then flips abruptly. A hierarchical QB × receiver adjustment with partial pooling works better.
- Injured players: replace proportional redistribution with position-aware redistribution.
  - Vacated WR routes go first to the WR who inherits the snaps (often WR4 or a newcomer). Vacated targets go partly to the route inheritor at his own TPRR, and the rest shift toward RB and TE.
  - This can be estimated empirically from nflfastR with-or-without splits.
- New acquisitions: use a ramp prior for weeks 1–3 (about 50% route participation in week 1, rising toward the role prior), with the TPRR prior from prior-team history, shrunk. Do not drop the player's prior-team data.
- Rookie RB taking over: use a draft-capital prior on carry share, plus a changepoint trigger on snap share. A 1st/2nd-round rookie whose snaps exceed the incumbent's for 1–2 games should be reset quickly.

### Gaps
- No rigorous public study of where vacated targets go by position share. No study of how a QB swap shifts team dropbacks. No published projection of rookie snap share from draft capital.

## 4. Team-level volume: pass attempts and plays from spread/total, pace, PROE, game script

### Takeaway
Standard practice is expected pass rate from an xpass model (down, distance, score, time, WP) plus team or coach PROE, times projected plays from pace and the total. The spread drives the game-script component. Dropbacks, including sacks and scrambles, are the right unit.

### Cited Findings
- PROE = actual pass rate − expected pass rate, where expected is the mean of the xpass model's per-play pass probabilities. That per-play probability is where game script enters. — [Stick To The Model](https://sticktothemodel.com/encyclopedia/pass-rate-over-expected)
- Dropback rate minus expected dropback rate, given down, distance, quarter, and score difference. Sacks and scrambles count as passes. — [Dynatyze](https://dynatyze.com/football/reports/pass-rate-over-expected); [Sharp Football Analysis PROE](https://www.sharpfootballanalysis.com/stats-nfl/nfl-pass-rate-over-expected/)
- Calibration example: in the 30–40% bucket, the xpass model predicted 35.6% and the actual was 31.8%, so it overstated passing. — [Stick To The Model](https://sticktothemodel.com/encyclopedia/pass-rate-over-expected)
- Defensive PROE faced is used as an opponent input. Example: the Vikings ranked 32nd in PROE faced at −5.1%. — [Yahoo Sports](https://sports.yahoo.com/articles/nfl-week-11-sunday-night-051745291.html)
- Weekly adjusted pace and pass rate reports rank games by projected plays. — [FanDuel Research](https://www.fanduel.com/research/adjusted-nfl-pace-and-pass-rate-report-ranking-week-10-s-fastest-games-2025)
- ETR has a PROE explainer. — [Establish The Run](https://establishtherun.com/pass-rate-over-expectation/)

### Inferences
- Team dropbacks ≈ projected offensive plays (from pace in neutral situations, the total, and opponent pace) × (expected pass rate given spread-implied script + team PROE, shrunk + QB adjustment). Pass attempts = dropbacks − sacks − scrambles.
- Re-fit PROE with recency weighting and reset it on a coordinator or QB change.

### Gaps
- No published coefficients mapping spread and total to pass attempts.

## 5. How professional services describe usage projection methods

### Takeaway
Public methodology is thin. ETR describes "math, usage, matchups" with continuous news updates. PFF's Spratt and the Analyst have process articles that I could not fetch. Mike Clay's projections power ESPN, and his xFP strips out talent to measure opportunity, but I found no write-up of how he projects shares.

### Cited Findings
- ETR projects every player using "math, an understanding of player usage, and matchups," updated continuously for news, with base, ceiling, and floor outputs. — [ETR weekly projections](https://establishtherun.com/fantasy-point-projections/)
- Mike Clay builds a full statistical projection each offseason after the draft, and it powers ESPN fantasy. His xFP isolates opportunity. — [ESPN Press Room](https://espnpressroom.com/us/bios/mike-clay/); [ESPN xFP](https://africa.espn.com/fantasy/football/story/_/id/46168860/2025-fantasy-football-expected-fantasy-points-xfp-qb)
- PFF's TPRR (TA/PR) and route rate (PR/SN) metrics; touchdown-per-touch rates based on Mike Clay's research. — [PFF Advanced Targets](https://www.pff.com/news/advanced-targets-week-4-wrap)
- Process articles exist but were not fetched: [PFF Spratt's 6 steps](https://www.pff.com/news/fantasy-football-scott-spratts-6-steps-to-creating-weekly-fantasy-rankings), [Opta Analyst projections explainer](https://theanalyst.com/articles/explaining-the-analysts-weekly-nfl-fantasy-football-projections), [DraftSharks Anatomy of a Projection](https://draftsharks.com/article/the-anatomy-of-a-projection), [Stokastic DIY projections](https://www.stokastic.com/articles/nfl-dfs/how-to-make-nfl-dfs-projections), [FantasyPros Kyle Yates](https://www.fantasypros.com/2020/08/an-introduction-to-kyle-yates-fantasy-projections-2020-fantasy-football).

### Inferences
- The common structure across services is a top-down team-volume projection, then player shares, then efficiency, with manual analyst overrides for news (role changes, ramps). Human news overrides are effectively the "changepoint detector" at these shops.

### Gaps
- No method details found for 4for4, FantasyPoints, numberFire, Rotoviz, SIS, or Clay's share logic. Fetching was blocked, and these are mostly paywalled.
