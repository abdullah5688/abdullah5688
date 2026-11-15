#!/usr/bin/env python3
"""Pull today's NFL player-prop prices (FanDuel first, DK/BetMGM for comparison)
from The Odds API and save them as JSON + CSV.

Usage:  ODDS_API_KEY=... python3 fetch_odds.py [--out DIR] [--date YYYY-MM-DD]

Only standard-library modules are used. Every price written out carries the
bookmaker key and the bookmaker's own `last_update` timestamp so the report
can cite exactly where and when each quote was seen.
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api.the-odds-api.com/v4"
SPORT = "americanfootball_nfl"
BOOKS = "fanduel,draftkings,betmgm"
ET = ZoneInfo("America/New_York")

# The six allowed categories, plus their alternate-line markets.
MARKETS = [
    "player_pass_yds", "player_pass_yds_alternate",
    "player_pass_attempts", "player_pass_attempts_alternate",
    "player_rush_yds", "player_rush_yds_alternate",
    "player_rush_attempts", "player_rush_attempts_alternate",
    "player_reception_yds", "player_reception_yds_alternate",
    "player_receptions", "player_receptions_alternate",
]

remaining = {"value": "?"}


def get(path, **params):
    params["apiKey"] = os.environ["ODDS_API_KEY"]
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "nfl-prop-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        remaining["value"] = r.headers.get("x-requests-remaining", "?")
        return json.load(r)


def event_odds(event_id, markets):
    """Fetch markets for one event; if the API rejects the combined request
    (e.g. one market key is unsupported), retry market by market."""
    common = dict(bookmakers=BOOKS, oddsFormat="american", dateFormat="iso")
    try:
        return get(f"/sports/{SPORT}/events/{event_id}/odds", markets=",".join(markets), **common), []
    except urllib.error.HTTPError as e:
        if e.code not in (400, 422):
            raise
    merged, rejected = None, []
    for m in markets:
        try:
            data = get(f"/sports/{SPORT}/events/{event_id}/odds", markets=m, **common)
        except urllib.error.HTTPError as e:
            if e.code in (400, 422):
                rejected.append(m)
                continue
            raise
        if merged is None:
            merged = data
            continue
        by_key = {b["key"]: b for b in merged.get("bookmakers", [])}
        for b in data.get("bookmakers", []):
            if b["key"] in by_key:
                by_key[b["key"]]["markets"].extend(b["markets"])
            else:
                merged.setdefault("bookmakers", []).append(b)
    return merged or {}, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".")
    ap.add_argument("--date", help="ET date to pull (default: today in ET)")
    args = ap.parse_args()

    if not os.environ.get("ODDS_API_KEY"):
        sys.exit("ODDS_API_KEY is not set: odds cannot be verified. Mark every candidate 'Research Only'.")

    now = datetime.now(timezone.utc)
    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else now.astimezone(ET).date()
    start = datetime(day.year, day.month, day.day, tzinfo=ET)
    end = start + timedelta(days=1)
    frm = max(start, now).astimezone(timezone.utc)  # pregame only: skip games already started

    events = get(f"/sports/{SPORT}/events",
                 commenceTimeFrom=frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 commenceTimeTo=end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"{len(events)} upcoming NFL events on {day} (ET) not yet started")

    os.makedirs(args.out, exist_ok=True)
    rows, raw = [], []
    for ev in events:
        data, rejected = event_odds(ev["id"], MARKETS)
        data["rejected_markets"] = rejected
        raw.append(data)
        kick = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00")).astimezone(ET)
        for b in data.get("bookmakers", []):
            for m in b.get("markets", []):
                for o in m.get("outcomes", []):
                    rows.append({
                        "game": f"{ev['away_team']} @ {ev['home_team']}",
                        "kickoff_et": kick.strftime("%Y-%m-%d %H:%M"),
                        "event_id": ev["id"],
                        "book": b["key"],
                        "book_last_update": m.get("last_update", b.get("last_update")),
                        "market": m["key"],
                        "player": o.get("description"),
                        "side": o.get("name"),
                        "line": o.get("point"),
                        "american_odds": o.get("price"),
                    })
        print(f"  {ev['away_team']} @ {ev['home_team']} {kick:%a %H:%M} ET: "
              f"{sum(len(b.get('markets', [])) for b in data.get('bookmakers', []))} book-markets"
              + (f", unsupported: {rejected}" if rejected else ""))

    stamp = now.astimezone(ET).strftime("%Y%m%d-%H%M")
    jpath = os.path.join(args.out, f"odds-{stamp}.json")
    cpath = os.path.join(args.out, f"odds-{stamp}.csv")
    with open(jpath, "w") as f:
        json.dump({"pulled_at_utc": now.isoformat(), "events": raw}, f, indent=1)
    with open(cpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["game"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} prices saved -> {cpath}\nAPI credits remaining: {remaining['value']}")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("The Odds API rejected ODDS_API_KEY (401). Odds are unverified: mark candidates 'Research Only'.")
        if e.code == 429:
            sys.exit("The Odds API quota/rate limit reached (429). Odds are unverified: mark candidates 'Research Only'.")
        raise
