#!/usr/bin/env python3
"""Walk-forward calibration backtest of the projection model.

For every game in the chosen weeks, the model is fitted on data from BEFORE that week
only, simulated with that game's pregame spread/total and starting QBs, and the
actual stat is located inside the simulated distribution (the PIT value).
A calibrated model gives PIT values that are uniform: ~50% of results inside the
central 50% interval, ~80% inside the 80% interval, ~50% above the median, etc.

It also scores synthetic "lines" at each player's simulated 30th/50th/70th percentiles,
which shows whether P(over) estimates are honest.

Usage: python3 backtest.py --season 2026 --weeks 4-10 [--season2 2025 --weeks2 4-18]
                           [--param kappa_tgt=28 ...] [--out results.json]
"""
import argparse
import json
import sys

import numpy as np
import pandas as pd

from engine.data import Data, norm
from engine.model import MARKETS, MIN_ROLE, NFLV_COL, Model


def weeks(s):
    a, b = s.split("-")
    return range(int(a), int(b) + 1)


def run(season, wks, params, n_sims, rng, calibrate=True):
    D = Data(season, max_age_h=48)
    rows = []
    for w in wks:
        dw = D.before(w)
        if dw.player.week.nunique() < 3:
            continue
        M = Model(dw, dict(params, n_sims=n_sims), calibrate=calibrate)
        G = D.games[(D.games.season == season) & (D.games.week == w) & D.games.result.notna()]
        act = D.player[D.player.week == w]
        snaps = D.snaps[D.snaps.week == w] if len(D.snaps) else pd.DataFrame()
        for g in G.itertuples():
            qbs = {g.home_team: g.home_qb_name, g.away_team: g.away_qb_name}
            out, inc = {}, {}
            for t in (g.home_team, g.away_team):
                played = set(snaps[(snaps.team == t) & (snaps.offense_snaps > 0)].nname) if len(snaps) \
                    else set(act[act.team == t].nname)
                hist = set(dw.player[dw.player.team == t].nname)
                out[t] = hist - played          # inactives / did not play (known pregame)
                inc[t] = played
            res, _ = M.simulate_game(g.home_team, g.away_team, g.spread_line, g.total_line,
                                     qbs=qbs, out=out, must_include=inc, seed=int(rng.integers(1e9)))
            for (t, nm), r in res.items():
                a = act[(act.team == t) & (act.nname == nm)]
                if not len(a):
                    continue
                a = a.iloc[0]
                for m in MARKETS:
                    if m not in r:
                        continue
                    sims = r[m]
                    med = float(np.median(sims))
                    if med < MIN_ROLE[m]:
                        continue
                    y = float(a[NFLV_COL[m]])
                    lo, eq = float(np.mean(sims < y)), float(np.mean(sims == y))
                    pit = lo + rng.random() * eq
                    qs = np.percentile(sims, np.arange(1, 100))
                    q = qs[[29, 49, 69]]
                    lines = [np.floor(v) + 0.5 for v in q]
                    rows.append(dict(season=season, week=w, team=t, player=r["name"], market=m,
                                     actual=y, mean=float(sims.mean()), median=med, pit=pit,
                                     **{f"p_over_{i}": float(np.mean(sims > L)) for i, L in enumerate(lines)},
                                     **{f"hit_{i}": float(y > L) for i, L in enumerate(lines)},
                                     flags=",".join(r["flags"]),
                                     q=" ".join(f"{v:.2f}" for v in qs)))
        print(f"  {season} wk{w}: {len(rows)} rows so far", file=sys.stderr)
    return rows


def summarize(df):
    out = {}
    for m, x in list(df.groupby("market")) + [("ALL", df)]:
        p = x.pit.values
        po = np.concatenate([x[f"p_over_{i}"].values for i in range(3)])
        hi = np.concatenate([x[f"hit_{i}"].values for i in range(3)])
        brier = float(np.mean((po - hi) ** 2))
        # calibration by predicted-probability bucket
        bins = np.clip((po * 10).astype(int), 0, 9)
        cal = {f"{b/10:.1f}-{(b+1)/10:.1f}": [round(float(po[bins == b].mean()), 3),
                                               round(float(hi[bins == b].mean()), 3), int((bins == b).sum())]
               for b in range(10) if (bins == b).sum() >= 20}
        out[m] = dict(n=len(x), in50=round(float(np.mean((p > .25) & (p < .75))), 3),
                      in80=round(float(np.mean((p > .1) & (p < .9))), 3),
                      above_median=round(float(np.mean(p > .5)), 3),
                      mean_pit=round(float(p.mean()), 3),
                      bias=round(float((x.actual - x["mean"]).mean()), 2),
                      brier=round(brier, 4), calibration=cal)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--weeks", default="4-10")
    ap.add_argument("--season2", type=int)
    ap.add_argument("--weeks2")
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--out")
    ap.add_argument("--raw", action="store_true", help="disable calibration layer (for fitting it)")
    a = ap.parse_args()
    params = {k: float(v) for k, v in (s.split("=") for s in a.param)}
    rng = np.random.default_rng(7)
    rows = run(a.season, weeks(a.weeks), params, a.sims, rng, not a.raw)
    if a.season2:
        rows += run(a.season2, weeks(a.weeks2), params, a.sims, rng, not a.raw)
    df = pd.DataFrame(rows)
    s = summarize(df)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "calibration"} for k, v in s.items()}, indent=1))
    if a.out:
        df.to_csv(a.out.replace(".json", ".csv"), index=False)
        json.dump(dict(params=params, summary=s), open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
