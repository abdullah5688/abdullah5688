import json
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.graphics.shapes import Drawing, String, Rect, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart

OUT = "/home/user/abdullah5688/nfl-agent/docs/NFL-Prop-Agent-Overview.pdf"
CAL = "/home/user/abdullah5688/nfl-agent/engine/calibration.json"

INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
MUTED = colors.HexColor("#8a8984")
RULE = colors.HexColor("#e2e1dc")
PANEL = colors.HexColor("#f4f3ef")
ACCENT = colors.HexColor("#2a78d6")      # series 1 (blue)
ACCENT2 = colors.HexColor("#eb6834")     # series 2 (orange)
GOOD = colors.HexColor("#1f7a3a")
BAD = colors.HexColor("#b42318")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=24, leading=29,
                    textColor=INK, alignment=0, spaceAfter=4)
SUB = ParagraphStyle("SUB", fontName="Helvetica", fontSize=12, leading=16, textColor=INK2, spaceAfter=14)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=9,
                    spaceAfter=4)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=8,
                    spaceAfter=3)
BODY = ParagraphStyle("BODY", fontName="Helvetica", fontSize=10, leading=13.6, textColor=INK, spaceAfter=5)
SMALL = ParagraphStyle("SMALL", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK2)
CELL = ParagraphStyle("CELL", fontName="Helvetica", fontSize=9, leading=11.5, textColor=INK)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
BUL = ParagraphStyle("BUL", parent=BODY, leftIndent=14, bulletIndent=2, spaceAfter=3)
BIG = ParagraphStyle("BIG", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=ACCENT,
                     alignment=TA_CENTER)
BIGL = ParagraphStyle("BIGL", fontName="Helvetica", fontSize=9, leading=12, textColor=INK2, alignment=TA_CENTER)


def P(t, s=BODY):
    return Paragraph(t, s)


def bullets(items, style=BUL):
    return [Paragraph(i, style, bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=True, styles=()):
    data = [[c if not isinstance(c, str) else P(c, CELLB if (header and i == 0) else CELL) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK if header else RULE),
          ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    t.setStyle(TableStyle(st + list(styles)))
    return t


def callout(flowables, bg=PANEL, border=ACCENT):
    t = Table([[flowables]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    return t


def stat_tiles(items):
    cells = [[P(v, BIG) for v, _ in items], [P(l, BIGL) for _, l in items]]
    w = 7.0 * inch / len(items)
    t = Table(cells, colWidths=[w] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL),
                           ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white),
                           ("TOPPADDING", (0, 0), (-1, 0), 10), ("BOTTOMPADDING", (0, 1), (-1, 1), 10)]))
    return t


def steps_flow(steps):
    """Numbered step cards in a 2-column grid."""
    cards = []
    for n, (title, text) in enumerate(steps, 1):
        num = Table([[P(f"<font color='white'><b>{n}</b></font>",
                        ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER,
                                       leading=14))]],
                    colWidths=[0.34 * inch], rowHeights=[0.34 * inch])
        num.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                 ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
        card = Table([[num, [P(f"<b>{title}</b>", ParagraphStyle("t", parent=BODY, spaceAfter=1)), P(text, SMALL)]]],
                     colWidths=[0.45 * inch, 2.95 * inch])
        card.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        cards.append(card)
    rows = [cards[i:i + 2] for i in range(0, len(cards), 2)]
    t = Table(rows, colWidths=[3.5 * inch, 3.5 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def calibration_chart(buckets):
    """Grouped bars: what the model predicted vs how often it actually happened."""
    W, H = 7.0 * inch, 2.4 * inch
    d = Drawing(W, H)
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 44, 42, W - 60, H - 82
    bc.data = [[round(p * 100) for _, p, _ in buckets], [round(a * 100) for _, _, a in buckets]]
    bc.categoryAxis.categoryNames = [b for b, _, _ in buckets]
    bc.valueAxis.valueMin, bc.valueAxis.valueMax, bc.valueAxis.valueStep = 0, 80, 20
    bc.valueAxis.labelTextFormat = "%d%%"
    bc.valueAxis.labels.fontName = bc.categoryAxis.labels.fontName = "Helvetica"
    bc.valueAxis.labels.fontSize = bc.categoryAxis.labels.fontSize = 8
    bc.valueAxis.labels.fillColor = bc.categoryAxis.labels.fillColor = INK2
    bc.valueAxis.strokeColor = colors.white
    bc.valueAxis.visibleGrid = True
    bc.valueAxis.gridStrokeColor = RULE
    bc.valueAxis.gridStrokeWidth = 0.5
    bc.categoryAxis.strokeColor = MUTED
    bc.bars[0].fillColor, bc.bars[1].fillColor = ACCENT, ACCENT2
    bc.bars.strokeColor = colors.white
    bc.bars.strokeWidth = 1.5            # surface gap between adjacent bars
    bc.barSpacing, bc.groupSpacing = 1.5, 9
    d.add(bc)
    # legend (two series -> legend always present)
    lx, ly = 44, H - 18
    for i, (lab, col) in enumerate((("Model said", ACCENT), ("Actually happened", ACCENT2))):
        x = lx + i * 150
        d.add(Rect(x, ly - 1, 10, 10, fillColor=col, strokeColor=None))
        d.add(String(x + 15, ly, lab, fontName="Helvetica", fontSize=9, fillColor=INK))
    d.add(String(44, 6, "Groups = how likely the model said the over was (all six prop types, 2026 games it never saw)",
                 fontName="Helvetica", fontSize=8, fillColor=INK2))
    return d


def pooled_reliability():
    cal = json.load(open(CAL))["holdout_test"]["report"]
    agg = {}
    for m, r in cal.items():
        for b, (p, a, n) in r["reliability_holdout_cal"].items():
            s = agg.setdefault(b, [0, 0, 0])
            s[0] += p * n
            s[1] += a * n
            s[2] += n
    out = []
    for b in sorted(agg):
        p, a, n = agg[b]
        if n >= 100:
            lo, hi = b.split("-")
            out.append((f"{int(float(lo)*100)}-{int(float(hi)*100)}%", p / n, a / n, n))
    return out


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.75 * inch, 0.5 * inch, "NFL Prop Agent - overview (Nov 2026). Research and decision support, not a guarantee.")
    canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = []
# ------------------------------------------------------------------ page 1
story += [P("Your NFL Prop Agent", H1),
          P("A plain-English guide to how it picks props, how it was tested, and what to do each Sunday.", SUB),
          stat_tiles([("8:47 AM", "every Sunday (ET)"), ("20,000", "simulations per game"),
                      ("~9,000", "past results it was tested on"), ("1", "notification per week")]),
          Spacer(1, 14),
          P("What it is, in one paragraph", H2),
          P("Every Sunday morning a Claude agent wakes up on its own, grades last week's picks, pulls today's "
            "FanDuel player-prop prices, and plays out every game 20,000 times on a computer using real NFL data. "
            "It then compares <b>how often each prop hit in those simulations</b> with <b>what FanDuel's price says</b>. "
            "When the gap is big enough in your favour, the prop becomes a pick. You get one phone notification, "
            "and the full report is saved in your GitHub repo."),
          P("What you get each Sunday", H2),
          *bullets(["<b>Top 10 player props</b> with FanDuel odds, a chance-of-hitting estimate and a tier (Bet or Lean).",
                    "<b>Parlay A</b> (different games) and <b>Parlay B</b> (same game), each with a "
                    "<b>\"bet only at X or better\"</b> price to compare with FanDuel's quote.",
                    "<b>FanDuel links</b> that open the betslip with the legs already added.",
                    "<b>Best over vs best under</b> for every player, so unders are never ignored.",
                    "<b>Last week's results</b>: record, units won or lost, season totals."]),
          P("The 6 steps every Sunday", H2),
          steps_flow([
              ("Grade last week", "Looks up the final stats for last Sunday's picks and records win / loss / units. "
               "Re-tunes the model with the newest games."),
              ("Gather the data", "FanDuel prices for all six prop types and every \"X+\" alt rung (DraftKings and "
               "BetMGM for comparison). Player and team stats, snap counts, starting QBs, spreads and totals "
               "(nflverse). Injury lists (ESPN). Breaking news (web search)."),
              ("Simulate every game 20,000 times", "Who plays QB, who is injured, how the game is likely to go, "
               "how good the defence is against each position: all built into the simulation."),
              ("Compare with FanDuel", "For every line and every alt rung, over and under: how often did it hit "
               "in the simulations vs. what does FanDuel's price imply? Finds the value."),
              ("Safety checks + review", "Automatic \"do not bet\" rules, then the agent checks the shortlist "
               "against the latest news. It can remove a pick (with a written reason) but never invent numbers."),
              ("Deliver", "Full report + quick-read summary saved to GitHub, results logged, one push notification."),
          ])]
story.append(PageBreak())

# ------------------------------------------------------------------ page 2
story += [P("How one pick gets chosen", H1),
          P("A real example from the Monday-night test run (Chargers @ Ravens).", SUB),
          callout([P("<b>Derrick Henry - Under 80.5 rushing yards - FanDuel -113</b>", BODY),
                   table([["", "What it means", "Number"],
                          ["Model", "In 20,000 simulated games Henry stayed under 80.5 this often", "60%"],
                          ["FanDuel", "What FanDuel's price says, after removing their built-in cut", "50%"],
                          ["Blend", "Half model, half FanDuel - our final estimate", "<b>55%</b>"],
                          ["Break-even", "How often a -113 bet must win just to not lose money", "53%"],
                          ["Edge (EV)", "Expected profit per $1 bet: 55% chance at -113 odds", "<b>+3%</b>"],
                          ["Verdict", "Positive, but under +4%", "<b>Lean</b>"]],
                         [0.95 * inch, 4.65 * inch, 1.0 * inch], zebra=False)]),
          Spacer(1, 6),
          P("Why blend with FanDuel instead of trusting the model alone?", H3),
          P("FanDuel's lines are set by professionals and move with sharp money, so they are usually close to right. "
            "Treating the market as a strong second opinion stops the model from betting on its own mistakes. "
            "The weight only changes if the results log proves the model is better."),
          P("The tiers", H3),
          table([["Tier", "Rule", "What to do"],
                 ["Bet", "Expected profit at least +4% and at least 2 points above break-even", "The main picks"],
                 ["Lean", "Expected profit at least +1.5%", "Smaller or optional"],
                 ["Pass", "Not enough value", "Skip"],
                 ["Research Only", "Looks good but a safety rule blocked it", "Do not bet"]],
                [1.2 * inch, 3.8 * inch, 2.0 * inch]),
          P("What the simulation takes into account", H2),
          *bullets(["<b>Who the QB is.</b> Stats only count from games with today's starter. A QB making his first "
                    "start blocks that team's passing props entirely (last week's rookie-QB picks lost).",
                    "<b>Who is injured.</b> An injured player's targets and carries are handed to his teammates.",
                    "<b>How the game should go.</b> Favourites run more, underdogs throw more (last week a running "
                    "back on a losing team got only 7 carries).",
                    "<b>The defence, position by position,</b> adjusted for the quality of offences it has faced.",
                    "<b>More history.</b> Last season counts at half weight so small samples don't fool it.",
                    "<b>Links inside a game.</b> A QB's passing yards are the sum of his receivers' yards, so "
                    "same-game parlays are priced with the real connections between legs."])]
story.append(PageBreak())

# ------------------------------------------------------------------ page 3
story += [P("Safety rules and quick tests", H1),
          P("The rules that stop a bet, and the smaller checks we ran before trusting the system.", SUB),
          KeepTogether([P("Automatic \"do not bet\" rules", H2),
          table([["Rule", "Why"],
                 ["QB making his first NFL start", "No reliable data for his receivers"],
                 ["Player listed questionable", "Might not play or be limited"],
                 ["Fewer than 4 games this season", "Sample too small"],
                 ["Odds worse than -350", "Your permanent setting"],
                 ["Projection outside the tested range (e.g. a running back's catches, most QB rushing)",
                  "The model was not tested there"],
                 ["Less than a 45% chance", "Your balanced style: long shots are listed separately, never in parlays"],
                 ["Removed by the agent for news or weather", "Always with a written reason"]],
                [3.6 * inch, 3.4 * inch])]),
          P("Test 2 - The odds feed matches the FanDuel app", H2),
          P("Your screenshots of Alt Rushing and Alt Receiving yards were compared with what the agent receives. "
            "Every price matched exactly - e.g. Derrick Henry 40+ / 50+ / 60+ / 70+ at -1100 / -500 / -300 / -188, "
            "Zay Flowers 60+ receiving at -182."),
          KeepTogether([P("Test 3 - A full live run on Monday night's game", H2),
          P("The whole system ran start to finish on Chargers @ Ravens. It correctly blocked the Ravens' passing "
            "game (their likely QB had never started) and found four bugs, all fixed:"),
          *bullets(["Low-volume props (a running back's receiving yards) slipped through - now blocked.",
                    "The FanDuel comparison broke on lopsided alt ladders - now uses each line's own price.",
                    "Results changed slightly every run - now identical every time.",
                    "A good main-line pick was hidden behind a long shot - fixed."])]),
          P("Test 4 - Plumbing", H2),
          *bullets(["A brand-new cloud session downloads all the data by itself (2 seconds).",
                    "Last Sunday's picks were graded automatically from official stats.",
                    "FanDuel betslip links come back for every pick, including alt rungs."])]
story.append(PageBreak())

# big test page
rel = pooled_reliability()
story += [P("The big test: replaying two seasons", H1),
          P("Short version: the model's chances are honest to within a few points. Whether it can beat FanDuel "
            "over time is what the weekly results log will now measure.", SUB),
          P("How the test worked", H2),
          P("We replayed <b>every game from 2025 and 2026</b> as if it were happening live: for each week, the model "
            "only saw data from earlier weeks, then predicted every player's stats. That gave <b>about 9,000 "
            "player results</b> to check. To make it a fair test, the final tuning was done on 2025 only and then "
            "graded on <b>2026 games it had never seen</b>."),
          P("<b>What \"honest\" looks like:</b> when the model says something happens 60% of the time, it should "
            "happen about 60% of the time. Blue and orange bars of similar height = honest.", BODY),
          calibration_chart([(b, p, a) for b, p, a, n in rel]),
          table([["Model said"] + [b for b, _, _, _ in rel],
                 ["Actually happened"] + [f"{a:.0%}" for _, _, a, _ in rel],
                 ["Number of checks"] + [f"{n:,}" for *_, n in rel]],
                [1.3 * inch] + [5.7 * inch / len(rel)] * len(rel), zebra=False),
          Spacer(1, 6),
          table([["Prop type", "2026 results checked", "When model said 60-70%, it actually hit"],
                 ["Receptions", "778", "70%"], ["Receiving yards", "712", "65%"],
                 ["Rushing attempts", "359", "65%"], ["Rushing yards", "333", "57%  (a little too optimistic)"],
                 ["Passing yards", "171", "63%"], ["Passing attempts", "171", "72%"]],
                [2.0 * inch, 1.8 * inch, 3.2 * inch])]
story.append(PageBreak())


# ------------------------------------------------------------------ page 4
res = [["Pick (old process, Nov 15)", "FanDuel", "Result"],
       ["Trey McBride over 6.5 receptions", "+102", "<font color='#b42318'>Lost (5)</font>"],
       ["Jaylen Warren over 64.5 rush yds", "-113", "Pending (15 late in game)"],
       ["Christian McCaffrey over 61.5 rush yds", "-113", "<font color='#1f7a3a'>Won (62)</font>"],
       ["George Kittle over 61.5 rec yds", "-113", "<font color='#1f7a3a'>Won (74)</font>"],
       ["Jaxon Smith-Njigba over 89.5 rec yds", "-113", "<font color='#1f7a3a'>Won (171)</font>"],
       ["Tee Higgins over 75.5 rec yds", "-113", "Pending (66 late in game)"],
       ["Brock Bowers over 58.5 rec yds", "-113", "<font color='#b42318'>Lost (18)</font>"],
       ["Brock Purdy over 21.5 rush yds", "-113", "<font color='#b42318'>Lost (21)</font>"],
       ["Joe Burrow over 6.5 rush yds", "-113", "Pending (8 late in game)"],
       ["Michael Mayer over 21.5 rec yds", "-113", "<font color='#b42318'>Lost (16)</font>"],
       ["Parlay A and Parlay B", "", "<font color='#b42318'>Both lost</font>"]]
story += [P("Last Sunday, and what changed", H1),
          P("These picks came from the first version, before the model existed. Graded so far: 3 wins, 4 losses "
            "(-1.34 units). The Sunday-night game was still being played when this was written.", SUB),
          table(res, [3.6 * inch, 1.0 * inch, 2.4 * inch]),
          Spacer(1, 8),
          table([["What went wrong", "What we changed"],
                 ["3 of the losses relied on a rookie QB's first start", "First-start QBs now block their team's passing props"],
                 ["A running back on a losing team got 7 carries", "The likely game flow now drives run/pass volume"],
                 ["All 10 picks were overs", "Overs and unders are scored the same way at every line"],
                 ["Two picks were decided by 1 yard or less", "Every line's chance is calculated, so thin cushions show up"],
                 ["\"Hit 5 of 8 games\" was treated as an edge", "Picks now need a real calculated edge over FanDuel's price"],
                 ["Parlay legs all depended on one team's run game", "Same-game parlays use the joint simulation"],
                 ["Nothing tracked whether picks won", "A results log grades every pick each Sunday"]],
                [3.3 * inch, 3.7 * inch]),
          ]
story.append(PageBreak())
story += [P("Honest limits and your checklist", H1),
          P("What the system can't do yet, and the five things to do each Sunday.", SUB),
          P("Honest limits", H2),
          *bullets(["<b>Not yet proven to beat FanDuel.</b> The model's chances are honest, but beating the market is "
                    "a separate question. Give it 150+ graded picks before judging.",
                    "<b>Rushing-yard overs</b> are rated a little too highly (see Test 1). Be extra careful with them.",
                    "<b>No weather in the model.</b> The agent checks wind and rain by hand for outdoor games.",
                    "<b>Inactives come out after the 8:47 run.</b> Check them yourself about 90 minutes before kickoff.",
                    "<b>FanDuel's parlay price isn't in the data feed.</b> That's why you get a \"bet only at X or better\" number.",
                    "Only Sunday games are covered. Thursday, Saturday and Monday games are skipped."]),
          KeepTogether([P("Your Sunday checklist", H2),
                        table([["", "Step"],
                               ["1", "Read the notification (~9:30 AM ET): last week's results and today's top picks."],
                               ["2", "Open the summary in GitHub: nfl-agent/reports/<date>-nfl-props-summary.md"],
                               ["3", "About 90 minutes before kickoff (11:30 AM for 1 PM games), check your players are active."],
                               ["4", "For parlays, only bet if FanDuel's quote is at or better than the \"bet only at\" price."],
                               ["5", "Bet small, flat amounts. No result is guaranteed."]],
                              [0.4 * inch, 6.6 * inch], zebra=False)])]

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                        topMargin=0.7 * inch, bottomMargin=0.8 * inch, title="NFL Prop Agent Overview",
                        author="NFL Prop Agent")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
