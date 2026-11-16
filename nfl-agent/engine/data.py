"""Data layer: nflverse weekly data (cached), ESPN injuries/odds, name + team mapping.

All network sources:
  * nflverse release files on github.com (player/team weekly stats, schedule with
    spreads/totals/starting QBs, snap counts) - updated nightly.
  * ESPN site API (scoreboard, game summaries with injury lists).
"""
import json
import os
import re
import time
import unicodedata
import urllib.request

import pandas as pd

NFLV = "https://github.com/nflverse/nflverse-data/releases/download"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get("NFL_CACHE", os.path.join(HERE, "..", "cache"))

# Full team name (Odds API / ESPN displayName) -> nflverse abbreviation
TEAMS = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}
ESPN_ABBR = {"LAR": "LA", "WSH": "WAS"}  # ESPN abbreviations that differ from nflverse

OUT_STATUSES = {"out", "injured reserve", "doubtful", "suspension", "physically unable to perform",
                "non football injury", "reserve/covid-19"}


def norm(name):
    """Normalise a player name for matching across sources."""
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.'`\-]", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _get(url, timeout=60, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nfl-prop-research/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # network hiccup -> retry with backoff
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _cached(path, url, max_age_h):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, path)
    if os.path.exists(fp) and (time.time() - os.path.getmtime(fp)) < max_age_h * 3600:
        return fp
    data = _get(url)
    with open(fp, "wb") as f:
        f.write(data)
    return fp


def nflverse(kind, season=None, max_age_h=6):
    """Load an nflverse release file as a DataFrame (cached for max_age_h hours)."""
    files = {
        "player": ("stats_player", f"stats_player_week_{season}.csv"),
        "team": ("stats_team", f"stats_team_week_{season}.csv"),
        "snaps": ("snap_counts", f"snap_counts_{season}.csv"),
        "games": ("schedules", "games.csv"),
    }
    tag, fn = files[kind]
    fp = _cached(fn, f"{NFLV}/{tag}/{fn}", max_age_h)
    df = pd.read_csv(fp, low_memory=False)
    if "season_type" in df.columns:
        df = df[df["season_type"] == "REG"]
    if "game_type" in df.columns and kind == "snaps":
        df = df[df["game_type"] == "REG"]
    return df


class Data:
    """Everything the model needs for one season, plus the prior season for priors."""

    def __init__(self, season, max_age_h=6):
        self.season = season
        self.games = nflverse("games", max_age_h=max_age_h)
        cur, prev = [], []
        for s, bucket in ((season, cur), (season - 1, prev)):
            try:
                bucket.append(nflverse("player", s, max_age_h))
                bucket.append(nflverse("team", s, max_age_h))
            except Exception:
                bucket.extend([pd.DataFrame(), pd.DataFrame()])
        self.player, self.team = cur
        self.player_prev, self.team_prev = prev
        try:
            self.snaps = nflverse("snaps", season, max_age_h)
        except Exception:
            self.snaps = pd.DataFrame()
        if len(self.player):
            self.player = self.player.copy()
            self.player["nname"] = self.player["player_display_name"].map(norm)
        if len(self.player_prev):
            self.player_prev = self.player_prev.copy()
            self.player_prev["nname"] = self.player_prev["player_display_name"].map(norm)
        if len(self.snaps):
            self.snaps = self.snaps.copy()
            self.snaps["nname"] = self.snaps["player"].map(norm)

    def before(self, week):
        """A copy of this Data restricted to games before `week` of the current season
        (used for walk-forward backtests so no future data leaks in)."""
        d = object.__new__(Data)
        d.__dict__.update(self.__dict__)
        d.player = self.player[self.player.week < week].copy()
        d.team = self.team[self.team.week < week].copy()
        d.snaps = self.snaps[self.snaps.week < week].copy() if len(self.snaps) else self.snaps
        g = self.games.copy()
        mask = (g.season == self.season) & (g.week >= week)
        g.loc[mask, ["away_score", "home_score", "result"]] = float("nan")
        d.games = g
        return d


# ---------------------------------------------------------------- ESPN helpers
def espn_json(path):
    return json.loads(_get(f"{ESPN}/{path}", timeout=30))


def espn_scoreboard(date_yyyymmdd=None):
    q = f"scoreboard?dates={date_yyyymmdd}" if date_yyyymmdd else "scoreboard"
    return espn_json(q)


def espn_game_context(event_id):
    """Injuries (out / questionable sets keyed by team abbr) and DraftKings spread/total."""
    d = espn_json(f"summary?event={event_id}")
    out, quest = {}, {}
    for t in d.get("injuries", []):
        ab = t["team"]["abbreviation"]
        ab = ESPN_ABBR.get(ab, ab)
        for i in t.get("injuries", []):
            st = (i.get("status") or "").lower()
            nm = norm(i["athlete"]["displayName"])
            if st in OUT_STATUSES:
                out.setdefault(ab, set()).add(nm)
            elif st == "questionable":
                quest.setdefault(ab, set()).add(nm)
    pc = (d.get("pickcenter") or [{}])[0]
    return {"out": out, "questionable": quest, "spread_text": pc.get("details"),
            "total": pc.get("overUnder"), "spread": pc.get("spread")}
