# Results ledger — updated 2026-11-26

1 unit per pick at the logged FanDuel price. CLV = closing implied probability minus logged implied probability (positive = beat the close). Small samples are noise: judge the model on CLV and calibration first, profit last.

## Overall

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| Top picks | 15 | 7-8 | -1.93 | -12.9% | — | 58% exp / 47% act |
| Long shots | 5 | 0-5 | -5.00 | -100.0% | — | 13% exp / 0% act |
| Avoided (not bet) | 1 | 0-1 | -1.00 | -100.0% | — | 49% exp / 0% act |
| Parlay C legs | 1 | 1-0 | +0.31 | +31.2% | — | 71% exp / 100% act |
| Streak singles (no parlay fit) | 2 | 1-1 | -0.40 | -19.9% | — | 63% exp / 50% act |

## Top picks by tier

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| Bet | 5 | 3-2 | +0.53 | +10.6% | — | 58% exp / 60% act |
| v1 (pre-model) | 10 | 4-6 | -2.46 | -24.6% | — | — |

## By market

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| reception_yds | 6 | 2-4 | -2.23 | -37.2% | — | 59% exp / 33% act |
| receptions | 3 | 2-1 | +0.65 | +21.5% | — | 58% exp / 67% act |
| rush_yds | 6 | 3-3 | -0.34 | -5.8% | — | 57% exp / 50% act |

## By side

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| Over | 10 | 4-6 | -2.46 | -24.6% | — | — |
| Under | 5 | 3-2 | +0.53 | +10.6% | — | 58% exp / 60% act |

## Calibration (blended probability bucket)

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| (0.55, 0.6] | 5 | 3-2 | +0.53 | +10.6% | — | 58% exp / 60% act |

## Who has been more accurate? (Brier score on graded top picks, lower is better)

Model 0.2557 · Market (no-vig) 0.2445 · Blend 0.2450 (n=5). Raise --model-weight only if the model beats the market here over 150+ picks and average CLV is positive.

## By week

| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |
|---|---|---|---|---|---|---|
| 2026-11-15 | 10 | 4-6 | -2.46 | -24.6% | — | — |
| 2026-11-22 | 5 | 3-2 | +0.53 | +10.6% | — | 58% exp / 60% act |

## Parlays

| Date | Type | Legs | Model prob | Fair odds | Result |
|---|---|---|---|---|---|
| 2026-11-15 | parlay_a | Trey McBride Over 6.5 Receptions + Jaylen Warren Over 64.5 Rush Yds + Christian McCaffrey Over 61.5 Rush Yds + Jaxon Smith-Njigba Over 89.5 Rec Yds | — | — | loss |
| 2026-11-15 | parlay_b | Christian McCaffrey Over 61.5 Rush Yds + George Kittle Over 61.5 Rec Yds + Brock Purdy Over 21.5 Rush Yds | — | — | loss |
| 2026-11-22 | parlay_c1 | Stefon Diggs 30+ Rec Yds + Justin Jefferson Under 84.5 Rec Yds | 0.4132 | 142.0 | loss |
