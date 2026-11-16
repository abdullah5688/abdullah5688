#!/usr/bin/env python3
"""Results ledger: log picks, capture closing prices (CLV), grade results, summarise.

  python3 ledger.py add reports/YYYY-MM-DD-picks.json   # log a run's picks (idempotent)
  python3 ledger.py snapshot [--date YYYY-MM-DD]        # FanDuel price now for open picks
  python3 ledger.py grade                               # settle every finished pick
  python3 ledger.py summary                             # write ledger/summary.md

Files (committed to the repo so history survives between sessions):
  ledger/picks.csv      one row per logged selection (top picks, long shots, avoided props)
  ledger/parlays.csv    one row per parlay
  ledger/snapshots.csv  timestamped FanDuel prices for logged picks (last one before
                        kickoff = closing price)
  ledger/summary.md     record, units, ROI, CLV and calibration, by tier/market/side

Units: every pick is graded as a 1-unit stake at the price logged when it was picked.
CLV ("closing line value"): implied probability of the closing price minus implied
probability of the logged price at the same line. Positive means the market moved toward
the pick after it was made, the most reliable early sign of real edge. If the exact line
disappeared, the move of the main line in the pick's favour is recorded instead.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from engine.data import Data, ESPN_ABBR, espn_json, espn_scoreboard, norm  # noqa: E402
from engine.model import NFLV_COL  # noqa: E402

L = os.path.join(HERE, "ledger")
PICKS, PARLAYS, SNAPS, SUMMARY = (os.path.join(L, f) for f in
                                  ("picks.csv", "parlays.csv", "snapshots.csv", "summary.md"))
PICK_COLS = ["pick_id", "date", "source", "rank", "game", "kickoff_et", "event_id", "player", "team", "market",
             "alt", "side", "line", "selection", "odds", "tier", "evidence_score", "p_model", "p_market",
             "p_blend", "ev", "flags", "close_odds", "close_main_line", "clv_prob", "clv_line_pts",
             "actual", "result", "units", "graded_at"]


def dec(o):
    return 1 + o / 100 if o > 0 else 1 + 100 / -o


def imp(o):
    return 1 / dec(o)


TEXT_COLS = {"result", "graded_at", "flags", "tier", "source", "selection", "market_ref_book", "event_id",
             "team", "kind", "game", "selections", "legs"}


def load(path, cols=None):
    df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=cols or [])
    for c in df.columns:  # pandas 3 is strict about dtypes; keep text columns as object
        if c in TEXT_COLS:
            df[c] = df[c].astype(object)
    return df


def pick_id(date, r):
    return f"{date}|{norm(r['player'])}|{r['market']}|{r['side']}|{float(r['line']):g}"


# ------------------------------------------------------------------ add
def cmd_add(a):
    o = json.load(open(a.picks_json))
    date = o["date"]
    df = load(PICKS, PICK_COLS)
    have = set(df.pick_id) if len(df) else set()
    new = []
    for src, rows in (("top", o.get("top", [])), ("longshot", o.get("longshots", [])),
                      ("avoid", o.get("avoid", []))):
        for i, r in enumerate(rows, 1):
            pid = pick_id(date, r)
            if pid in have:
                continue
            have.add(pid)
            new.append({**{c: r.get(c) for c in PICK_COLS if c in r}, "pick_id": pid, "date": date,
                        "source": src, "rank": i if src == "top" else None})
    if new:
        df = pd.concat([df, pd.DataFrame(new)], ignore_index=True)[PICK_COLS]
        os.makedirs(L, exist_ok=True)
        df.to_csv(PICKS, index=False)
    pl = load(PARLAYS)
    rows = []
    for kind in ("parlay_a", "parlay_b"):
        p = o.get(kind)
        if not p:
            continue
        pid = f"{date}|{kind}"
        if len(pl) and pid in set(pl.parlay_id):
            continue
        rows.append(dict(parlay_id=pid, date=date, kind=kind, game=p.get("game"),
                         legs=" || ".join(f"{l['player']}|{l['market']}|{l['side']}|{l['line']}" for l in p["legs"]),
                         selections=" + ".join(f"{l['player']} {l['selection']}" for l in p["legs"]),
                         model_joint_prob=p["model_joint_prob"], fair_odds=p["fair_odds"],
                         min_acceptable_odds=p["min_acceptable_odds"],
                         product_of_leg_prices=p["product_of_leg_prices"], result=None, graded_at=None))
    if rows:
        pl = pd.concat([pl, pd.DataFrame(rows)], ignore_index=True)
        pl.to_csv(PARLAYS, index=False)
    print(f"logged {len(new)} picks and {len(rows)} parlays from {a.picks_json}")


# ------------------------------------------------------------- snapshot
def cmd_snapshot(a):
    import fetch_odds as F
    df = load(PICKS, PICK_COLS)
    if not len(df):
        return print("ledger empty")
    now = datetime.now(timezone.utc)
    kick = pd.to_datetime(df.kickoff_et).dt.tz_localize("America/New_York").dt.tz_convert("UTC")
    open_ = df[(kick > now) & df.result.isna() & df.event_id.notna()]
    if a.date:
        open_ = open_[open_.date == a.date]
    if not len(open_):
        return print("no open picks before kickoff")
    rows = []
    for ev, x in open_.groupby("event_id"):
        mk = sorted({f"player_{m}" for m in x.market} | {f"player_{m}_alternate" for m in x[x.alt == True].market})
        data, _ = F.event_odds(ev, mk)
        fd = [b for b in data.get("bookmakers", []) if b["key"] == "fanduel"]
        outcomes = []
        for b in fd:
            for m in b["markets"]:
                for o in m["outcomes"]:
                    outcomes.append((m["key"], norm(o.get("description")), o["name"], float(o.get("point", 0)),
                                     int(o["price"])))
        for r in x.itertuples():
            mkey = f"player_{r.market}" + ("_alternate" if r.alt in (True, "True") else "")
            exact = [o for o in outcomes if o[0] == mkey and o[1] == norm(r.player) and o[2] == r.side
                     and o[3] == float(r.line)]
            main = [o for o in outcomes if o[0] == f"player_{r.market}" and o[1] == norm(r.player) and o[2] == r.side]
            rows.append(dict(ts=now.isoformat(timespec="seconds"), pick_id=r.pick_id,
                             odds=exact[0][4] if exact else None,
                             main_line=main[0][3] if main else None, main_odds=main[0][4] if main else None))
    s = load(SNAPS)
    s = pd.concat([s, pd.DataFrame(rows)], ignore_index=True)
    s.to_csv(SNAPS, index=False)
    print(f"snapshotted {len(rows)} open picks; API credits left {F.remaining['value']}")


# ---------------------------------------------------------------- grade
def espn_stat(date, team, player, market):
    """Fallback: read a player's stat from the ESPN box score. Returns (value, played)."""
    cols = {"receptions": ("receiving", "receptions"), "reception_yds": ("receiving", "receivingYards"),
            "rush_yds": ("rushing", "rushingYards"), "rush_attempts": ("rushing", "rushingAttempts"),
            "pass_yds": ("passing", "passingYards"), "pass_attempts": ("passing", "completions/passingAttempts")}
    sb = espn_scoreboard(date.replace("-", ""))
    for e in sb.get("events", []):
        comp = e["competitions"][0]
        abbrs = [ESPN_ABBR.get(c["team"]["abbreviation"], c["team"]["abbreviation"]) for c in comp["competitors"]]
        if team not in abbrs:
            continue
        if not comp["status"]["type"].get("completed"):
            return None, None
        d = espn_json(f"summary?event={e['id']}")
        seen = False
        for t in d["boxscore"].get("players", []):
            for cat in t["statistics"]:
                for at in cat["athletes"]:
                    if norm(at["athlete"]["displayName"]) != norm(player):
                        continue
                    seen = True
                    cat_name, key = cols[market]
                    if cat["name"] != cat_name:
                        continue
                    if "/" in key:
                        v = dict(zip(cat["keys"], at["stats"])).get(key, "0/0").split("/")[1]
                    else:
                        v = dict(zip(cat["keys"], at["stats"])).get(key, 0)
                    return float(v), True
        return (0.0, True) if seen else (None, False)
    return None, None


def settle(side, line, actual):
    if actual == line:
        return "push"
    return "win" if (actual > line) == (side == "Over") else "loss"


def cmd_grade(a):
    df = load(PICKS, PICK_COLS)
    if not len(df):
        return print("ledger empty")
    now = datetime.now(timezone.utc)
    todo = df[df.result.isna()]
    seasons = {}
    snaps = load(SNAPS)
    for i, r in todo.iterrows():
        k = pd.Timestamp(r.kickoff_et).tz_localize("America/New_York")
        if k.tz_convert("UTC") + pd.Timedelta(hours=4) > now:
            continue  # not finished yet
        season = k.year if k.month >= 8 else k.year - 1
        if season not in seasons:
            seasons[season] = Data(season, max_age_h=1)
        D = seasons[season]
        g = D.games[(D.games.season == season) & (D.games.gameday == k.strftime("%Y-%m-%d")) &
                    ((D.games.home_team == r.team) | (D.games.away_team == r.team))]
        val, played = None, None
        if len(g):
            wk = int(g.iloc[0].week)
            x = D.player[(D.player.week == wk) & (D.player.nname == norm(r.player))]
            if len(x):
                val, played = float(x.iloc[0][NFLV_COL[r.market]]), True
        if val is None:
            val, played = espn_stat(k.strftime("%Y-%m-%d"), r.team, r.player, r.market)
        if played is None:
            continue  # data not available yet; try again later
        if played is False:
            res, units = "void", 0.0  # did not play: FanDuel voids player props
        else:
            res = settle(r.side, float(r.line), val)
            units = {"win": dec(r.odds) - 1, "loss": -1.0, "push": 0.0}[res]
        df.loc[i, ["actual", "result", "units", "graded_at"]] = [val, res, round(units, 4), now.date().isoformat()]
        # closing line value from the last snapshot before kickoff
        if len(snaps):
            s = snaps[(snaps.pick_id == r.pick_id) &
                      (pd.to_datetime(snaps.ts, utc=True) <= k.tz_convert("UTC"))]
            if len(s):
                last = s.iloc[-1]
                if pd.notna(last.odds):
                    df.loc[i, ["close_odds", "clv_prob"]] = [last.odds, round(imp(last.odds) - imp(r.odds), 4)]
                if pd.notna(last.main_line):
                    mv = float(last.main_line) - float(r.line)
                    df.loc[i, ["close_main_line", "clv_line_pts"]] = [last.main_line,
                                                                      mv if r.side == "Over" else -mv]
    df.to_csv(PICKS, index=False)
    # parlays: all legs must win (a void leg drops out, as at FanDuel)
    pl = load(PARLAYS)
    for i, p in pl[pl.result.isna()].iterrows() if len(pl) else []:
        res = []
        for leg in p.legs.split(" || "):
            pl_, mk, sd, ln = leg.split("|")
            m = df[(df.date == p.date) & (df.player == pl_) & (df.market == mk) & (df.side == sd) &
                   (df.line.astype(float) == float(ln))]
            res.append(m.iloc[0].result if len(m) and pd.notna(m.iloc[0].result) else None)
        if "loss" in res:
            pl.loc[i, ["result", "graded_at"]] = ["loss", now.date().isoformat()]
            continue
        if None in res:
            continue
        live = [x for x in res if x not in ("void", "push")]
        out = "void" if not live else ("win" if all(x == "win" for x in live) else "loss")
        pl.loc[i, ["result", "graded_at"]] = [out, now.date().isoformat()]
    if len(pl):
        pl.to_csv(PARLAYS, index=False)
    print(f"graded {int(df.graded_at.eq(now.date().isoformat()).sum())} picks")
    cmd_summary(a)


# -------------------------------------------------------------- summary
def block(x, title):
    x = x[x.result.isin(["win", "loss", "push"])]
    if not len(x):
        return f"| {title} | 0 | — | — | — | — | — |"
    w, l_, p = (x.result == "win").sum(), (x.result == "loss").sum(), (x.result == "push").sum()
    u = x.units.astype(float).sum()
    clv = x.clv_prob.dropna().astype(float)
    exp = x.p_blend.dropna().astype(float)
    return (f"| {title} | {len(x)} | {w}-{l_}" + (f"-{p}" if p else "") + f" | {u:+.2f} | {u / len(x):+.1%} | "
            + (f"{clv.mean():+.1%} ({len(clv)})" if len(clv) else "—") + " | "
            + (f"{exp.mean():.0%} exp / {w / max(1, w + l_):.0%} act" if len(exp) else "—") + " |")


def cmd_summary(a):
    df = load(PICKS, PICK_COLS)
    if not len(df):
        return
    g = df[df.result.notna()]
    H = "| Slice | Graded | W-L | Units | ROI | Avg CLV (n) | Win rate: expected vs actual |\n|---|---|---|---|---|---|---|"
    out = [f"# Results ledger — updated {datetime.now().date()}", "",
           "1 unit per pick at the logged FanDuel price. CLV = closing implied probability minus logged "
           "implied probability (positive = beat the close). Small samples are noise: judge the model on "
           "CLV and calibration first, profit last.", "", "## Overall", "", H,
           block(g[g.source == "top"], "Top picks"), block(g[g.source == "longshot"], "Long shots"),
           block(g[g.source == "avoid"], "Avoided (not bet)"), "", "## Top picks by tier", "", H]
    t = g[g.source == "top"]
    for k, x in t.groupby(t.tier.fillna("v1 (pre-model)")):
        out.append(block(x, k))
    out += ["", "## By market", "", H] + [block(x, k) for k, x in t.groupby("market")]
    out += ["", "## By side", "", H] + [block(x, k) for k, x in t.groupby("side")]
    t2 = t[t.p_blend.notna()].copy()
    if len(t2):
        t2["bucket"] = pd.cut(t2.p_blend.astype(float), [0, .5, .55, .6, .65, .7, 1.0])
        out += ["", "## Calibration (blended probability bucket)", "", H] + \
               [block(x, str(k)) for k, x in t2.groupby("bucket", observed=True)]
    d = t[t.p_model.notna() & t.p_market.notna() & t.result.isin(["win", "loss"])]
    if len(d):
        y = (d.result == "win").astype(float)
        bs = {k: float(np.mean((d[k].astype(float) - y) ** 2)) for k in ("p_model", "p_market", "p_blend")}
        out += ["", "## Who has been more accurate? (Brier score on graded top picks, lower is better)", "",
                f"Model {bs['p_model']:.4f} · Market (no-vig) {bs['p_market']:.4f} · Blend {bs['p_blend']:.4f} "
                f"(n={len(d)}). Raise --model-weight only if the model beats the market here over 150+ picks "
                "and average CLV is positive."]
    out += ["", "## By week", "", H] + [block(x, k) for k, x in t.groupby("date")]
    pl = load(PARLAYS)
    if len(pl):
        out += ["", "## Parlays", "", "| Date | Type | Legs | Model prob | Fair odds | Result |", "|---|---|---|---|---|---|"]
        for p in pl.itertuples():
            out.append(f"| {p.date} | {p.kind} | {p.selections} | {p.model_joint_prob if pd.notna(p.model_joint_prob) else '—'} | "
                       f"{p.fair_odds if pd.notna(p.fair_odds) else '—'} | {p.result if pd.notna(p.result) else 'open'} |")
    open(SUMMARY, "w").write("\n".join(out) + "\n")
    print("\n".join(out[:12]))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("add")
    s.add_argument("picks_json")
    s = sp.add_parser("snapshot")
    s.add_argument("--date")
    sp.add_parser("grade")
    sp.add_parser("summary")
    a = ap.parse_args()
    {"add": cmd_add, "snapshot": cmd_snapshot, "grade": cmd_grade, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
