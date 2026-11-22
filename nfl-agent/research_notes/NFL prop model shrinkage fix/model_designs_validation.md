# End-to-end designs of NFL player stat projection / prop models, and how they are validated

Research note on access: most full-text fetches failed because these domains are blocked in this session: medium.com (DraftKings Engineering post), walrusquant.github.io, opensourcefootball.com, the-odds-api.com, establishtherun.com, substack.com, teamrankings.com and the Princeton theses site. Per-repo GitHub API access was also not enabled. Many findings below therefore come from search-result summaries of those pages rather than full reads, and they are marked "(snippet)". The Inferences sections are reasoning from those findings and from standard statistics practice. They are not sourced facts.

## Q1. Published / open-source model architectures (volume x efficiency, distributions, correlation)

### Takeaway
Public designs fall into three families. (a) Play-by-play Monte Carlo simulators that sample each play from ML classifiers (DraftKings Engineering). (b) Team-level volume projections allocated down by player share, as in ESPN/Mike Clay's team-by-team method. (c) Direct player-level ML regressors, such as XGBoost with quantile heads, or distributions fitted to the outputs of expert or ML models. Few open-source NFL prop models are mature. The GitHub repos found are mostly small personal projects with 0-4 stars.

### Cited Findings
- DraftKings Engineering, "Modeling Football: Combining ML models and Monte Carlo simulations", describes a play-by-play simulation that "sample[s] from a multi-class classifier model to get a value for the yards attempted for this specific play in this particular simulation". Yardage is a discretized multi-class output, not a parametric gamma. (snippet) — [DraftKings Engineering](https://medium.com/draftkings-engineering/modeling-football-combining-ml-models-and-monte-carlo-simulations-170fd58cbe11)
- A practitioner write-up on prop Monte Carlo recommends Poisson for count stats and lognormal for yardage, with simulation of "tens of thousands" of outcomes to handle the complexity. (snippet) — [WalrusQuant: Player Prop Simulation](https://walrusquant.github.io/rust-bet-tracker/blog/player-prop-simulation)
- Hugging Face Spaces "NFL_Betting_Models" (Multichem/TrueDFS) runs player-prop simulations whose variables include pass_yards, rush_yards, rec_yards, receptions, rush_attempts, pass_attempts and pass_completions. (snippet; internals not inspected) — [HF Space app.py](https://huggingface.co/spaces/Multichem/NFL_Betting_Models/blob/c790aaf8bcc165039bebbe09a4ba84c4a4c53764/app.py)
- ESPN's Mike Clay builds projections team by team, projecting dropback, carry and target shares for each player. This is the canonical top-down volume-allocation approach. (snippet) — [ESPN: What Mike Clay learned doing 2022 projections](https://africa.espn.com/fantasy/football/insider/story/_/id/33621386/mike-clay-learned-doing-2022-fantasy-football-projections)
- ffopportunity (ffverse/nflverse) applies XGBoost models to nflverse play-by-play to compute expected fantasy points, meaning what an average player would score given each opportunity. Models were trained on 2006-2020 data, preprocessing splits passes and rushes, and outputs are summarized to player level. Precomputed results load through `nflreadr::load_ff_opportunity()`. This is a usable "expected volume/efficiency" feature source. — [ffopportunity GitHub](https://github.com/ffverse/ffopportunity); [nflreadr docs](https://search.r-project.org/CRAN/refmans/nflreadr/html/load_ff_opportunity.html)
- nflfastR's built-in models (via fastrmodels 2.1.0, CRAN Feb 2026) cover EP, WP, completion probability (CP) and expected YAC. These are per-play models, not game-level player projections, but CP and xYAC are standard efficiency inputs. — [nflfastR README](https://cran.r-project.org/web/packages/nflfastR/readme/README.html); [fastrmodels CRAN](https://cran.r-project.org/web/packages/fastrmodels/index.html)
- A Princeton senior thesis builds per-position XGBoost models (RB/WR/TE) with quantile regression heads for 80% prediction intervals. It reports 2025-season MAE of 2.909 fantasy points vs ESPN's 3.074. (snippet) — [Princeton thesis](https://theses-dissertations.princeton.edu/entities/publication/d6981488-f30c-47ce-8f06-b6c3e98f2578)
- arXiv:2111.02874 (IBM/ESPN "Deep AI for Fantasy Football Language Understanding") makes a point projection from a position-based regression ensemble, then fits 24 candidate probability distributions to each player's historical and predicted performance to produce a score distribution. — [arXiv 2111.02874](https://arxiv.org/pdf/2111.02874)
- NFL DensOrd turns FantasyPros expert rankings into weekly fantasy-point distributions using kernel density estimation on about 60,000 player-weeks (2013-2021). Hyperparameters are tuned by cross-validated test accuracy. The author notes the distributions are lumpy because of discrete scoring (TDs) and that "smoothing them out lowers model fit on testing data". The readme describes no explicit calibration check. — [NFL_DensOrd GitHub](https://www.github.com/paulcbogdan/NFL_DensOrd)
- Older point-prediction academic work compares SVR and neural nets for fantasy scores (arXiv:1505.06918), and a Stanford CS229 project ("Any Given Sunday") does similar. — [arXiv 1505.06918](https://arxiv.org/pdf/1505.06918); [CS229 2014](https://cs229.stanford.edu/proj2014/Bobak%20Moallemi,%20Matthew%20Wilson,%20Steven%20Hoerning,%20Any%20Given%20Sunday.pdf)
- Bayesian hierarchical approaches: Spencer Rome's blog applies hierarchical modeling to fantasy projections for uncertainty, and an RPubs project uses Bayesian linear regression for RB rushing yards. (snippets) — [srome.github.io](https://srome.github.io/Bayesian-Hierarchical-Modeling-Applied-to-Fantasy-Football-Projections-for-Increased-Insight-and-Confidence); [RPubs](https://rstudio-pubs-static.s3.amazonaws.com/1053227_d98abb298105422792f4e1ba64d4a0c2.html)
- PFF built a route-level model of predicted target share and reports that raw target share explains 41% of the variance in next-week target share. Usage stickiness is moderate, so share shrinkage is warranted, but only partially. (snippet) — [PFF "Coach, I was open"](https://www.pff.com/news/nfl-refining-coach-i-was-open-a-model-comparing-actual-vs-predicted-target-shares)
- GitHub search for "nfl player props" and "nfl prop model" returns mostly 0-4 star personal repos. Examples: GinoMariello/nfl-prop-model ("Weekly NFL player stat projections, calibrated prop probabilities and live paper trading (PyTorch, scikit-learn, SQLite, React)"), AndrewAOh/nfl-prop-model ("modeling and evaluation"), sibitogit/nfl-prop-lab ("historical backtesting tool") and notsmrt/NFL-prop-model (predicts the book line, then ranks by probability and edge). Contents could not be read. — [GitHub search, via gh CLI](https://github.com/search?q=nfl+prop+model&type=repositories)

### Inferences
- Our structure (team plays, then pass rate, then Dirichlet shares, then binomial catches, then gamma YPC) matches the common volume x efficiency decomposition. The architecture is not unusual. The under bias is more likely to come from parameter choices (shrinkage targets and strength, calibration scale) than from the topology.
- Gamma yards per catch summed over a binomial number of catches gives a compound distribution whose shape is driven by the target count. That is reasonable. The common alternatives (lognormal per game, discretized classifier per play) mainly affect tails, not the mean.
- QB-WR correlation in simulators comes from shared game script (pace, margin, pass rate) and shared team pass volume and efficiency. A simulator in which receivers' efficiencies are drawn independently will understate the QB variance and the positive QB-WR correlation.

### Gaps
- Could not read the full DraftKings post or any Open Source Football posts (domains blocked). The exact distributions, features and validation used there are unverified.
- Found no published open-source NFL prop model that reports out-of-sample results against prop lines.

## Q2. QB yards = sum of receivers' yards (bottom-up) vs projecting QB directly and allocating down (top-down)

### Takeaway
The industry-standard projection workflow (Mike Clay, team-by-team) is top-down. Project team dropbacks and team passing efficiency first, then allocate targets and yards by share, so that team totals reconcile by construction. Play-by-play simulators (DraftKings) are bottom-up per play, but the play is the unit: QB yards and receiver yards for a completion are the same number, sampled once.

### Cited Findings
- Mike Clay projects team by team, with dropback, carry and target shares for each player (top-down allocation). (snippet) — [ESPN Mike Clay](https://africa.espn.com/fantasy/football/insider/story/_/id/33621386/mike-clay-learned-doing-2022-fantasy-football-projections)
- DraftKings' simulator samples yards per play from a classifier. Aggregation is per play, so passer and receiver stats come from the same draw. (snippet) — [DraftKings Engineering](https://medium.com/draftkings-engineering/modeling-football-combining-ml-models-and-monte-carlo-simulations-170fd58cbe11)
- Footballguys lists "percent of team passing yards" as a stat that regresses, which presumes a team-level total that is allocated. (snippet) — [Footballguys Regression Alert](https://www.footballguys.com/article/2023-regression-alert-week-15)

### Inferences
- Summing receivers' yards is internally consistent, since each completion's yards count for both QB and receiver. The danger lies in how each receiver's efficiency is estimated. If each receiver's YPT/YPC is shrunk independently toward a position average, the QB inherits the sum of all those shrinkages, and the QB's own skill (accuracy, aDOT, scheme) gets no direct prior. An elite QB's yards then shrink toward "average QB with average receivers". This is a plausible direct cause of under-projecting good QBs and their WR1s.
- Hybrid fix used in practice: a team or QB-level passing-efficiency factor (QB-specific yards per attempt with its own shrinkage, opponent-adjusted) sets the team's pass-yard mean. Receivers' relative efficiencies are then allocated as multipliers normalized to the team total. This keeps correlation and reconciliation, and gives QB skill a prior.
- Pros of bottom-up: natural correlation and coherent SGP pricing. Cons: compounding shrinkage, and team totals drift from the market's implied team passing environment. Pros of top-down: anchors to the team total and QB skill, and is easy to calibrate against team-level markets. Cons: allocation needs care to preserve receiver-level variance.

### Gaps
- No source found that quantitatively compares top-down and bottom-up QB-yard accuracy.

## Q3. Calibration techniques and pitfalls (scale < 1, isotonic/quantile, bias vs market, bias by tier)

### Takeaway
Shrinkage toward population means is standard and correct for noisy stats, but it should be sample-size-weighted toward a player-specific (or tier/role-specific) prior, not a flat position average. A global multiplicative scale below 1 fitted on PIT or Brier will mechanically pull high-volume and efficient players down the most in absolute yards. Medians of right-skewed yardage sit below means, and the under side has historically hit about 55% or more, so some under lean is expected. A model where most picks are unders, concentrated on good players, is a classic sign of over-shrinkage.

### Cited Findings
- Bayesian regression to the mean: the regressed estimate blends the observed stat with a population baseline weighted by sample size. NFL completion percentage is very noisy at about 250 attempts. The same blog argues that hot streaks inflate lines because the public bets overs. (snippet) — [WalrusQuant: Regression to the Mean](https://walrusquant.github.io/rust-bet-tracker/blog/regression-to-the-mean)
- Mean vs median: in right-skewed passing yards, using the mean "might tend to overestimate the likelihood of the 'over'" because rare high games pull the average up. (snippet) — [TeamRankings: prop bets passing yards](https://www.teamrankings.com/blog/sports-betting/prop-bets-passing-yards)
- ASA example: a player with a 2.5-catch mean and a 0-catch median. A mean-based system would bet over 1.5, a long-run loser. ASA also says projecting means matters more than medians for DFS. (snippet) — [Advanced Sports Analytics substack](https://advancedsportsanalytics.substack.com/p/getting-ready-for-nfl-props-and-sports)
- ETR: a player's median is lower than its mean projection because of distribution shape and less predictable outcomes like in-game injury. For pick'em/props the median (50th percentile) is "more applicable". (snippet) — [ETR: PrizePicks props vs ETR projections](https://establishtherun.com/prizepicks-props-vs-etr-projections/)
- A US patent covers "calibrating sports statistics projections by player performance tiers". Tier-specific calibration is an established idea. (snippet; patent text not read) — [USPTO 9082074](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9082074)
- Projecting only the most likely outcome undersells players with bimodal or skewed outcome distributions. (snippet) — [DraftSharks](https://feature.draftsharks.com/article/the-danger-of-relying-too-heavily-on-projections)
- Sportsbooks set lines from more than mean projections: liability, sharp action and line movement. (snippet) — [Bleacher Nation](https://www.bleachernation.com/?p=2622938)
- Historical under rates (betting media, small self-reported samples, so treat with caution):
  - PFF puts weekly player-prop unders at about 55% in 2017-2019, with 2021 "historic" for unders. Passing-yard unders were the only profitable category from 2020 to the 2022 midseason (+14.06u). — [PFF 2022 midseason review](https://pff.com/news/nfl-betting-2022-midseason-player-prop-performance-review); [PFF 2020 wk11](https://pff.com/news/bet-nfl-betting-2020-week-11-thursday-night-football-player-props)
  - For season-long props: Action Network reports unders at 71.2% (2017) and 61.0% (2018), and 4for4 reports 61% across 2021-22, with passing-yard unders at 78%/71%. Season-long props are a different market from weekly ones. — [Action Network](https://www.actionnetwork.com/nfl/nfl-betting-player-props-over-unders-season-long-percentages); [4for4](https://www.4for4.com/2023/preseason/key-winning-season-long-player-props)

### Inferences (diagnostics and fixes for our under bias)
- **Scale < 1 is the prime suspect.** A per-market scale of 0.88-0.98 multiplies the mean, so a 300-yd QB loses 6-36 yards while a 150-yd QB loses 3-18. If the scale was fitted to fix PIT/Brier overall, it may be compensating for a different defect, such as variance too small, mean too high for low-tier players, or the mean/median gap. A single multiplicative scale cannot fix tier-dependent bias and will push elite players under. Use an additive plus slope recalibration fitted by tier, or an isotonic map from model P(over) to empirical P(over), instead of scaling the projection.
- **Mixing up a distribution's mean and median.** If the calibration target is P(X > line) and the line sits near the median, fit the calibration on probabilities, not on means. Scaling the mean down to fix an over-predicted P(over) double-counts skew.
- **Over-shrinkage to position averages.** Use empirical-Bayes weights: w = n / (n + k), where k = (within-player noise variance) / (between-player true variance), estimated per stat. Use a role or tier prior (WR1 vs WR3, alpha by aDOT/route share) rather than the position mean. Flat position-mean shrinkage compresses everyone toward the middle and under-projects the best.
- **Compounding shrinkage.** Shrinking shares (Dirichlet), catch rate, YPC and team volume each a bit produces a product that is shrunk a lot. Check by regressing actual stats on projected stats out of sample. A slope above 1 means the projection is over-shrunk; ideally the slope is about 1 and the intercept about 0.
- **Bias by tier.** Bin residuals (actual - projection) by projection decile and by market-line decile. If residuals are positive in the top deciles and negative in the bottom deciles, the model is over-regressed.
- **Some under lean is legitimate**, given about 55% historical under rates and the public over bias. But if more than about 65-70% of picks are unders, and they cluster on high-line players, the model is miscalibrated relative to the market rather than finding edge.
- **The 50/50 blend with FanDuel no-vig** partly masks the problem, but it also halves any true edge. Fit the blend weight walk-forward, possibly by market or tier, rather than fixing it at 0.5.

### Gaps
- No public NFL-specific study found that quantifies projection bias by player tier.
- The patent's tier-calibration method was not read in full.

## Q4. Validation (walk-forward, CRPS/pinball, closing lines, Brier, reliability, pick balance, ROI; historical prop-line sources)

### Takeaway
Rigorous public NFL prop-model validation write-ups are scarce. Practitioners use walk-forward or cross-validated MAE for point projections, quantile intervals for coverage, and hit rate or ROI against lines. Historical prop lines are available from The Odds API from May 3, 2023 onward (paid; event-level endpoint; 5-minute snapshots), and also from SportsDataIO, Sportradar and some aggregators.

### Cited Findings
- The Odds API: historical odds for additional markets, including player props, are available from May 3, 2023, with snapshots at 5-minute intervals. They must be queried one event at a time via the historical event-odds endpoint, on paid plans only. Featured markets go back to 2020. — [The Odds API Historical Odds Data](https://the-odds-api.com/historical-odds-data/); [Betting markets list](https://the-odds-api.com/sports-odds-data/betting-markets.html)
- SportsDataIO sells historical odds (the "Vault") and publishes a historical-data integration guide. Sportradar has an odds-comparison player-props product. (unverified depth of NFL prop history) — [SportsDataIO historical odds](https://sportsdata.io/historical-odds); [SportsDataIO guide](https://sportsdata.io/help/historical-data-integration-guide); [Sportradar player props](https://developer.sportradar.com/odds/reference/oc-player-props-overview)
- Other sources: Apify's "NFL Player Props Scraper" (DraftKings lines and O/U results), and OddsPapi blog posts on rebuilding closing lines from historical calls. (third-party; claims unverified) — [Apify](https://apify.com/datawright/nfl-player-props-scraper); [OddsPapi closing line](https://oddspapi.io/blog/?p=5269)
- Princeton thesis: evaluates by season-level MAE vs ESPN projections and by 80% quantile intervals (pinball-loss-style training). (snippet) — [Princeton thesis](https://theses-dissertations.princeton.edu/entities/publication/d6981488-f30c-47ce-8f06-b6c3e98f2578)
- DensOrd: cross-validated test accuracy used to tune KDE smoothing; no explicit reliability check. — [NFL_DensOrd](https://www.github.com/paulcbogdan/NFL_DensOrd)
- Pick tracking by media outlets: the Fantasy Footballers DFS Pass tracked 181 props at a 57.5% hit rate, and PFF publishes midseason prop performance reviews by category, with units. — [Fantasy Footballers recap](https://www.thefantasyfootballers.com/props/nfl-player-props-recap-strategy-takeaways-2023-dfs-pass-fantasy-football/); [PFF review](https://pff.com/news/nfl-betting-2022-midseason-player-prop-performance-review)

### Inferences (recommended validation stack)
- Walk-forward by week, with features computed strictly as of the bet time. Score with:
  - CRPS (or pinball loss at 10/25/50/75/90) for the full distribution.
  - PIT histograms by market and by tier.
  - Brier and log-loss on P(over the closing line).
  - Reliability diagrams of predicted P(over) vs realized P(over).
- Market-relative checks:
  1. Mean of (model median - line) by market and by line decile. This should be about 0 overall, with no trend against the line.
  2. Over/under pick share, both overall and by tier.
  3. CLV: did the line move toward the model's side between the open (or bet-time) snapshot and the close? The Odds API's 5-minute snapshots support this from 2023-05-03.
  4. ROI at actual juice, with bootstrap CIs, because 1-2 seasons of props is a small sample.
- A model that beats the closing line on Brier/log-loss is rare. Beating a no-vig close on log-loss is a stronger test than raw hit rate.

### Gaps
- No public NFL prop model found that publishes CRPS, reliability diagrams or CLV results.
- BettingPros and Kaggle historical prop datasets were not verified in this pass.

## Q5. ML (XGBoost/LightGBM) vs Bayesian simulation; ensembles

### Takeaway
Public work leans toward gradient boosting for point and quantile projection (ffopportunity, the Princeton thesis), and toward simulation for coherent joint distributions (DraftKings combines both: ML models inside a Monte Carlo). The common hybrid uses ML to predict per-play or per-game parameters (shares, efficiency, volume) from rolling usage, Vegas implied totals and opponent adjustments, then simulates to get correlated distributions.

### Cited Findings
- DraftKings explicitly combines ML models with Monte Carlo simulation: ML classifiers provide per-play outcome distributions that the simulator samples. (snippet) — [DraftKings Engineering](https://medium.com/draftkings-engineering/modeling-football-combining-ml-models-and-monte-carlo-simulations-170fd58cbe11)
- ffopportunity uses XGBoost on play-by-play to estimate expected fantasy points per opportunity. — [ffopportunity](https://github.com/ffverse/ffopportunity)
- Per-position XGBoost with quantile heads beat ESPN on MAE (2.909 vs 3.074) in a 2025 test. (snippet) — [Princeton thesis](https://theses-dissertations.princeton.edu/entities/publication/d6981488-f30c-47ce-8f06-b6c3e98f2578)
- Ensemble of position-based regressors, plus fitting from 24 candidate distributions (IBM/ESPN). — [arXiv 2111.02874](https://arxiv.org/pdf/2111.02874)
- FTN's prop write-ups cite model inputs such as projected pass attempts (e.g., Dak Prescott at 32.9, "7th-fewest") and pass/run tendencies. Volume projection is front and center. (snippet) — [FTN Fantasy](https://ftnfantasy.com/?p=42796)

### Inferences
- A practical redesign keeps the simulator, which is good for correlation and SGPs. Replace the hand-set efficiency shrinkage with ML-predicted, player-specific parameters (target share, aDOT, catch rate, YPT, carries, YPC). Use rolling usage (snap%, route%, TPRR, air-yard share), ffopportunity expected points, implied team total and spread, and opponent-adjusted defense as features. Train walk-forward so the shrinkage is learned from data rather than imposed.
- Use the market line itself as a feature or prior. The 50/50 blend is a crude version of this. A learned weight, or stacking model and market, usually beats a fixed blend.

### Gaps
- No head-to-head public comparison found of GBM vs Bayesian simulation for NFL props against market lines.
