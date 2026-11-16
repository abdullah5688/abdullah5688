#!/usr/bin/env python3
"""Fit the per-market calibration layer from a RAW backtest (backtest.py --raw --out X.json).

What is scored is what matters for betting: P(stat > line) at prop-style half-point
lines. For every backtest row, lines are placed at the raw distribution's 20th/35th/
50th/65th/80th percentiles (rounded to x.5), and the Brier score of the predicted
P(over) vs what happened is minimised over two parameters per market:
  scale  - multiplies the whole distribution (fixes systematic over/under-projection)
  spread - widens/narrows it around the median (fixes over/under-confidence)
The fit uses every season except --holdout-season; the holdout season is then used to
report out-of-sample Brier scores and a reliability table (predicted vs actual
over-rate), so the calibration is tested on games it never saw.

Usage: python3 fit_calibration.py RAW_BACKTEST.csv --holdout-season 2026
Writes engine/calibration.json.
"""
import argparse
import json
from datetime import date

import numpy as np
import pandas as pd

from engine.model import CAL_FILE

PROBS = np.arange(1, 100) / 100
LINE_PCT = [19, 34, 49, 64, 79]  # indexes into the 1..99 percentile table


def prepare(x):
    Q = np.array([list(map(float, s.split())) for s in x.q])
    L = np.floor(Q[:, LINE_PCT]) + 0.5
    Y = (x.actual.values[:, None] > L).astype(float)
    return Q, L, Y


def p_over(Q, L, scale, spread):
    med = Q[:, 49:50]
    T = np.maximum(scale * (med + spread * (Q - med)), 0)
    out = np.empty_like(L)
    for i in range(len(Q)):
        # strictly increasing x for interpolation (break ties of discrete stats)
        xs = T[i] + np.arange(99) * 1e-6
        out[i] = 1.0 - np.interp(L[i], xs, PROBS, left=0.0, right=1.0)
    return np.clip(out, 0.005, 0.995)


def brier(P, Y):
    return float(np.mean((P - Y) ** 2))


def reliability(P, Y):
    p, y = P.ravel(), Y.ravel()
    b = np.clip((p * 10).astype(int), 0, 9)
    return {f"{k/10:.1f}-{(k+1)/10:.1f}": [round(float(p[b == k].mean()), 3), round(float(y[b == k].mean()), 3),
                                           int((b == k).sum())] for k in range(10) if (b == k).sum() >= 15}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--holdout-season", type=int)
    a = ap.parse_args()
    df = pd.read_csv(a.csv)
    out, report = {}, {}
    for m, x in df.groupby("market"):
        fit = x[x.season != a.holdout_season] if a.holdout_season else x
        hold = x[x.season == a.holdout_season] if a.holdout_season else x.iloc[0:0]
        Qf, Lf, Yf = prepare(fit)
        best = None
        for sc in np.arange(0.86, 1.061, 0.02):
            for sp in np.arange(0.85, 1.51, 0.05):
                b = brier(p_over(Qf, Lf, sc, sp), Yf)
                if best is None or b < best[0]:
                    best = (b, round(float(sc), 3), round(float(sp), 3))
        _, sc, sp = best
        out[m] = dict(scale=sc, spread=sp, nonneg=True)
        rep = dict(n_fit=len(fit), brier_fit_raw=round(brier(p_over(Qf, Lf, 1, 1), Yf), 4),
                   brier_fit_cal=round(best[0], 4))
        if len(hold):
            Qh, Lh, Yh = prepare(hold)
            Pr, Pc = p_over(Qh, Lh, 1, 1), p_over(Qh, Lh, sc, sp)
            rep.update(n_holdout=len(hold), brier_holdout_raw=round(brier(Pr, Yh), 4),
                       brier_holdout_cal=round(brier(Pc, Yh), 4),
                       reliability_holdout_cal=reliability(Pc, Yh))
        report[m] = rep
        print(f"{m:14} scale={sc} spread={sp}  " + "  ".join(f"{k}={v}" for k, v in rep.items()
                                                           if not k.startswith("reliability")))
    json.dump(dict(fitted=str(date.today()), source=a.csv, holdout_season=a.holdout_season,
                   markets=out, report=report), open(CAL_FILE, "w"), indent=1)
    print("wrote", CAL_FILE)


if __name__ == "__main__":
    main()
