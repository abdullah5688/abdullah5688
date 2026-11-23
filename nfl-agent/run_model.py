#!/usr/bin/env python3
"""Edge engine: projections x FanDuel prices -> ranked props + parlays.

Usage:
  python3 run_model.py --odds reports/odds-YYYYMMDD-HHMM.csv [--context context.json]
                       [--out reports/] [--model-weight 0.5] [--sims 20000]

Outputs (in --out):
  YYYY-MM-DD-candidates.csv  every FanDuel line/rung, both sides, with model / market /
                             blended probability, EV, flags, sample hit counts
  YYYY-MM-DD-picks.json      top 10, Parlays C1, C2... (last-5 streak, 5 legs each), best over vs best under per
                             player, popular props to avoid, game inputs. grade.py reads this.
  YYYY-MM-DD-model-tables.md markdown tables to paste into the report.

context.json (written by the agent from news before running; every key is optional):
  {"qb": {"ARI": "Carson Beck"},             # confirmed starters (nflverse abbreviations)
   "out": {"LA": ["Puka Nacua"]},            # extra players ruled out (ESPN list is automatic)
   "questionable": {"SF": ["Trent Williams"]},
   "exclude": {"Brock Bowers": "reason",     # never pick this player today
               "Justin Jefferson|receptions": "reason"},  # or just one of his markets
   "notes": {"Jaylen Warren": "text shown in the output"}}
"""
import argparse
import itertools
import json
import math
import os
import sys
import zlib
from datetime import datetime

import numpy as np
import pandas as pd

from engine.data import TEAMS, Data, espn_game_context, espn_scoreboard, norm, ESPN_ABBR
from engine.model import MARKETS, MIN_ROLE, NFLV_COL, Model

PRICE_CAP = -350          # user rule: nothing shorter than -350
MIN_TOP_PROB = 0.45       # balanced style: top-10 / parlay legs need >= 45% blended chance
BET_EV, LEAN_EV = 0.04, 0.015
BLOCKING = {"qb_debut", "qb_unknown", "questionable", "excluded", "small_sample", "no_projection",
            "price_cap", "outside_calibrated_range", "line_gap"}
LINE_GAP = 0.30           # model median this far (fraction) from the main line -> Research Only
DEFAULT_HOLD = 0.07       # assumed bookmaker margin when no two-sided main line exists
SOFT_PENALTY = {"qb_change": 25, "teammate_out": 10, "snap_decline": 20, "no_market_ref": 25,
                "role_sample_short": 15}
LABEL = {"pass_yds": "Pass Yds", "pass_attempts": "Pass Att", "rush_yds": "Rush Yds",
         "rush_attempts": "Rush Att", "reception_yds": "Rec Yds", "receptions": "Receptions"}


def dec(o):
    return 1 + o / 100 if o > 0 else 1 + 100 / -o


def american(d):
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def fmt(o):
    return f"+{o}" if o > 0 else str(o)


def selection_text(r):
    if r["alt"] and r["side"] == "Over" and float(r["line"]) % 1 == 0.5:
        return f"{int(float(r['line']) + 0.5)}+ {LABEL[r['market']]}"
    return f"{r['side']} {r['line']:g} {LABEL[r['market']]}"


def load_context(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        c = json.load(f)
    for k in ("out", "questionable"):
        if isinstance(c.get(k), list):  # allow a flat list of names
            c[k] = {"*": c[k]}
    return c


def espn_events(dates):
    ev = {}
    for d in dates:
        try:
            sb = espn_scoreboard(d)
        except Exception:
            continue
        for e in sb.get("events", []):
            comp = e["competitions"][0]
            teams = {}
            for c in comp["competitors"]:
                ab = ESPN_ABBR.get(c["team"]["abbreviation"], c["team"]["abbreviation"])
                teams[c["homeAway"]] = ab
            ev[(teams.get("home"), teams.get("away"))] = e["id"]
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", required=True)
    ap.add_argument("--context")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--model-weight", type=float, default=0.5,
                    help="weight on the model vs the FanDuel no-vig market (0..1)")
    ap.add_argument("--sims", type=int, default=20000)
    a = ap.parse_args()
    ctx = load_context(a.context)
    odds = pd.read_csv(a.odds)
    if not len(odds):
        sys.exit("odds file is empty - nothing to evaluate")
    odds["mkt"] = odds.market.str.replace("player_", "", regex=False).str.replace("_alternate", "", regex=False)
    odds["alt"] = odds.market.str.endswith("_alternate")
    odds["nname"] = odds.player.map(norm)
    kick = pd.to_datetime(odds.kickoff_et)
    season = int(kick.min().year if kick.min().month >= 8 else kick.min().year - 1)
    run_date = kick.min().strftime("%Y-%m-%d")
    D = Data(season)
    M = Model(D, dict(n_sims=a.sims))
    G = D.games[(D.games.season == season)]
    esp = espn_events(sorted({k.strftime("%Y%m%d") for k in kick}))

    cand, sims_store, games_info = [], {}, {}
    for (game, kickoff, event_id), od in odds.groupby(["game", "kickoff_et", "event_id"]):
        away_full, home_full = [s.strip() for s in game.split(" @ ")]
        home, away = TEAMS[home_full], TEAMS[away_full]
        gr = G[(G.home_team == home) & (G.away_team == away) & G.result.isna()]
        gr = gr.iloc[0] if len(gr) else None
        spread = float(gr.spread_line) if gr is not None and gr.spread_line == gr.spread_line else None
        total = float(gr.total_line) if gr is not None and gr.total_line == gr.total_line else None
        out, quest = {home: set(), away: set()}, {home: set(), away: set()}
        espn_ok = False
        eid = esp.get((home, away))
        if eid:
            try:
                ec = espn_game_context(eid)
                espn_ok = True
                for t in (home, away):
                    out[t] |= ec["out"].get(t, set())
                    quest[t] |= ec["questionable"].get(t, set())
                if spread is None and ec.get("spread") is not None:
                    # ESPN spread is quoted for the home side (negative = home favoured)
                    spread = -float(ec["spread"])
                if total is None and ec.get("total"):
                    total = float(ec["total"])
            except Exception:
                pass
        for t in (home, away):
            for nm in ctx.get("out", {}).get(t, []) + ctx.get("out", {}).get("*", []):
                out[t].add(norm(nm))
            for nm in ctx.get("questionable", {}).get(t, []) + ctx.get("questionable", {}).get("*", []):
                quest[t].add(norm(nm))
        qbs = {}
        for t, col in ((home, "home_qb_name"), (away, "away_qb_name")):
            if t in ctx.get("qb", {}):
                qbs[t] = ctx["qb"][t]
            elif gr is not None and isinstance(gr[col], str) and norm(gr[col]) not in out[t]:
                qbs[t] = gr[col]
        # players with props are presumed active unless listed out
        must = {home: set(), away: set()}
        roster_now = D.player.sort_values("week").groupby("nname").team.last().to_dict()
        for nm in set(od.nname):
            t = roster_now.get(nm)
            if t in must:
                must[t].add(nm)
        res, info = M.simulate_game(home, away, spread if spread is not None else 0.0, total,
                                    qbs=qbs, out=out, must_include=must,
                                    seed=zlib.crc32(str(event_id).encode()))  # deterministic
        games_info[game] = dict(kickoff=kickoff, home=home, away=away, spread_home=spread, total=total,
                                espn_injuries=espn_ok, qbs={t: info[t]["qb"] for t in info},
                                team_flags={t: info[t]["flags"] for t in info},
                                proj_pass_att={t: round(info[t]["sim_att_mean"], 1) for t in info},
                                proj_carries={t: round(info[t]["sim_car_mean"], 1) for t in info},
                                out=sorted(out[home] | out[away]))
        idx = {nm: (t, r) for (t, nm), r in res.items()}
        # bookmaker margin (hold) per player-market from the two-sided main line;
        # FanDuel first, then DK, then BetMGM
        mains = {}
        for book in ("fanduel", "draftkings", "betmgm"):
            mb = od[(od.book == book) & (~od.alt)]
            for (nm, mk), x in mb.groupby(["nname", "mkt"]):
                sides = {r.side: r for r in x.itertuples()}
                if "Over" in sides and "Under" in sides and (nm, mk) not in mains \
                        and sides["Over"].line == sides["Under"].line:
                    po, pu = 1 / dec(sides["Over"].american_odds), 1 / dec(sides["Under"].american_odds)
                    mains[(nm, mk)] = (float(sides["Over"].line), po + pu - 1, book)
        fd = od[od.book == "fanduel"]
        for r in fd.itertuples():
            base = dict(game=game, kickoff_et=kickoff, event_id=event_id, player=r.player, nname=r.nname,
                        market=r.mkt, alt=bool(r.alt), side=r.side, line=float(r.line),
                        odds=int(r.american_odds), book_last_update=r.book_last_update,
                        betslip_link=getattr(r, "betslip_link", None))
            flags = []
            hit = idx.get(r.nname)
            if hit is None or r.mkt not in hit[1]:
                flags.append("no_projection")
                cand.append(dict(base, team=None, flags=",".join(flags), tier="Research Only"))
                continue
            team, pr = hit
            sims = pr[r.mkt]
            L = float(r.line)
            p_over, p_eq = float(np.mean(sims > L)), float(np.mean(sims == L))
            p_model = p_over if r.side == "Over" else float(np.mean(sims < L))
            # market-implied fair probability of THIS selection: its own price with the
            # bookmaker margin removed (margin measured on the two-sided main line)
            ref = mains.get((r.nname, r.mkt))
            if ref:
                _, hold, rbook = ref
            else:
                hold, rbook = DEFAULT_HOLD, None
                flags.append("no_market_ref")
            p_mkt = min(0.99, (1 / dec(r.american_odds)) / (1 + max(hold, 0.0)))
            w = a.model_weight
            p = w * p_model + (1 - w) * p_mkt
            d = dec(r.american_odds)
            if L % 1 == 0:  # integer line: a push returns the stake
                ev = p * (d - 1) - (1 - p - p_eq)
            else:
                ev = p * d - 1
            flags += [f for f in pr["flags"] if f not in flags]
            if r.nname in quest.get(team, set()):
                flags.append("questionable")
            # exclude a whole player ("Name") or one market ("Name|receptions")
            if r.player in ctx.get("exclude", {}) or f"{r.player}|{r.mkt}" in ctx.get("exclude", {}):
                flags.append("excluded")
            if r.american_odds < PRICE_CAP:
                flags.append("price_cap")
            if float(np.median(sims)) < MIN_ROLE[r.mkt]:
                flags.append("outside_calibrated_range")
            # sanity rule (RUNBOOK step 4.4), automated: a projection far from the market's main
            # line usually means a role change the data hasn't caught yet
            if ref and ref[0] > 0 and abs(float(np.median(sims)) - ref[0]) / ref[0] > LINE_GAP:
                flags.append("line_gap")
            if pr["sample_games"] < 4 and "small_sample" not in flags:
                flags.append("role_sample_short")
            # passing-game flags only matter for pass-catchers / QB markets
            if r.mkt in ("rush_yds", "rush_attempts") and pr["pos"] == "RB":
                flags = [f for f in flags if f not in ("qb_change", "qb_debut")]
            # historical results at this exact line (all games this season)
            # same name AND an offensive skill position (a CLE linebacker shares a WR's name)
            hist = D.player[(D.player.nname == r.nname) &
                            D.player.position.isin(["QB", "RB", "WR", "TE", "FB"])].sort_values("week")
            vals = hist[NFLV_COL[r.mkt]].astype(float).tolist()
            won = [v > L if r.side == "Over" else v < L for v in vals]
            push = [v == L for v in vals]
            be = 1 / d
            tier = "Bet" if ev >= BET_EV and p - be >= 0.02 else "Lean" if ev >= LEAN_EV else "Pass"
            if set(flags) & BLOCKING:
                tier = "Research Only" if tier in ("Bet", "Lean") else tier
            # evidence score (heuristic, NOT a probability) - engine weights 20/25/20/25/10
            n = len(vals)
            hr = (sum(won) + 2 * be) / (n - sum(push) + 2) if n else be
            consistency = float(np.clip(50 + 250 * (hr - be), 0, 100))
            opp_key = "targets" if r.mkt in ("receptions", "reception_yds") else "carries" \
                if r.mkt in ("rush_yds", "rush_attempts") else "attempts"
            opp_vals = hist[opp_key].astype(float).values[-6:]
            cv = float(np.std(opp_vals) / np.mean(opp_vals)) if len(opp_vals) >= 3 and np.mean(opp_vals) > 0 else 1.0
            workload = float(np.clip(100 * (1 - cv), 0, 100)) - (20 if "snap_decline" in flags else 0) \
                + (5 if "snap_rise" in flags else 0)
            dfac = pr["def_factor"][1] if r.mkt in ("rush_yds", "rush_attempts") else pr["def_factor"][0]
            matchup = float(np.clip(50 + 250 * ((dfac - 1) if r.side == "Over" else (1 - dfac)), 0, 100))
            value = float(np.clip(50 + 600 * ev, 0, 100))
            quality = float(np.clip(100 - sum(SOFT_PENALTY.get(f, 0) for f in flags)
                                    - (60 if set(flags) & BLOCKING else 0), 0, 100))
            score = 0.20 * consistency + 0.25 * np.clip(workload, 0, 100) + 0.20 * matchup + 0.25 * value + 0.10 * quality
            row = dict(base, team=team, opp=pr["opp"], pos=pr["pos"], proj_median=round(float(np.median(sims)), 1),
                       proj_mean=round(float(np.mean(sims)), 1), p_model=round(p_model, 4),
                       p_market=None if p_mkt is None else round(p_mkt, 4), market_ref_book=rbook,
                       p_blend=round(p, 4), breakeven=round(be, 4), edge=round(p - be, 4), ev=round(ev, 4),
                       tier=tier, flags=",".join(dict.fromkeys(flags)), evidence_score=round(float(score), 1),
                       season_hits=f"{sum(won)}/{n - sum(push)}" + (f" ({sum(push)} push)" if sum(push) else ""),
                       last5=f"{sum(won[-5:])}/{len(won[-5:])}", last10=f"{sum(won[-10:])}/{len(won[-10:])}",
                       last5_values=" ".join(f"{v:g}" for v in vals[-5:]),
                       # game-by-game history this season (oldest -> newest) for the phone page
                       history=[dict(wk=int(h.week), opp=str(h.opponent_team), v=float(getattr(h, NFLV_COL[r.mkt])))
                                for h in hist.itertuples()],
                       score_parts=dict(consistency=round(consistency), workload=round(float(np.clip(workload, 0, 100))),
                                        matchup=round(matchup), value=round(value), quality=round(quality)),
                       def_factor=round(float(dfac), 3), target_share=round(pr["ts"], 3), carry_share=round(pr["cs"], 3))
            row["selection"] = selection_text(row)
            cand.append(row)
            key = (game, r.nname, r.mkt, r.side, L)
            sims_store[key] = (sims > L) if r.side == "Over" else (sims < L)

    C = pd.DataFrame(cand)
    os.makedirs(a.out, exist_ok=True)
    C.drop(columns=["score_parts", "history"], errors="ignore").to_csv(os.path.join(a.out, f"{run_date}-candidates.csv"), index=False)
    ok = C[C.tier.isin(["Bet", "Lean"])].copy()
    ok["tier_rank"] = ok.tier.map({"Bet": 0, "Lean": 1})

    # best rung per player-market-side, then best per player
    longshots = ok[ok.p_blend < MIN_TOP_PROB].sort_values("ev", ascending=False) \
        .groupby("nname").head(1).head(5)
    best = ok[ok.p_blend >= MIN_TOP_PROB].sort_values("ev", ascending=False) \
        .groupby(["nname", "market", "side"]).head(1)
    per_player = best.sort_values(["tier_rank", "evidence_score", "ev"], ascending=[True, False, False]) \
        .groupby("nname").head(1)
    top, per_game = [], {}
    for r in per_player.to_dict("records"):
        if per_game.get(r["game"], 0) >= 3:
            continue
        top.append(r)
        per_game[r["game"]] = per_game.get(r["game"], 0) + 1
        if len(top) == 10:
            break

    # best over vs best under for every player-market (comparison table)
    allv = C[C.tier != "Research Only"].dropna(subset=["ev"]) if "ev" in C else C.iloc[0:0]
    ou = []
    for (nm, mk), x in allv[~allv["flags"].fillna("").str.contains("price_cap")].groupby(["nname", "market"]):
        bo = x[x.side == "Over"].sort_values("ev").tail(1)
        bu = x[x.side == "Under"].sort_values("ev").tail(1)
        ou.append(dict(player=x.player.iloc[0], market=mk,
                       best_over=None if not len(bo) else f"{bo.selection.iloc[0]} {fmt(int(bo.odds.iloc[0]))} EV {bo.ev.iloc[0]:+.1%}",
                       best_under=None if not len(bu) else f"{bu.selection.iloc[0]} {fmt(int(bu.odds.iloc[0]))} EV {bu.ev.iloc[0]:+.1%}"))

    # Parlay C ("streak" parlay, user rule) - the ONLY parlay (Parlays A and B were retired
    # 2026-11-22 at the user's request). Independent of the top 10.
    # A leg qualifies when the player cleared that exact threshold in ALL of his last 5 games
    # (over: every game above the line; under: every game below it). For each player-market-side
    # the hardest such rung is used (best price), within the -350 cap. Model checks still apply:
    # no status/role blocks and a blended probability of at least 50%. One leg per game, up to 5.
    # also skipped: lines the model can't vouch for (outside_calibrated_range, line_gap) and a
    # streak running against a role change (under while snaps rise / over while snaps fall)
    STREAK_BLOCK = {"qb_debut", "qb_unknown", "questionable", "excluded", "small_sample",
                    "no_projection", "price_cap", "outside_calibrated_range", "line_gap"}
    sc = C[(C.last5 == "5/5") & C.p_blend.notna()].copy() if "last5" in C else C.iloc[0:0]
    if len(sc):
        sc = sc[sc["flags"].fillna("").map(lambda f: not (set(f.split(",")) & STREAK_BLOCK))]
        fl = sc["flags"].fillna("")
        sc = sc[~(((sc.side == "Under") & fl.str.contains("snap_rise")) |
                  ((sc.side == "Over") & fl.str.contains("snap_decline")))]
        sc = sc[(sc.p_blend >= 0.5) & (sc.odds >= PRICE_CAP)]

        def rate(t):
            a, b = str(t).split(" ")[0].split("/")
            return int(a) / int(b) if int(b) else 0.0
        sc["l10_rate"] = sc.last10.map(rate)
        sc["season_rate"] = sc.season_hits.map(rate)
        # hardest rung he still cleared 5/5 = the best-priced one
        sc = sc.sort_values("odds", ascending=False).groupby(["nname", "market", "side"]).head(1)
        sc = sc.sort_values(["l10_rate", "season_rate", "p_blend", "odds"], ascending=False) \
            .groupby("nname").head(1)
    streak = [clean(r) for r in sc.to_dict("records")] if len(sc) else []
    # Split ALL qualifying legs into as many parlays as needed (user rule, 2026-11-22): up to 5
    # legs each, never two legs from the same game in one parlay, each player used once. Legs go,
    # in rank order, into the first parlay that has room and no leg from that game; a new parlay
    # opens when none fits. A group left with a single leg is reported as a leftover, not a parlay.
    groups = []
    for r in sc.to_dict("records") if len(sc) else []:
        for g in groups:
            if len(g) < 5 and r["game"] not in {x["game"] for x in g}:
                g.append(r)
                break
        else:
            groups.append([r])
    parlays_c, streak_leftover = [], []
    for g in groups:
        if len(g) < 2:
            streak_leftover += [clean(x) for x in g]
            continue
        pc = parlay_summary(g, joint=float(np.prod([r["p_blend"] for r in g])))
        pc["name"] = f"Parlay C{len(parlays_c) + 1}"
        pc["rule"] = "every leg hit in each of the player's last 5 games"
        parlays_c.append(pc)

    # popular props to avoid: highest-volume players whose main line is clearly -EV both ways
    avoid = []
    mains_fd = C[(~C.alt) & C.ev.notna()] if "ev" in C else C.iloc[0:0]
    for (nm, mk), x in mains_fd.groupby(["nname", "market"]):
        if x.ev.max() < -0.03 and x.proj_median.max() >= {"pass_yds": 200, "reception_yds": 55,
                                                           "rush_yds": 55, "receptions": 4.5}.get(mk, 1e9):
            o = x[x.side == "Over"]
            if len(o):
                o = o.iloc[0]
                avoid.append(dict(clean(o.to_dict()), why=f"model median {o.proj_median:g} vs line {o.line:g}"))
    avoid = sorted(avoid, key=lambda r: r["ev"])[:6]

    out = dict(date=run_date, generated_at=datetime.now().isoformat(timespec="seconds"), odds_file=a.odds,
               model_weight=a.model_weight, games=games_info, top=[clean(r) for r in top],
               parlays_c=parlays_c, streak=streak, streak_leftover=streak_leftover, over_under=ou, avoid=avoid,
               longshots=[clean(r) for r in longshots.to_dict("records")],
               counts=dict(candidates=len(C), bets=int((C.tier == "Bet").sum()), leans=int((C.tier == "Lean").sum()),
                           research_only=int((C.tier == "Research Only").sum())))
    with open(os.path.join(a.out, f"{run_date}-picks.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    md = tables(out)
    with open(os.path.join(a.out, f"{run_date}-model-tables.md"), "w") as f:
        f.write(md)
    print(md)


def clean(r):
    keep = ["game", "kickoff_et", "event_id", "player", "team", "opp", "pos", "market", "alt", "side", "line",
            "selection", "odds", "book_last_update", "betslip_link", "proj_median", "proj_mean", "p_model",
            "p_market", "market_ref_book", "p_blend", "breakeven", "edge", "ev", "tier", "flags",
            "evidence_score", "score_parts", "season_hits", "last5", "last10", "last5_values", "def_factor",
            "target_share", "carry_share", "history"]
    return {k: (None if isinstance(r.get(k), float) and math.isnan(r.get(k)) else r.get(k)) for k in keep}


def parlay_summary(legs, joint):
    if not legs:
        return None
    prod_dec = float(np.prod([dec(r["odds"]) for r in legs]))
    links = [r.get("betslip_link") for r in legs]
    url = None
    if all(isinstance(l, str) and "marketId=" in l for l in links):
        from urllib.parse import parse_qs, urlparse
        parts = []
        for i, l in enumerate(links):
            q = parse_qs(urlparse(l).query)
            parts.append(f"marketId[{i}]={q['marketId'][0]}&selectionId[{i}]={q['selectionId'][0]}")
        url = "https://sportsbook.fanduel.com/addToBetslip?" + "&".join(parts)
    fair = 1 / joint if joint > 0 else None
    return dict(legs=[clean(r) for r in legs], n_legs=len(legs), model_joint_prob=round(joint, 4),
                fair_odds=american(fair) if fair else None,
                min_acceptable_odds=american(fair * 1.05) if fair else None,
                product_of_leg_prices=american(prod_dec), ev_if_priced_as_product=round(joint * prod_dec - 1, 4),
                betslip_url=url)


def tables(o):
    L = [f"### Model output — {o['date']} (generated {o['generated_at']})", "",
         f"Candidates evaluated: {o['counts']['candidates']} FanDuel lines/rungs · Bet {o['counts']['bets']} · "
         f"Lean {o['counts']['leans']} · Research Only {o['counts']['research_only']}. "
         f"Blend: {o['model_weight']:.0%} model / {1 - o['model_weight']:.0%} FanDuel no-vig market.", "",
         "| # | Player | Game | Selection | FD odds | Proj (median) | Model p | Market p | Blend p | Break-even | EV | Season | L5 | L10 | Evidence | Tier | Flags |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(o["top"], 1):
        mp = "—" if r["p_market"] is None else f"{r['p_market']:.0%}"
        L.append(f"| {i} | {r['player']} | {r['game']} | {r['selection']} | {fmt(r['odds'])} | {r['proj_median']:g} | "
                 f"{r['p_model']:.0%} | {mp} | {r['p_blend']:.0%} | {r['breakeven']:.0%} | {r['ev']:+.1%} | "
                 f"{r['season_hits']} | {r['last5']} | {r['last10']} | {r['evidence_score']:.0f} | {r['tier']} | {r['flags'] or '—'} |")
    pcs = o.get("parlays_c") or []
    if not pcs:
        L += ["", "**Parlay C (last-5 streak)**", "No Parlay C today: fewer than 2 streak legs passed the checks."]
    for p in pcs:
        name = f"{p['name']} (last-5 streak, multi-game)"
        L += ["", f"**{name}**"]
        for r in p["legs"]:
            L.append(f"- {r['player']} {r['selection']} ({fmt(r['odds'])}) · blend p {r['p_blend']:.0%}"
                     + f" · last 5: {r['last5_values']} · L10 {r['last10']}")
        L.append(f"- Model joint probability **{p['model_joint_prob']:.1%}** → fair odds **{fmt(p['fair_odds'])}**; "
                 f"only bet at **{fmt(p['min_acceptable_odds'])} or better**. Product of leg prices "
                 f"{fmt(p['product_of_leg_prices'])} (not a FanDuel quote)."
                 + (f" Correlation factor {p['correlation_factor']} (1.0 = independent)." if p.get("correlation_factor") else ""))
        if p.get("betslip_url"):
            L.append(f"- [Open in FanDuel]({p['betslip_url']})")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
