#!/usr/bin/env python3
"""Write the quick-read summary (RUNBOOK step 8) from the run's files, so every number is copied
straight from picks.json, context.json and notes.json, never retyped.

Usage: python3 make_summary.py 2026-11-26 [--out reports/]
Writes reports/DATE-nfl-props-summary.md
"""
import argparse
import json
import os
from datetime import datetime


def am(o):
    o = int(o)
    return f"+{o}" if o > 0 else str(o)


def short(g):
    return " @ ".join(x.split()[-1] for x in g.split(" @ "))


def when(k):
    t = datetime.strptime(k, "%Y-%m-%d %H:%M")
    return t.strftime("%a %-I:%M %p ET")


def recheck(k):
    t = datetime.strptime(k, "%Y-%m-%d %H:%M")
    m = t.hour * 60 + t.minute - 90
    return f"{t.strftime('%a')} {(m // 60 - 1) % 12 + 1}:{m % 60:02d} {'AM' if m < 720 else 'PM'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--out", default="reports/")
    a = ap.parse_args()
    D, R = a.date, a.out
    b = json.load(open(os.path.join(R, f"{D}-picks.json")))
    ctx = json.load(open(os.path.join(R, f"{D}-context.json")))
    try:
        notes = json.load(open(os.path.join(R, f"{D}-notes.json")))
    except OSError:
        notes = {}
    kicks = sorted({g["kickoff"] for g in b["games"].values()})
    odds_t = os.path.basename(b["odds_file"]).replace("odds-", "")[:13]
    pulled = datetime.strptime(odds_t, "%Y%m%d-%H%M").strftime("%a %-I:%M %p ET")
    games = " · ".join(f"{short(g)} {when(i['kickoff'])}" for g, i in sorted(b["games"].items(), key=lambda kv: kv[1]["kickoff"]))
    S = [f"# NFL Props — Parlay C — {datetime.strptime(D, '%Y-%m-%d').strftime('%a %b %-d, %Y')}",
         f"FanDuel odds verified (pulled {pulled}) · recheck inactives ~{', '.join(recheck(k) for k in kicks)} · "
         "Research only, not a guarantee.", "", f"Games: {games}", "",
         "## Parlay C (last-5 streak)", "",
         "_Each link opens FanDuel with that parlay's legs already in your betslip. Check every leg and the price "
         "before placing the bet._", ""]
    pcs = b.get("parlays_c") or []
    if not pcs:
        S += ["No Parlay C today: not enough streak legs from different games passed the checks.", ""]
    for p in pcs:
        S += [f"### {p['name']}", "```"]
        S += [f"{l['player']} {l['selection']} ({am(l['odds'])}) · last 5 (newest first): "
              + " ".join(f"{h['v']:g}" for h in reversed(l["history"][-5:])) for l in p["legs"]]
        S += ["```", f"FanDuel pays ≈{am(p['product_of_leg_prices'])} · model fair odds {am(p['fair_odds'])} · "
                     f"bet only at {am(p['min_acceptable_odds'])} or better"]
        if p["product_of_leg_prices"] < p["min_acceptable_odds"]:
            S.append(f"⚠️ FanDuel's typical {am(p['product_of_leg_prices'])} is below the {am(p['min_acceptable_odds'])} "
                     "price the model needs: negative value. Pass unless FanDuel pays that.")
        S += [f"👉 **[Open {p['name']} in FanDuel]({p['betslip_url']})**", ""]
    S += ["## Leg details", ""]
    legs = [(l, p["name"]) for p in pcs for l in p["legs"]] + \
           [(l, "single, no parlay fit") for l in b.get("streak_leftover", [])]
    for l, tag in legs:
        n = notes.get(f"{l['player']}|{l['market']}", {})
        line, over = float(l["line"]), l["side"] == "Over"
        S += [f"### {l['player']} — {l['selection']} ({am(l['odds'])}) ({tag})", f"_{short(l['game'])} · {when(l['kickoff_et'])}_", "",
              f"| Week | Opp | Result | vs {line:g} |", "|---|---|---|---|"]
        S += [f"| {h['wk']} | {h['opp']} | {h['v']:g} | {'Hit' if ((h['v'] > line) if over else (h['v'] < line)) else 'Miss'} |"
              for h in reversed(l["history"])]
        S += ["", f"Chance {l['p_blend']:.0%} · projection {l['proj_median']:g} · value alone {l['ev']:+.1%} · "
                  f"season {l['season_hits']} · last 10 {l['last10']}", "",
              f"- ✅ **Why:** {n.get('why', '')}", f"- ⚠️ **Risk:** {n.get('risk', '')}",
              f"[➕ This leg alone in FanDuel]({l['betslip_link']})", ""]
    sa = b.get("streak_all") or []
    by = {}
    for r in sa:
        by.setdefault(r["game"], []).append(r)
    S += ["## All last-5 streaks", "",
          f"Every line a player cleared in each of his last 5 games: {len(sa)} lines, "
          f"{sum(r['passes'] for r in sa)} pass every Parlay C check. The phone page shows each one's checklist "
          "and game-by-game data.", ""]
    for g, rs in sorted(by.items(), key=lambda kv: kv[1][0]["kickoff_et"]):
        S += [f"**{short(g)}**", ""] + [f"- {r['player']} {r['selection']} ({am(r['odds'])}) · {r['status']}" for r in rs] + [""]
    ex = ctx.get("exclude", {})
    if ex:
        S += ["## Removed today", ""]
        reasons = {}
        for k, v in ex.items():
            reasons.setdefault(v, []).append(k.replace("|", " "))
        S += [f"- {', '.join(ks)}: {v}" for v, ks in reasons.items()] + [""]
    S += [f"Full research: `{D}-nfl-props.md`"]
    out = os.path.join(R, f"{D}-nfl-props-summary.md")
    open(out, "w").write("\n".join(S) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
