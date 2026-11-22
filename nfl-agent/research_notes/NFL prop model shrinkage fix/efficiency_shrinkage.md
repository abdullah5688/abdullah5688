# Regressing NFL Player Efficiency Stats Without Over-Shrinking Elite Players

Research context: the current model shrinks YPT, catch rate and YPC toward position averages, with last season at half weight. It projects Brock Purdy (about 9.0 YPA this season) at about 6.8 YPA and Amon-Ra St. Brown (median 75 receiving yards) at 59.

Access note: WebFetch could not reach footballguys.com, 4for4.com, sumersports.com, footballperspective.com or baseball-reference.com because they are outside the session's allowed network domains. Every figure below therefore comes from search-result excerpts of those pages, not full-text reads. To verify sample thresholds and methods, those domains would need to be allowed.

## 1. Published stabilization points and year-to-year reliability for NFL stats

### Takeaway
Volume and usage stats are the stickiest. Target share and targets per route run have a year-over-year r of about 0.55. Per-play efficiency stats are much noisier: yards per target has R² of about 0.08, YPC is close to random, and RYOE has r of about 0.21. QB YPA sits in between, at a 50/50 point of about 396 attempts, so a full QB season should keep roughly half of its deviation from the mean. None of the published numbers justify pulling a 9.0-YPA QB below league average.

### Cited Findings
- **QB yards per attempt:** about 396 pass attempts before a QB's YPA is half skill and half luck. Harstad, citing Danny Tuccitto's stabilization research, describes this as "a little bit less than a full season." — [Footballguys, Harstad "Regression Alert: Be Very Wary of Yards per Carry"](https://www.footballguys.com/article/HarstadRegression02)
- **Yards per carry:** stabilizes at 1,978 carries, which in practice means "never." Harstad calls YPC "basically a random number generator." — [Footballguys HarstadRegression02](https://www.footballguys.com/article/HarstadRegression02); [Footballguys 2021 Regression Alert Wk 8](https://www.footballguys.com/article/2021-regression-alert-week-08)
- **Year-to-year correlations, 2005–2015 (Wharton student study):** YPA r = 0.392, which the authors call "surprisingly low." Completion % was the most reliable stat in the study and YPC the most volatile. — [Wharton, 2017 NFL Cherry Yr2Yr](https://wsb.wharton.upenn.edu/wp-content/uploads/2022/01/2017_NFL_Cherry_Yr2Yr-1.pdf)
- **Net yards per attempt:** QBs with at least 100 attempts for the same team in consecutive seasons since 1970 give R² = 0.24. Each extra yard of NY/A in Year N predicts about half a yard of NY/A in Year N+1, so the slope is about 0.5. — [Football Perspective, regression tag](http://www.footballperspective.com/tag/regression/)
- **Split method:** Football Perspective prefers even/odd game splits over first-half/second-half splits so that injuries and roster changes don't bias the result. — [Football Perspective, yards tag](https://www.footballperspective.com/tag/yards/)
- **CPOE:** the 2022→2023 year-over-year r is 0.46, rising to 0.51 after noisy plays are filtered out (SumerSports, charting data, two seasons only). — [SumerSports, "Cutting through noise to increase CPOE stability"](https://sumersports.com/the-zone/cutting-through-noise-to-increase-cpoe-stability/). NFELO reports a CPOE year-over-year R² of about 0.226 and calls that "about as good as it gets." — [nfeloapp, Over Expected Explained](https://www.nfeloapp.com/analysis/over-expected-explained-what-are-cpoe-ryoe-and-yacoe/)
- **QB EPA:** PFF found that a QB's execution/decision measure predicts next-year EPA better (R = 0.46) than prior EPA does (R = 0.43). — [PFF, Evaluating QB decision-making](https://www.pff.com/news/nfl-evaluating-quarterbacks-decision-making-process)
- **Yards per target:** N+1 Y/T = 5.84 + 0.28 × (Year N Y/T), R² = 0.08, so it is "not very sticky." In the same analysis, targets per route run is "a very sticky metric." — [Football Perspective, YPRR / Y/T / TPRR](https://www.footballperspective.com/yards-per-route-run-yards-per-target-and-targets-per-route-run/)
- **Yards per target as a usage stat:** Harstad argues that Y/T measures usage more than efficiency. Across 180 receivers, yards per reception correlated 0.70 with Y/T, and 28 of 31 outliers were *over*performing their expected Y/T. — [Footballguys, "When Yards Per Target is Off Target"](https://www.footballguys.com/article/HarstadRegression03). Another Footballguys projection piece says Y/T "even when only looking at the best receivers, isn't a very sticky metric." — [Footballguys, How to Project Receiving Yards](https://www.footballguys.com/article/stuart_projecting_receiving_yards)
- **YPRR:** year-over-year 0.51, and Expected YPRR 0.67 (SumerSports). — [SumerSports, Revisiting YPRR](https://sumersports.com/the-zone/revisiting-yards-per-route-run/). 4for4 puts WR YPRR at 0.56 for 2017–2023, below targets per game and yards per game. It names YPRR and first downs per route run as the most predictive efficiency stats. — [4for4, Most Predictable WR Stats 2024](https://www.4for4.com/2024/preseason/most-predictable-wide-receiver-stats)
- **Target share:** WR year-over-year r = 0.55 for 2012–2022, with air-yards share at 0.53 (4for4). — [4for4, Most Predictable WR Stats 2023](https://www.4for4.com/2023/preseason/most-predictable-wide-receiver-stats). Sharp Football says team target share and targets per route run "hold some water in remaining stable." — [Sharp Football, WR stats that matter](https://www.sharpfootballanalysis.com/fantasy/wide-receiver-stats-that-matter-fantasy-football-2024/)
- **PFF receiving grade per slot target:** player-level stability of only 0.232. — [PFF, value of receiver and coverage positions](https://www.pff.com/news/pro-pff-forecast-examines-value-of-coverage-and-receiving)
- **RYOE:** PFF's version has a year-to-year r = 0.21. — [PFF, plays over expectation](https://www.pff.com/news/nfl-plays-over-expectation-pff-research-stats-grades). Another site says RYOE has "almost no predictiveness" season to season, close to a coin flip. — [nfeloapp](https://www.nfeloapp.com/analysis/over-expected-explained-what-are-cpoe-ryoe-and-yacoe/). For YPC, R² stays very low even for backs with 250+ carries in consecutive seasons. — [Football Perspective, How sticky is YPC](http://www.footballperspective.com/how-sticky-is-yards-per-carry-from-year-to-year/)
- **Team-level DVOA, for context:** year-to-year r is about 0.37. For 2011–2021 it was 0.42 for offense, 0.38 for defense and 0.36 for special teams. DVOA v8.0 raised the 2013–2022 DVOA-to-DVOA Y+1 correlation from 0.424 to 0.457. — [FO, Introducing DVOA v7.3](https://footballoutsiders.com/dvoa-ratings/2020/introducing-dvoa-v73); [FTN, Introducing DVOA v8.0](https://ftnfantasy.com/nfl/introducing-dvoa-v8-0)

### Inferences
- **Converting stabilization points to phantom samples.** A stabilization point N50, where split-half or between-season r = 0.5, is the same quantity as the number of league-average "phantom" attempts to add: regressed = (n·x + k·μ) / (n + k), with k ≈ N50. For YPA, k ≈ 400 attempts. A QB with 450 attempts at 9.0 YPA and a prior mean of 7.0 regresses to about (450·9 + 400·7) / 850 ≈ 8.06, not 6.8.
- **A below-average projection means a bug.** Any linear shrinkage toward a mean μ has to land *between* the observed value and μ. Since league YPA is roughly 7.0 and our projection of 6.8 is below the prior, the model is doing something other than shrinkage. Likely causes are a mean that includes backups, or a second multiplicative haircut such as a calibration scale or opponent adjustment applied on top. Section 5 covers these.
- **Different stats need very different k.** YPA needs k ≈ 400 attempts. YPC needs k ≈ 2,000 carries, which is close to full shrinkage within a season. Y/T needs heavy shrinkage too: a slope of 0.28 implies k of about 2.5× a typical season's target count. The k values should come from the data per stat, not from one shared rule.
- **Y/T is driven by aDOT/role.** Harstad's point means the prior for Y/T should be conditional on the receiver's aDOT and role, not the all-WR mean. A deep threat and a slot receiver have different true Y/T. Most of the "regression" seen when pooling all WRs is actually a regression toward the wrong role mean.

### Gaps
- I found no published split-half number for nflfastR EPA/dropback or ANY/A. The search turned up no ANY/A-specific year-to-year r; NY/A (R² 0.24) is the closest proxy.
- I found no published catch-rate stabilization point. The Wharton study says completion % is the most reliable QB stat but gives no figure in the excerpts.
- The original Tuccitto stabilization study (thresholds and method) couldn't be fetched.
- The 4for4 and SumerSports sample thresholds couldn't be verified because the sites were blocked.

## 2. Empirical Bayes / beta-binomial / hierarchical shrinkage and baseball analogues (Tango, Marcel)

### Takeaway
The standard tool is empirical Bayes with phantom samples. For rate stats like catch rate and completion %, that means a beta-binomial posterior (successes + α) / (n + α + β), whose shrinkage weight is κ / (κ + n) with κ = α + β. For continuous per-play stats, the normal-normal analogue uses k = σ²_noise / σ²_true. Marcel adds a fixed amount of league average (1,200 PA) to multi-year, 5/4/3-weighted history. The more history a player has, the less he regresses.

### Cited Findings
- **Beta-binomial posterior mean:** (successes + α) / (attempts + α + β), with α and β fitted by maximum likelihood across players. — [r-statistics.co, Empirical Bayes in R](https://r-statistics.co/Empirical-Bayes-in-R.html). The same method is implemented in David Robinson's `ebbr` package, including `add_ebb_estimate` and beta-binomial regression on covariates. — [GitHub dgrtwo/ebbr](https://github.com/dgrtwo/ebbr)
- **Shrinkage weight:** κ / (κ + n), where κ = α + β is the effective prior sample size. Hyperparameters can come from method of moments or the beta-binomial marginal likelihood (Efron-Morris baseball example). — [metricgate, Hierarchical Beta-Binomial](https://metricgate.com/docs/hierarchical-beta-binomial-baseball/). A parametric prior can misfit, and nonparametric EB is an alternative. — [metricgate, Empirical Bayes](https://metricgate.com/docs/empirical-bayes/)
- **Marcel:** weights the last three seasons 5/4/3 and adds league average equal to 1,200 PA (2 weights × 600 PA) per player. — [Tango on Baseball Archives](https://www.tangotiger.net/archives/stud0214.shtml)
- **Marcel regression share:** about 50% for about 300 weighted PA and about 14% for about 1,800 PA. — [Tango archives](https://tangotiger.net/archives/stud0346.shtml)
- **Reliability and data:** Marcel's reliability factor rises with the amount of data a player has. — [MLB.com glossary, Marcel](https://www.mlb.com/glossary/projection-systems/marcel-the-monkey-forecasting-system)
- **Sample size is the core of projection:** a model that ignores the sample size behind a performance "is missing the fundamental job of a projection." — [Saber Powers, SMGT 435 projections lecture](https://saberpowers.github.io/teaching/smgt435/lecture/projections.pdf)
- **Variance decomposition:** var(observed) = var(true) + var(random), and "the more random the process, the stronger regression will be" (Burke). — [Advanced Football Analytics, Randomness of Win-Loss Records](http://www.advancedfootballanalytics.com/2010/11/randomness-of-win-loss-records.html)
- **nflWAR's multilevel model:** not explicitly Bayesian, but still shrinks individual player estimates toward group averages. — [nflWAR, arXiv:1802.00998](https://arxiv.org/pdf/1802.00998)
- **Empirical Bayes completion-% surfaces:** next-gen-scraPy estimates each QB's completion-% surface by pass location using an empirical Bayesian approach. — [arXiv:1906.03339](https://ar5iv.labs.arxiv.org/html/1906.03339)
- **Bayesian multilevel QB random effects (snap timing):** — [Nguyen & Yurko, arXiv:2502.16313](https://arxiv.org/abs/2502.16313)
- **Shrinkage helps less in the NFL:** for NFL team strength it improved out-of-sample MSE by about 16.8%, a smaller gain than in the NBA because of fewer games and a sparser schedule network. — [arXiv:1807.09236](https://arxiv.org/pdf/1807.09236)

### Inferences
- **Phantom attempts to add, per stat.** These derive from Section 1 and are rough; refit them on nflverse data.
  - YPA: about 400 attempts.
  - YPC: about 2,000 carries, which is nearly full shrinkage to an O-line/scheme-adjusted mean.
  - Y/T: a single-season slope of about 0.28 implies k of about 2.5 seasons of targets, but only *toward a role/aDOT-conditional mean*.
  - Catch rate / completion %: fit α + β by beta-binomial MLE. They are believed to be more stable, so κ should be smaller.
- **Marcel-style multi-season pooling for NFL.**
  - Weight seasons, for example 5/4/3 or a decay, and add k league-mean (or role-mean) phantom plays once to the *pooled* history.
  - Don't shrink each season separately and then average them.
  - Our current approach (last season at half weight, shrunk to the position mean) throws away career history, which is the main thing that separates elite players from flukes.
- **Fit k by stat and by position.** Use σ²_true = var(observed) − mean(σ²_noise / n) across qualified players, then k = σ²_noise / σ²_true.

### Gaps
- I found no NFL-specific published beta-binomial fit with α and β for catch rate or completion %.
- I didn't fetch David Robinson's Variance Explained posts directly; the method is cited via ebbr instead.

## 3. Player-specific priors: career history, draft capital, age, team/scheme context, role tiers

### Takeaway
I found little public NFL work on hierarchical priors conditioned on covariates. The evidence that does exist points the same way: shrink toward an *expected* value built from role and usage, not toward the position mean. Expected YPRR is stickier than YPRR (0.67 vs 0.51), and Y/T is mostly explained by usage (yards per reception r = 0.70). Rookie models lean on draft capital, YPRR and age.

### Cited Findings
- **Expected YPRR vs YPRR:** Expected YPRR has a year-over-year stability of 0.67, compared with 0.51 for raw YPRR. Receivers' situations, meaning role and usage, persist from season to season. — [SumerSports, Revisiting YPRR](https://sumersports.com/the-zone/revisiting-yards-per-route-run/)
- **Y/T depends on usage:** Y/T is largely a function of usage, with yards per reception correlating 0.70 with Y/T, and Harstad gives a best-fit expected-Y/T equation. — [Footballguys HarstadRegression03](https://www.footballguys.com/article/HarstadRegression03)
- **Rookie WR models:** draft capital is the most weighted input, mapped through a non-linear pick-value curve. Other inputs are YPRR, breakout age, college production and age. — [Fantasy Life, WR Rookie Super Model](https://www.fantasylife.com/articles/redraft/2024-wr-rookie-super-model-tier-1-and-2-wide-receivers); [PFF rookie WR prospect model](https://www.pff.com/news/draft-fantasy-football-rookie-wide-receiver-prospect-model)
- **QB execution vs results:** a QB's execution predicts future EPA better than past EPA does. That supports shrinking QB results toward a skill-based prior (CPOE, grade) rather than a league mean. — [PFF](https://www.pff.com/news/nfl-evaluating-quarterbacks-decision-making-process)
- **Hits/pressure confound QB per-play EPA:** pressure is a context covariate that a QB prior should account for. — [Open Source Football, QB hits vs efficiency](https://opensourcefootball.com/posts/2020-08-19-the-accumulation-of-qb-hits-vs-passing-efficiency/)
- **Marcel's league-average component:** Tango determines each player's own league average (by context) before adding the 1,200 PA. — [Tango archives](https://www.tangotiger.net/archives/stud0214.shtml)

### Inferences
- **Prior mean, recommended form.** μ_player = f(role tier, aDOT, route share, team pass rate, QB quality, age, draft capital), fitted as a regression across player-seasons. Then shrink observed efficiency toward μ_player, not toward the all-WR or all-QB mean.
  - For WRs, define tiers by target share or routes (for example WR1 with ≥22% target share vs WR3), or use continuous covariates.
  - For QBs, condition on a career-weighted prior plus offense/scheme (EPA/play of the offense, receiver quality).
  - For RBs, take YPC almost entirely from team/O-line rushing context plus RYOE, heavily shrunk.
- **Covariate priors have smaller residual variance.** Because they explain part of the true talent, σ²_true around μ_player is smaller. That matters in two directions:
  - A good covariate prior can sit close to elite players' true level, so the shrinkage *does no harm* even though k may be large.
  - Pooling across all players with a single mean makes k look smaller than it really is, yet it still pulls elite players hard, because the gap between their true talent and the mean is large.
- **Career history is the strongest prior for veterans.** Purdy and St. Brown each have three or more seasons of high-efficiency data. Pooling 3+ seasons gives n_eff of roughly 1,000+ attempts or 400+ targets, which leaves the shrinkage share at about 30% or less, Marcel-style.

### Gaps
- I found no public NFL paper that fits a full hierarchical Bayesian model with draft capital, age and team-context priors for per-play efficiency.
- I found no published NFL efficiency age curves (YPA, Y/T by age) in this search.

## 4. Volume vs efficiency: what is stable and how to split modeling

### Takeaway
Volume and usage stats are stable and need little shrinkage: target share r ≈ 0.55, targets per route run "very sticky," and targets or yards per game rank above YPRR. Efficiency stats (Y/T R² 0.08, YPC, RYOE r 0.21) need heavy shrinkage toward a role-conditional prior. Standard practice is to project volume (snaps → routes/dropbacks/carries → targets/attempts) separately from efficiency per opportunity, then multiply.

### Cited Findings
- **Target share:** r = 0.55, among the most stable WR stats. — [4for4 2023](https://www.4for4.com/2023/preseason/most-predictable-wide-receiver-stats); [Fantasy Classroom WR sticky stats](https://fantasyclassroom.org/Blogs/sticky-stats/wr-sticky-season-totals)
- **Targets per route run vs Y/T:** targets per route run is "a very sticky metric," while Y/T has R² 0.08. — [Football Perspective](https://www.footballperspective.com/yards-per-route-run-yards-per-target-and-targets-per-route-run/)
- **YPRR ranks below volume stats:** YPRR (0.56) is less stable than targets per game and yards per game. — [4for4 2024](https://www.4for4.com/2024/preseason/most-predictable-wide-receiver-stats)
- **RB volume vs efficiency:** volume and opportunity stats are more predictable than per-carry efficiency. — [4for4, Most Predictable RB Stats](https://www.4for4.com/2023/preseason/most-predictable-running-back-stats); [Sharp Football, RB stats that matter](https://www.sharpfootballanalysis.com/fantasy/running-back-stats-that-matter-fantasy-football-2024/)
- **Hermsmeyer's air-yards approach:** aDOT, air yards and RACR, a usage-based approach to predicting receiving production. — [SI 2018, Most Predictable WR Stats](https://www.si.com/nfl/2018/08/01/fantasy-football-2018-most-predictable-wide-receiver-stats)

### Inferences
- **Recommended decomposition for receiving yards:** Rec Yds = team dropbacks × route share × TPRR × Y/T.
  - Shrink TPRR and route share lightly, since they are stable.
  - Shrink Y/T heavily, but toward a prior conditional on aDOT/role and career.
  - Optionally split Y/T into catch rate × yards per reception, each with its own k.
- **For QBs:** Pass Yds = attempts (team volume) × YPA_shrunk.
- **For RBs:** Rush Yds = carries × YPC_shrunk, where YPC is nearly fully shrunk to a team/line-context mean.
- **Why our St. Brown projection is too low.** A 75 → 59 drop (−21%) implies heavy shrinkage of both catch rate *and* YPT toward an all-WR mean. St. Brown's role (high target share, slot) means his catch rate and YPT priors should be his own career rates, lightly regressed. Shrinking two correlated components separately toward the population mean compounds the haircut, so we may be shrinking one product twice.

### Gaps
- No single source gives a full side-by-side table of year-over-year r for every stat on a common sample. The numbers above come from different samples and thresholds, so their absolute values are not directly comparable.

## 5. Known pitfalls: wrong mean, double-shrinking, selection bias

### Takeaway
The model's failure symptoms point to known pitfalls: Purdy is projected *below* league average, and St. Brown loses 21%.
- The prior mean is too low. It includes backups and low-volume players, whose true efficiency is lower.
- Shrinkage is applied more than once: per-component shrinkage multiplied together, possibly followed by a calibration scale.
- Single-season data at half weight discards the career evidence.

### Cited Findings
- **Use each player's own context mean:** Marcel determines each player's own league-average baseline before regressing. — [Tango archives](https://www.tangotiger.net/archives/stud0214.shtml)
- **Fit priors on the right population:** prior fits are sensitive to population. Pooling different roles distorts α and β, so fit separate priors by position or role. — [metricgate, Empirical Bayes](https://metricgate.com/docs/empirical-bayes/); [r-statistics.co](https://r-statistics.co/Empirical-Bayes-in-R.html)
- **Regression to the mean in groups:** QBs who averaged 150–175 passing yards per game in Year N (mean 165) averaged 178 in N+1, which is how group means move toward the overall mean. — [Footballguys, Stuart, Regression to the Mean](https://subscribers.footballguys.com/apps/article.php?article=stuart_regression_to_the_mean)
- **Selection bias in Y/T outliers:** 28 of 31 receivers whose Y/T was off their expected value were *over*performers. Extreme observed values are mostly upside noise, which is the selection effect regression is meant to correct. Shrinkage should target that noise, not the role-explained component. — [Footballguys HarstadRegression03](https://www.footballguys.com/article/HarstadRegression03)
- **Choice of split:** even/odd splits avoid injury and roster bias when estimating reliability; first-half/second-half splits don't. — [Football Perspective](https://www.footballperspective.com/tag/yards/)

### Inferences
- **Wrong mean.** The position mean for "all WRs with ≥1 target" or "all QBs" is pulled down by backups and garbage-time players, and low-volume players are lower-efficiency on average. That is survivorship and selection: high-efficiency players earn volume.
  - Use a volume-weighted mean (weighted by attempts or targets), or better, a regression prior on role covariates.
  - Fit on qualified starters if you are projecting starters.
- **Double-shrinking, three ways:**
  - Shrinking catch rate and YPT separately and then multiplying, when YPT already includes catch rate.
  - Shrinking the efficiency rate and then applying a global calibration or scale factor fitted on the *unshrunk* residuals.
  - Shrinking within each season and then shrinking the multi-season blend again.
  - Each step pulls elite players further. Calibrate once, on the final output, against out-of-sample results.
- **Too little data.** Using last season at half weight shrinks the effective sample. A Marcel-style 3-season weighted pool with a single phantom-sample addition is the standard fix.
- **Back-of-envelope Purdy check.**
  - Purdy's career YPA is roughly 8.5+ from memory (unverified here). With about 1,500 weighted attempts and k = 400 toward a starter mean of about 7.2, the projection comes to about (1500·8.6 + 400·7.2) / 1900 ≈ 8.3.
  - Sanity check: any projection below the prior mean shows the pipeline is not pure shrinkage.
  - A backtest should show that shrunk projections for top-decile players aren't biased low. Check mean residual by decile of prior-season efficiency; under-projecting elites is the symptom of over-shrinking.

### Gaps
- I found no published NFL article that addresses "double-shrinkage" by name. The points above are methodological inferences from the general empirical-Bayes sources.
- I couldn't verify Purdy's or St. Brown's career per-play numbers in this search, so the worked examples use illustrative values.
