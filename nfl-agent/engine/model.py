"""Monte Carlo projection model for NFL player props.

For one game it simulates, N times:
  1. game script: final margin ~ Normal(spread, sd) and a shared pace shock;
  2. each team's plays, pass rate (which depends on the simulated margin), pass
     attempts and carries;
  3. how targets and carries are split among the active players (Dirichlet-perturbed
     usage shares), then receptions, receiving yards and rushing yards per player;
  4. the QB's passing yards as the sum of his receivers' yards, so passing and
     receiving props on the same team are correlated by construction.

Role and matchup inputs:
  * usage shares are recency-weighted and, when the expected QB has started 3+ games,
    estimated only from games he started (role-change gate);
  * shares vacated by players who are out are redistributed to active teammates;
  * efficiencies (yards/target, catch rate, yards/carry) are shrunk toward position
    means, use the prior season as extra evidence, and are multiplied by an
    opponent-adjusted defensive factor for that position group;
  * the expected QB's own efficiency scales his receivers' yards per target.
Every simplifying assumption is listed in README_MODEL.md.
"""
import json
import os

import numpy as np
import pandas as pd

from .data import norm

DEFAULTS = dict(
    n_sims=10000,
    half_life=4.0,       # games; recency weighting of usage and volume
    kappa_tgt=28.0,      # Dirichlet concentration of target shares (lower = noisier)
    kappa_car=22.0,      # Dirichlet concentration of carry shares
    rec_cv=0.85,         # CV of yards per single reception
    rush_sd=6.2,         # sd of yards per single carry
    rush_shift=4.0,      # shifted-gamma offset so a carry can lose yards
    eff_noise=0.12,      # per-game lognormal noise on a player's efficiency
    pace_sd=0.08,        # team-level play-count noise (fraction)
    game_pace_sd=0.05,   # shared game-level play-count noise
    rate_sd=0.065,       # team pass-rate noise beyond game script (play-calling variance)
    k_ypt=45.0, k_cr=45.0, k_ypc=70.0,  # shrinkage pseudo-counts (opportunities)
    k_def=5.0,           # shrinkage of defensive factors (games)
    k_vol=4.0,           # shrinkage of team volume factors (games)
    qb_gate_min=3,       # starts needed to estimate shares from that QB's games only
    prev_weight=0.5,     # weight of a prior-season opportunity vs a current one
)
POS_GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "QB": "QB"}


def _wmean(x, w):
    w = np.asarray(w, float)
    return float(np.sum(np.asarray(x, float) * w) / np.sum(w)) if np.sum(w) > 0 else float("nan")


CAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")


def load_calibration(path=CAL_FILE):
    try:
        with open(path) as f:
            return json.load(f)["markets"]
    except (OSError, KeyError, ValueError):
        return {}


def apply_calibration(sims, c):
    """Post-hoc correction fitted by fit_calibration.py on walk-forward backtests:
    widen/narrow around the median by `spread`, then scale by `scale`."""
    if not c:
        return sims
    med = np.median(sims)
    out = c["scale"] * (med + c["spread"] * (sims - med))
    return np.maximum(out, 0.0) if c.get("nonneg", True) else out


class Model:
    def __init__(self, data, params=None, calibrate=True):
        self.d = data
        self.p = dict(DEFAULTS, **(params or {}))
        self.cal = load_calibration() if calibrate else {}
        self._prep()

    # ------------------------------------------------------------------ setup
    def _prep(self):
        d, P = self.d, self.d.player
        g = d.games[d.games.season.isin([d.season, d.season - 1])]
        g = g[g.result.notna() & (g.game_type == "REG")]
        # team-game table with margin (current + prior season, for slope fitting)
        rows = []
        for tdf, season in ((d.team, d.season), (d.team_prev, d.season - 1)):
            if not len(tdf):
                continue
            for r in tdf.itertuples():
                gm = g[(g.season == season) & (g.week == r.week) &
                       ((g.home_team == r.team) | (g.away_team == r.team))]
                if not len(gm):
                    continue
                gm = gm.iloc[0]
                home = gm.home_team == r.team
                margin = gm.result if home else -gm.result
                pts = gm.home_score if home else gm.away_score
                plays = r.attempts + r.carries
                rows.append(dict(season=season, week=r.week, team=r.team, opp=r.opponent_team,
                                 att=r.attempts, car=r.carries, plays=plays,
                                 rate=r.attempts / plays if plays else np.nan,
                                 margin=margin, pts=pts,
                                 pass_yds=r.passing_yards, sacks=r.sacks_suffered))
        tg = pd.DataFrame(rows)
        self.tg_all = tg
        # game-script slope: pass rate vs final margin (pooled, both seasons)
        b, a = np.polyfit(tg.margin, tg.rate, 1)
        self.slope = float(b)
        tg["neutral"] = tg.rate - self.slope * tg.margin
        cur = tg[tg.season == d.season].copy()
        self.tg = cur
        self.lg_plays = float(cur.plays.mean()) if len(cur) else float(tg.plays.mean())
        self.lg_neutral = float(cur.neutral.mean()) if len(cur) else float(tg.neutral.mean())
        # residual sd of margin vs closing spread (recent seasons)
        h = d.games[(d.games.season >= d.season - 3) & d.games.result.notna() & d.games.spread_line.notna()]
        self.margin_sd = float((h.result - h.spread_line).std()) if len(h) > 50 else 13.0
        self.lg_total = float(h.total_line.mean()) if len(h) > 50 else 44.0
        # target / attempt ratio
        cp = P[P.position.isin(["WR", "TE", "RB", "FB", "QB"])]
        self.tgt_ratio = float(cp.targets.sum() / max(1, d.team.attempts.sum())) if len(d.team) else 0.93
        self.tgt_ratio = min(max(self.tgt_ratio, 0.85), 0.98)
        # position efficiency means (current + prev pooled)
        both = pd.concat([P, d.player_prev]) if len(d.player_prev) else P
        self.pos_mean = {}
        for grp in ["WR", "TE", "RB", "QB"]:
            x = both[both.position.map(POS_GROUP) == grp]
            tg_, rc, ry = x.targets.sum(), x.receptions.sum(), x.receiving_yards.sum()
            ca, ryd = x.carries.sum(), x.rushing_yards.sum()
            self.pos_mean[grp] = dict(ypt=ry / tg_ if tg_ else 7.5, cr=rc / tg_ if tg_ else 0.65,
                                      ypc=ryd / ca if ca else 4.2)
        qb = both[both.position == "QB"]
        self.lg_ypa = float(qb.passing_yards.sum() / max(1, qb.attempts.sum()))
        self._defense()

    def _weights(self, n):
        """Recency weights for n games ordered oldest -> newest."""
        age = np.arange(n)[::-1]
        return 0.5 ** (age / self.p["half_life"])

    def _defense(self):
        """Opponent-adjusted defensive factors.

        For defense D and position group G (WR/TE/RB receiving; team rushing), each game's
        yards allowed are compared with what that offense gains against everyone else
        (its season rate), so a defense isn't credited/blamed for opponent strength.
        Factor > 1 means the defense allows more than expected. Shrunk toward 1.
        """
        P = self.d.player.copy()
        P["grp"] = P.position.map(POS_GROUP)
        k = self.p["k_def"]
        self.def_rec, self.def_rush, self.def_plays, self.def_neutral = {}, {}, {}, {}
        rec = P[P.grp.isin(["WR", "TE", "RB"])].groupby(["team", "opponent_team", "week", "grp"])[
            ["targets", "receiving_yards"]].sum().reset_index()
        off_rate = rec.groupby(["team", "grp"]).apply(
            lambda x: x.receiving_yards.sum() / max(1, x.targets.sum()), include_groups=False).to_dict()
        for (dfn, grp), x in rec.groupby(["opponent_team", "grp"]):
            exp = sum(r.targets * off_rate.get((r.team, grp), self.pos_mean[grp]["ypt"]) for r in x.itertuples())
            act = x.receiving_yards.sum()
            n = x.week.nunique()
            ratio = act / exp if exp > 0 else 1.0
            self.def_rec[(dfn, grp)] = (n * ratio + k) / (n + k)
        ru = P.groupby(["team", "opponent_team", "week"])[["carries", "rushing_yards"]].sum().reset_index()
        off_ypc = ru.groupby("team").apply(lambda x: x.rushing_yards.sum() / max(1, x.carries.sum()),
                                           include_groups=False).to_dict()
        for dfn, x in ru.groupby("opponent_team"):
            exp = sum(r.carries * off_ypc.get(r.team, 4.3) for r in x.itertuples())
            n = x.week.nunique()
            ratio = x.rushing_yards.sum() / exp if exp > 0 else 1.0
            self.def_rush[dfn] = (n * ratio + k) / (n + k)
        tg = self.tg
        kv = self.p["k_vol"]
        for dfn, x in tg.groupby("opp"):
            n = len(x)
            self.def_plays[dfn] = (n * (x.plays.mean() / self.lg_plays) + kv) / (n + kv)
            self.def_neutral[dfn] = n * (x.neutral.mean() - self.lg_neutral) / (n + kv)

    # ------------------------------------------------------------ team inputs
    def team_inputs(self, team, opp, team_spread, total):
        """team_spread: expected margin for `team` (positive = favoured)."""
        x = self.tg[self.tg.team == team].sort_values("week")
        kv = self.p["k_vol"]
        n = len(x)
        if n:
            w = self._weights(n)
            f_off = (n * (_wmean(x.plays, w) / self.lg_plays) + kv) / (n + kv)
            neutral = (n * _wmean(x.neutral, w) + kv * self.lg_neutral) / (n + kv)
        else:
            f_off, neutral = 1.0, self.lg_neutral
        f_def = self.def_plays.get(opp, 1.0)
        tot = total if total and total == total else self.lg_total
        plays = self.lg_plays * f_off * f_def * (tot / self.lg_total) ** 0.3
        neutral = neutral + 0.5 * self.def_neutral.get(opp, 0.0)
        return dict(plays=plays, neutral=neutral, margin=team_spread)

    # ----------------------------------------------------------- player pool
    def team_starters(self, team):
        """week -> starting QB name (normalised) for this team's completed games."""
        P = self.d.player
        q = P[(P.team == team) & (P.position == "QB")]
        out = {}
        for wk, x in q.groupby("week"):
            out[wk] = x.sort_values("attempts").iloc[-1].nname
        return out

    def qb_profile(self, qb_norm):
        P = pd.concat([self.d.player, self.d.player_prev]) if len(self.d.player_prev) else self.d.player
        x = P[(P.nname == qb_norm) & (P.position == "QB")]
        att, yds = float(x.attempts.sum()), float(x.passing_yards.sum())
        prior = self.lg_ypa if att >= 50 else self.lg_ypa - 0.6  # debut QBs start below average
        ypa = (yds + 150 * prior) / (att + 150)
        return dict(att=att, ypa=ypa, debut=att < 50)

    def player_pool(self, team, expected_qb, out_set, must_include=()):
        """Active players with usage shares and efficiencies, plus flags."""
        p, d = self.p, self.d
        P = d.player[(d.player.team == team)]
        P = P[P.position.isin(["WR", "TE", "RB", "FB", "QB"])]
        weeks = sorted(self.tg[self.tg.team == team].week.unique())
        flags_team = []
        starters = self.team_starters(team)
        qbn = norm(expected_qb) if expected_qb else (starters[weeks[-1]] if weeks else "")
        qb_starts = [w for w in weeks if starters.get(w) == qbn]
        qbp = self.qb_profile(qbn) if qbn else dict(att=0, ypa=self.lg_ypa - 0.6, debut=True)
        if not qbn or qbn in out_set:
            flags_team.append("qb_unknown")
        gate = len(qb_starts) >= p["qb_gate_min"]
        if not gate:
            flags_team.append("qb_change")
        if qbp["debut"]:
            flags_team.append("qb_debut")
        sample_weeks = qb_starts if gate else weeks
        # team totals per week
        tt = P.groupby("week")[["targets", "carries"]].sum()
        # snap participation
        S = d.snaps[(d.snaps.team == team)] if len(d.snaps) else pd.DataFrame()
        played = {}
        if len(S):
            for r in S[S.offense_snaps > 0].itertuples():
                played.setdefault(r.nname, {})[r.week] = r.offense_pct
        for r in P.itertuples():
            played.setdefault(r.nname, {}).setdefault(r.week, np.nan)
        last2 = set(weeks[-2:])
        # who is on the team now: most recent team appearance in the season
        latest_team = d.player.sort_values("week").groupby("nname").team.last().to_dict()
        names = sorted(set(P.nname))
        pool, vac_t, vac_c = [], 0.0, 0.0
        team_ypa_sample = []
        prev = d.player_prev
        for nm in names:
            x = P[P.nname == nm].set_index("week")
            pos = x.position.iloc[-1]
            grp = POS_GROUP.get(pos, "WR")
            if grp == "QB" and nm != qbn:
                continue
            wk_played = sorted(w for w in played.get(nm, {}) if w in tt.index)
            use_w = [w for w in wk_played if w in sample_weeks] or wk_played
            if not use_w:
                continue
            w = self._weights(len(use_w))
            pt = np.array([x.targets.get(wk, 0) if wk in x.index else 0 for wk in use_w], float)
            pc = np.array([x.carries.get(wk, 0) if wk in x.index else 0 for wk in use_w], float)
            T = tt.loc[use_w, "targets"].values.astype(float)
            C = tt.loc[use_w, "carries"].values.astype(float)
            ts = float(np.sum(w * pt) / max(1e-9, np.sum(w * T)))
            cs = float(np.sum(w * pc) / max(1e-9, np.sum(w * C)))
            # light shrink toward the player's prior-season share (same team) for small samples
            if len(prev) and len(use_w) < 4:
                pv = prev[(prev.nname == nm) & (prev.team == team)]
                if len(pv) >= 4:
                    pt_tt = prev[prev.team == team].groupby("week")[["targets", "carries"]].sum()
                    pts = pv.targets.sum() / max(1, pt_tt.loc[pv.week].targets.sum())
                    pcs = pv.carries.sum() / max(1, pt_tt.loc[pv.week].carries.sum())
                    m = 1.5
                    ts = (ts * len(use_w) + pts * m) / (len(use_w) + m)
                    cs = (cs * len(use_w) + pcs * m) / (len(use_w) + m)
            on_team = latest_team.get(nm) == team
            active = on_team and nm not in out_set and (bool(set(wk_played) & last2) or nm in must_include)
            if not active:
                vac_t += ts
                vac_c += cs
                continue
            # efficiency with shrinkage; prior season counts at prev_weight
            pvx = prev[(prev.nname == nm)] if len(prev) else prev
            pw = p["prev_weight"]
            tgt = x.targets.sum() + pw * (pvx.targets.sum() if len(pvx) else 0)
            rec = x.receptions.sum() + pw * (pvx.receptions.sum() if len(pvx) else 0)
            ryd = x.receiving_yards.sum() + pw * (pvx.receiving_yards.sum() if len(pvx) else 0)
            car = x.carries.sum() + pw * (pvx.carries.sum() if len(pvx) else 0)
            rud = x.rushing_yards.sum() + pw * (pvx.rushing_yards.sum() if len(pvx) else 0)
            pm = self.pos_mean[grp]
            ypt = (ryd + p["k_ypt"] * pm["ypt"]) / (tgt + p["k_ypt"])
            cr = (rec + p["k_cr"] * pm["cr"]) / (tgt + p["k_cr"])
            ypc = (rud + p["k_ypc"] * pm["ypc"]) / (car + p["k_ypc"])
            # snap trend
            sn = [played.get(nm, {}).get(wk) for wk in wk_played]
            sn = [s for s in sn if s == s and s is not None]
            fl = []
            if len(sn) >= 4:
                recent, base = np.mean(sn[-2:]), np.mean(sn[:-2])
                if recent - base <= -0.15:
                    fl.append("snap_decline")
                elif recent - base >= 0.15:
                    fl.append("snap_rise")
            if len(wk_played) < 4:
                fl.append("small_sample")
            pool.append(dict(name=x.player_display_name.iloc[-1], nname=nm, pos=pos, grp=grp,
                             ts=ts, cs=cs, ypt=ypt, cr=cr, ypc=ypc, games=len(wk_played),
                             sample_games=len(use_w), flags=fl,
                             snap_recent=float(np.mean(sn[-2:])) if sn else None))
            if grp != "QB":
                team_ypa_sample.append((ypt, ts))
        # redistribute vacated shares proportionally (including the 'other' bucket)
        sum_t = sum(r["ts"] for r in pool)
        sum_c = sum(r["cs"] for r in pool)
        other_t = max(0.0, 1.0 - sum_t - vac_t)
        other_c = max(0.0, 1.0 - sum_c - vac_c)
        scale_t = 1.0 / max(1e-9, sum_t + other_t)
        scale_c = 1.0 / max(1e-9, sum_c + other_c)
        for r in pool:
            r["ts"] *= scale_t
            r["cs"] *= scale_c
        if vac_t >= 0.15 or vac_c >= 0.30:
            flags_team.append("teammate_out")
        # QB efficiency factor relative to the QBs the sample was built with
        samp_qbs = {starters.get(w) for w in sample_weeks if starters.get(w)}
        base_ypa = np.mean([self.qb_profile(q)["ypa"] for q in samp_qbs]) if samp_qbs else self.lg_ypa
        qb_factor = float(np.clip(qbp["ypa"] / base_ypa, 0.8, 1.15)) if base_ypa else 1.0
        return dict(pool=pool, other_t=other_t * scale_t, other_c=other_c * scale_c, qb=qbn,
                    qb_starts=len(qb_starts), qb_factor=qb_factor, flags=flags_team,
                    vacated_t=vac_t, vacated_c=vac_c)

    # ---------------------------------------------------------------- simulate
    def simulate_game(self, home, away, spread_home, total, qbs=None, out=None,
                      must_include=None, seed=0):
        """Return {(team, nname): {"name","pos","flags",market: np.array}} and team info.

        spread_home: expected home margin (nflverse convention: positive = home favoured).
        """
        p = self.p
        rng = np.random.default_rng(seed)
        N = p["n_sims"]
        qbs, out, must_include = qbs or {}, out or {}, must_include or {}
        M_home = rng.normal(spread_home if spread_home == spread_home else 0.0, self.margin_sd, N)
        g_pace = rng.normal(0, p["game_pace_sd"], N)
        res, info = {}, {}
        for team, opp, sign in ((home, away, 1.0), (away, home, -1.0)):
            ti = self.team_inputs(team, opp, sign * (spread_home or 0.0), total)
            pp = self.player_pool(team, qbs.get(team), set(out.get(team, set())),
                                  set(must_include.get(team, set())))
            info[team] = dict(ti, **{k: v for k, v in pp.items() if k != "pool"},
                              players=[r["name"] for r in pp["pool"]])
            M = sign * M_home
            plays = ti["plays"] * (1 + g_pace + rng.normal(0, p["pace_sd"], N))
            rate = np.clip(ti["neutral"] + self.slope * M + rng.normal(0, p["rate_sd"], N), 0.30, 0.85)
            att = rng.binomial(np.maximum(plays, 1).astype(int), rate)
            car = np.maximum(plays.astype(int) - att, 0)
            pool = pp["pool"]
            # targets
            ts = np.array([r["ts"] for r in pool] + [pp["other_t"]])
            ts = np.maximum(ts, 1e-4)
            ts = ts / ts.sum()
            tshares = rng.dirichlet(ts * p["kappa_tgt"], N)
            tgt_tot = rng.binomial(att, self.tgt_ratio)
            tgts = rng.multinomial(tgt_tot, tshares)
            cs = np.array([r["cs"] for r in pool] + [pp["other_c"]])
            cs = np.maximum(cs, 1e-4)
            cs = cs / cs.sum()
            cshares = rng.dirichlet(cs * p["kappa_car"], N)
            cars = rng.multinomial(car, cshares)
            team_rec_yds = np.zeros(N)
            dr = self.def_rush.get(opp, 1.0)
            for j, r in enumerate(pool + [None]):
                if r is None:
                    pm = self.pos_mean["WR"]
                    ypt, cr, ypc, grp = pm["ypt"], pm["cr"], 4.2, "WR"
                else:
                    ypt, cr, ypc, grp = r["ypt"], r["cr"], r["ypc"], r["grp"]
                dgrp = grp if grp in ("WR", "TE", "RB") else "WR"
                ypt_adj = ypt * self.def_rec.get((opp, dgrp), 1.0) * pp["qb_factor"]
                ypr = ypt_adj / max(cr, 0.2)
                noise = np.exp(rng.normal(0, p["eff_noise"], N))
                t = tgts[:, j]
                rec = rng.binomial(t, min(max(cr, 0.05), 0.98))
                a = 1.0 / p["rec_cv"] ** 2
                ryd = np.where(rec > 0, rng.gamma(np.maximum(rec, 1) * a, ypr * noise / a), 0.0)
                c = cars[:, j]
                mu = ypc * dr * np.exp(rng.normal(0, p["eff_noise"], N))
                s = p["rush_shift"]
                kk = (mu + s) ** 2 / p["rush_sd"] ** 2
                th = p["rush_sd"] ** 2 / (mu + s)
                rud = np.where(c > 0, rng.gamma(np.maximum(c, 1) * kk, th) - s * c, 0.0)
                team_rec_yds += ryd
                if r is None:
                    continue
                res[(team, r["nname"])] = dict(
                    name=r["name"], pos=r["pos"], team=team, opp=opp,
                    flags=list(r["flags"]) + list(pp["flags"] if r["grp"] in ("WR", "TE", "QB") or
                                                  "qb_unknown" in pp["flags"] else []),
                    receptions=rec, reception_yds=ryd, rush_yds=rud, rush_attempts=c,
                    targets=t, ts=r["ts"], cs=r["cs"], games=r["games"], sample_games=r["sample_games"],
                    def_factor=(self.def_rec.get((opp, dgrp), 1.0), dr))
            qbk = (team, pp["qb"])
            if qbk in res:
                res[qbk]["pass_yds"] = team_rec_yds
                res[qbk]["pass_attempts"] = att
            for r in res.values():
                if r["team"] == team:
                    for m in MARKETS:
                        if m in r and m in self.cal:
                            r[m] = apply_calibration(r[m], self.cal[m])
            info[team]["sim_att_mean"] = float(att.mean())
            info[team]["sim_car_mean"] = float(car.mean())
        return res, info


# Smallest projected median for which the model has been calibrated (backtest.py uses the
# same thresholds). Picks below these are outside the tested range and are blocked.
MIN_ROLE = {"reception_yds": 15, "receptions": 1.5, "rush_yds": 15, "rush_attempts": 4,
            "pass_yds": 120, "pass_attempts": 20}
MARKETS = ["pass_yds", "pass_attempts", "rush_yds", "rush_attempts", "reception_yds", "receptions"]
NFLV_COL = {"pass_yds": "passing_yards", "pass_attempts": "attempts", "rush_yds": "rushing_yards",
            "rush_attempts": "carries", "reception_yds": "receiving_yards", "receptions": "receptions"}
