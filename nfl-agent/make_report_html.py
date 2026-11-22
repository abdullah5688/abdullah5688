#!/usr/bin/env python3
"""Render the weekly picks as a phone-friendly HTML page (and, via make_pdf.js, a PDF).

Usage: python3 make_report_html.py 2026-11-22 [--out reports/]

Reads, for that date:
  reports/DATE-picks.json    model output (all numbers come from here)
  reports/DATE-context.json  analyst context (QBs, exclusions with reasons)
  reports/DATE-notes.json    optional {"Player": {"why": "...", "risk": "..."}} written by the analyst
  ledger/picks.csv           graded results for the record line
Writes reports/DATE-nfl-props.html. Nothing here invents a number: every figure is copied
from those files.
"""
import argparse
import html
import json
import os
from datetime import datetime

import pandas as pd

E = html.escape


def am(o):
    o = int(o)
    return f"+{o}" if o > 0 else str(o)


def pct(x):
    return f"{x * 100:.0f}%"


def evs(x):
    return f"{x * 100:+.1f}%"


def kick(k):
    t = datetime.strptime(k, "%Y-%m-%d %H:%M")
    return t.strftime("%-I:%M %p").replace(":00 ", " ")


def recheck(k):
    t = datetime.strptime(k, "%Y-%m-%d %H:%M") - pd.Timedelta(minutes=90)
    return t.strftime("%-I:%M %p")


def record(date):
    """Last graded week and season-to-date for top picks, from ledger/picks.csv."""
    try:
        df = pd.read_csv("ledger/picks.csv")
    except OSError:
        return None
    g = df[(df.source == "top") & df.result.isin(["win", "loss", "push"]) & (df.date < date)]
    if not len(g):
        return None

    def line(x):
        w, l = int((x.result == "win").sum()), int((x.result == "loss").sum())
        u = float(x.units.sum())
        return dict(w=w, l=l, units=u, roi=u / max(1, len(x)))
    last = g.date.max()
    return dict(last_date=last, last=line(g[g.date == last]), season=line(g))


def short_game(g):
    a, h = g.split(" @ ")
    return f"{a.split()[-1]} @ {h.split()[-1]}"


def leg_rows(legs, extra=False):
    out = []
    for l in legs:
        sub = f"{E(short_game(l['game']))} · {kick(l['kickoff_et'])}"
        if extra:
            sub += f" · last 5: <span class=num>{E(l['last5_values'])}</span>"
        out.append(f"""<li class="leg"><div class="leg-main"><span class="leg-name">{E(l['player'])}</span>
<span class="leg-sel">{E(l['selection'])}</span><span class="leg-sub">{sub}</span></div>
<span class="odds">{am(l['odds'])}</span></li>""")
    return "\n".join(out)


def parlay_card(key, title, tag, p, warn=None):
    if not p:
        return f'<section class="parlay" id="{key}"><h3>{title}</h3><p class="muted">No qualifying combination today.</p></section>'
    extra = key.startswith("parlay-c")
    value = p["ev_if_priced_as_product"]
    verdict = ("good", "Model sees value at FanDuel's typical price") if value > 0 else \
        ("bad", "Model sees negative value at FanDuel's typical price")
    corr = f'<div class="kv"><span>Correlation</span><b class="num">{p["correlation_factor"]}</b></div>' \
        if p.get("correlation_factor") else ""
    w = f'<p class="note warn">{warn}</p>' if warn else ""
    link = f'<a class="btn" href="{E(p["betslip_url"])}" target="_blank" rel="noopener">Open in FanDuel</a>' \
        if p.get("betslip_url") else ""
    return f"""<section class="parlay" id="{key}">
<div class="parlay-head"><h3>{title}</h3><span class="tag">{tag}</span></div>
<ul class="legs">{leg_rows(p['legs'], extra)}</ul>
<div class="minbox"><span>Bet only at</span><b class="num">{am(p['min_acceptable_odds'])}</b><span>or better</span></div>
<div class="kvs"><div class="kv"><span>Model chance</span><b class="num">{p['model_joint_prob']*100:.1f}%</b></div>
<div class="kv"><span>Fair odds</span><b class="num">{am(p['fair_odds'])}</b></div>
<div class="kv"><span>Legs multiplied</span><b class="num">{am(p['product_of_leg_prices'])}</b></div>{corr}</div>
<p class="pill {verdict[0]}">{verdict[1]}</p>{w}{link}</section>"""


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
    top, games = b["top"], b["games"]
    day = datetime.strptime(D, "%Y-%m-%d")
    pulled = datetime.fromisoformat(b["generated_at"]).strftime("%-I:%M %p")
    odds_t = os.path.basename(b["odds_file"]).replace("odds-", "").replace(".csv", "")
    odds_time = datetime.strptime(odds_t, "%Y%m%d-%H%M").strftime("%-I:%M %p ET")
    rec = record(D)
    kicks = sorted({g["kickoff"] for g in games.values()})

    # ---- header stats
    rec_html = ""
    if rec:
        L, S = rec["last"], rec["season"]
        rec_html = f"""<div class="stat"><span>Last week</span><b class="num">{L['w']}-{L['l']}</b><small class="num">{L['units']:+.2f}u</small></div>
<div class="stat"><span>Season</span><b class="num">{S['w']}-{S['l']}</b><small class="num">{S['units']:+.2f}u · ROI {S['roi']*100:+.1f}%</small></div>"""

    # ---- top 10
    cards = []
    for i, p in enumerate(top, 1):
        n = notes.get(p["player"], {})
        why = n.get("why") or f"Model median {p['proj_median']:g} vs this line."
        risk = n.get("risk") or "See flags."
        flags = "".join(f'<span class="flag">{E(f)}</span>' for f in (p.get("flags") or "").split(",") if f)
        cards.append(f"""<details class="pick">
<summary><span class="rank num">{i}</span><span class="pick-main"><span class="pick-name">{E(p['player'])}</span>
<span class="pick-sel">{E(p['selection'])}</span><span class="pick-sub">{E(short_game(p['game']))} · {kick(p['kickoff_et'])}</span></span>
<span class="pick-right"><span class="odds">{am(p['odds'])}</span><span class="tier {p['tier'].lower()}">{E(p['tier'])}</span></span></summary>
<div class="pick-body">
<div class="kvs"><div class="kv"><span>Chance</span><b class="num">{pct(p['p_blend'])}</b></div>
<div class="kv"><span>Value (EV)</span><b class="num">{evs(p['ev'])}</b></div>
<div class="kv"><span>Projection</span><b class="num">{p['proj_median']:g}</b></div>
<div class="kv"><span>Season</span><b class="num">{E(p['season_hits'])}</b></div></div>
<p class="l5">Last 5 games: <span class="num">{E(p['last5_values'])}</span> <span class="muted">({E(p['last5'])} would have won)</span></p>
<p><b>Why.</b> {E(why)}</p><p><b>Risk.</b> {E(risk)}</p>{('<p class="flags">' + flags + '</p>') if flags else ''}
<a class="btn small" href="{E(p['betslip_link'])}" target="_blank" rel="noopener">Add to FanDuel betslip</a>
</div></details>""")

    copy_text = "\n".join(f"{i}. {p['player']} {p['selection']} ({am(p['odds'])}) · {p['tier']}" for i, p in enumerate(top, 1))

    # ---- parlays
    pcs = b.get("parlays_c") or ([b["parlay_c"]] if b.get("parlay_c") else [])
    warn_c = "Every leg hit in each of the player's last 5 games. Books price streaks steeply, so keep stakes small."
    parlays = "\n".join(
        parlay_card(f"parlay-c{i}", p.get("name") or f"Parlay C{i}", "Last-5 streak", p,
                    warn_c if p["ev_if_priced_as_product"] <= 0 else None)
        for i, p in enumerate(pcs, 1)) or parlay_card("parlay-c", "Parlay C", "Last-5 streak", None)

    # ---- avoided & exclusions
    avoid = "".join(f"<li><b>{E(x['player'])}</b> {E(x['selection'])} <span class=num>({am(x['odds'])})</span>"
                    f" <span class=muted>EV {evs(x['ev'])}</span></li>" for x in b.get("avoid", [])[:5])
    excl = "".join(f"<li><b>{E(k)}</b> <span class=muted>{E(v)}</span></li>" for k, v in ctx.get("exclude", {}).items())
    qbs = "".join(f"<li><b>{E(t)}</b> {E(q)}</li>" for t, q in ctx.get("qb", {}).items())
    checks = "".join(f"<li><span class=num>{recheck(k)}</span> for the {kick(k)} games</li>" for k in kicks)

    page = f"""<meta charset="utf-8"><title>NFL Props {day.strftime('%b %-d')}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Inter:wght@400;500;600&display=swap">
<style>
/* Layout: one phone-width column, a ticket-like stack: record, copy list, parlays, details. */
:root {{
  --bg:#f3f5f2; --surface:#ffffff; --ink:#15201a; --muted:#5d6b62; --line:#dbe2dc;
  --accent:#1d6b45; --accent-ink:#ffffff; --good:#1d6b45; --bad:#b3261e; --warn:#8a5a00; --chip:#e6ede8;
  --display:"Barlow Condensed","Arial Narrow",Arial,sans-serif; --body:Inter,system-ui,-apple-system,sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#0f1512; --surface:#18211c; --ink:#e7eee9; --muted:#9aa9a0; --line:#2a3630;
  --accent:#5cc28c; --accent-ink:#08130d; --good:#5cc28c; --bad:#ff8a80; --warn:#f2c46b; --chip:#223029; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#0f1512; --surface:#18211c; --ink:#e7eee9; --muted:#9aa9a0; --line:#2a3630;
  --accent:#5cc28c; --accent-ink:#08130d; --good:#5cc28c; --bad:#ff8a80; --warn:#f2c46b; --chip:#223029; color-scheme:dark }}
* {{ box-sizing:border-box }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.5 var(--body); padding-left:max(16px, env(safe-area-inset-left,0px)); padding-right:max(16px, env(safe-area-inset-right,0px)); padding-block:20px 48px }}
.wrap {{ max-width:640px; margin:0 auto; display:flex; flex-direction:column; gap:28px }}
h1,h2,h3 {{ font-family:var(--display); font-weight:700; letter-spacing:.01em; margin:0; text-wrap:balance }}
h1 {{ font-size:2.4rem; line-height:1 }} h2 {{ font-size:1.5rem; text-transform:uppercase; letter-spacing:.04em }} h3 {{ font-size:1.35rem }}
p {{ margin:0 }} .muted {{ color:var(--muted) }} .num {{ font-variant-numeric:tabular-nums }}
section {{ display:flex; flex-direction:column; gap:12px; min-width:0 }}
.eyebrow {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.12em; color:var(--muted); font-weight:600 }}
.status {{ display:flex; flex-wrap:wrap; gap:8px }}
.chip {{ background:var(--chip); border-radius:999px; padding:4px 10px; font-size:.8rem; font-weight:500 }}
.chip.ok {{ color:var(--good) }}
.stats {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px }} .stat.wide {{ grid-column:1/-1 }}
.stat {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:10px 12px; display:flex; flex-direction:column }}
.stat span {{ font-size:.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em }}
.stat b {{ font-family:var(--display); font-size:1.8rem; line-height:1.1 }} .stat small {{ color:var(--muted) }}
.copy {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:12px; overflow-x:auto }}
.copy pre {{ margin:0; font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace; white-space:pre-wrap; padding-left:1.6em; text-indent:-1.6em }}
.row {{ display:flex; justify-content:space-between; align-items:center; gap:12px }}
.btn {{ display:inline-flex; justify-content:center; align-items:center; background:var(--accent); color:var(--accent-ink); text-decoration:none; font-weight:600; border-radius:10px; padding:12px 16px; border:0; font:600 15px var(--body); cursor:pointer }}
.btn.small {{ padding:8px 12px; font-size:.85rem; align-self:flex-start }} .btn.ghost {{ background:var(--chip); color:var(--ink) }}
.btn:focus-visible, summary:focus-visible {{ outline:3px solid var(--accent); outline-offset:2px }}
.parlay {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; padding:16px; gap:14px }}
.parlay-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; flex-wrap:wrap }}
.tag {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.1em; color:var(--muted); font-weight:600 }}
.legs {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column }}
.leg {{ display:flex; justify-content:space-between; gap:12px; padding:10px 0; border-top:1px dashed var(--line) }}
.leg:first-child {{ border-top:0 }}
.leg-main {{ display:flex; flex-direction:column; min-width:0 }}
.leg-name {{ font-weight:600 }} .leg-sel {{ }} .leg-sub {{ font-size:.8rem; color:var(--muted) }}
.odds {{ font-family:var(--display); font-size:1.3rem; font-weight:700; font-variant-numeric:tabular-nums; white-space:nowrap }}
.minbox {{ display:flex; align-items:baseline; gap:8px; justify-content:center; background:var(--chip); border-radius:10px; padding:10px }}
.minbox b {{ font-family:var(--display); font-size:2rem; color:var(--accent) }} .minbox span {{ font-size:.85rem; color:var(--muted) }}
.kvs {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(110px,1fr)); gap:8px }}
.kv {{ display:flex; flex-direction:column }} .kv span {{ font-size:.72rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em }} .kv b {{ font-size:1rem }}
.pill {{ font-size:.85rem; font-weight:600 }} .pill.good {{ color:var(--good) }} .pill.bad {{ color:var(--bad) }}
.note.warn {{ font-size:.85rem; color:var(--warn) }}
.picks {{ display:flex; flex-direction:column; gap:8px }}
.pick {{ background:var(--surface); border:1px solid var(--line); border-radius:12px }}
.pick summary {{ list-style:none; display:flex; gap:12px; align-items:center; padding:12px; cursor:pointer }}
.pick summary::-webkit-details-marker {{ display:none }}
.rank {{ font-family:var(--display); font-size:1.4rem; color:var(--muted); width:1.4em; text-align:center; flex:none }}
.pick-main {{ display:flex; flex-direction:column; flex:1; min-width:0 }}
.pick-name {{ font-weight:600 }} .pick-sub {{ font-size:.8rem; color:var(--muted) }}
.pick-right {{ display:flex; flex-direction:column; align-items:flex-end; gap:2px }}
.tier {{ font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em; color:var(--good) }}
.tier.lean {{ color:var(--warn) }}
.pick-body {{ padding:0 12px 14px 12px; display:flex; flex-direction:column; gap:10px; border-top:1px solid var(--line); padding-top:12px }}
.flags {{ display:flex; flex-wrap:wrap; gap:6px }} .flag {{ background:var(--chip); border-radius:6px; padding:2px 6px; font-size:.72rem }}
ul.plain {{ margin:0; padding-left:18px; display:flex; flex-direction:column; gap:6px }}
.foot {{ font-size:.8rem; color:var(--muted); border-top:1px solid var(--line); padding-top:14px }}
@media print {{
  body {{ background:#fff; color:#000; padding:0 }} .btn {{ display:none }}
  .pick, .parlay {{ break-inside:avoid }} details > .pick-body {{ display:flex }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important }} }}
</style>
<div class="wrap">
<header style="display:flex;flex-direction:column;gap:12px">
<span class="eyebrow">NFL player props · Sunday slate</span>
<h1>{day.strftime('%A, %B %-d')}</h1>
<div class="status"><span class="chip ok">FanDuel odds verified · {odds_time}</span><span class="chip">{len(games)} games</span>
<span class="chip">Research only, not a guarantee</span></div>
<div class="stats">{rec_html}<div class="stat wide"><span>Recheck inactives</span><b class="num">{recheck(kicks[0])}</b><small>{' · '.join(recheck(k) for k in kicks[1:]) and 'then ' + ' · '.join(recheck(k) for k in kicks[1:])} · 90 min before each kickoff</small></div></div>
</header>

<section id="copy"><div class="row"><h2>Top {len(top)}</h2><button class="btn ghost small" id="copy-btn" type="button">Copy list</button></div>
<div class="copy"><pre id="copy-text">{E(copy_text)}</pre></div></section>

<section id="parlays"><h2>Parlays</h2>
<p class="muted">Each button opens FanDuel with the legs in your betslip. Check every leg and the price before you bet.</p>
{parlays}</section>

<section id="picks"><h2>Pick details</h2><p class="muted">Tap a pick for the reasoning.</p>
<div class="picks">{''.join(cards)}</div></section>

<section id="checks"><h2>Before kickoff</h2><ul class="plain">{checks}
<li>Re-check every price in the app; these are from {odds_time}.</li></ul></section>

<section id="context"><h2>Today's context</h2>
{('<p class="eyebrow">Starting QB changes</p><ul class="plain">' + qbs + '</ul>') if qbs else ''}
{('<p class="eyebrow">Avoided (popular props with negative value)</p><ul class="plain">' + avoid + '</ul>') if avoid else ''}
{('<p class="eyebrow">Removed by the analyst</p><ul class="plain">' + excl + '</ul>') if excl else ''}
</section>

<p class="foot">Probabilities blend the projection model with FanDuel's no-vig price. "Bet only at" is the model's fair price plus 5%. Parlay prices are not FanDuel quotes. Generated {pulled} ET from {E(os.path.basename(b['odds_file']))}. Research and decision support only.</p>
</div>
<script>
document.getElementById('copy-btn').addEventListener('click', async (e) => {{
  const t = document.getElementById('copy-text').innerText;
  try {{ await navigator.clipboard.writeText(t); e.target.textContent = 'Copied'; }}
  catch (err) {{ const r = document.createRange(); r.selectNodeContents(document.getElementById('copy-text'));
    const s = getSelection(); s.removeAllRanges(); s.addRange(r); e.target.textContent = 'Selected, copy now'; }}
}});
</script>
"""
    out = os.path.join(R, f"{D}-nfl-props.html")
    open(out, "w").write(page)
    print("wrote", out)


if __name__ == "__main__":
    main()
